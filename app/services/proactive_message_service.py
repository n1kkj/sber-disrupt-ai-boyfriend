from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.character_version_dao import CharacterVersionDao
from app.dao.memory_event_dao import MemoryEventDao
from app.dao.message_dao import MessageDao
from app.dao.proactive_message_dao import ProactiveMessageDao
from app.dao.user_profile_dao import UserProfileDao
from app.logging import logger
from app.models.chat import Chat
from app.models.memory_event import MemoryEvent
from app.models.message import Message
from app.models.proactive_message import ProactiveMessage
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.companion_prompt_service import CompanionPromptService
from app.services.gemini_service import GeminiAIService
from app.services.gender_addressing_service import GenderAndAddressingService
from app.services.memory_service import MemoryService
from app.services.redis_task_service import RedisTaskService
from settings import config


class ProactiveMessageService:
    @classmethod
    def _now(cls: type['ProactiveMessageService']) -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _is_quiet_hours(
        cls: type['ProactiveMessageService'],
        profile: UserProfile,
        now: datetime,
    ) -> bool:
        if profile.quiet_hours_start is None or profile.quiet_hours_end is None:
            return False
        try:
            local_now = now.astimezone(ZoneInfo(profile.timezone)).time()
        except Exception:
            logger.warning('proactive_invalid_timezone timezone=%s', profile.timezone)
            local_now = now.time()
        start = profile.quiet_hours_start
        end = profile.quiet_hours_end
        if start <= end:
            return start <= local_now < end
        return local_now >= start or local_now < end

    @classmethod
    def _reason(
        cls: type['ProactiveMessageService'],
        last_message: Optional[Message],
        now: datetime,
    ) -> Optional[str]:
        if last_message is None:
            return None
        created_at = last_message.created_at.replace(tzinfo=timezone.utc)
        age = now - created_at
        if last_message.role == 'user' and age >= timedelta(minutes=config.proactive.follow_up_delay_minutes):
            return 'follow_up'
        if last_message.role == 'assistant' and age >= timedelta(hours=config.proactive.return_after_hours):
            return 'return'
        return None

    @classmethod
    def _deduplication_key(
        cls: type['ProactiveMessageService'],
        user_id: UUID,
        chat_id: UUID,
        reason: str,
        now: datetime,
    ) -> str:
        return f'{user_id}:{chat_id}:{reason}:{now.date().isoformat()}'

    @classmethod
    def _memory_event_deduplication_key(
        cls: type['ProactiveMessageService'],
        event_id: UUID,
    ) -> str:
        return f'memory_event:{event_id}'

    @classmethod
    async def scan_candidates(
        cls: type['ProactiveMessageService'],
        db: AsyncSession,
    ) -> int:
        now = cls._now()
        candidates = await ProactiveMessageDao.list_candidate_chats(db, config.proactive.scan_batch_size)
        scheduled = 0
        for chat, user, profile in candidates:
            reason = await cls._candidate_reason(db, chat, user, profile, now)
            if reason is None:
                continue
            deduplication_key = cls._deduplication_key(user.id, chat.id, reason, now)
            existing = await ProactiveMessageDao.get_by_deduplication_key(db, deduplication_key)
            if existing is not None:
                continue
            proactive_message = await ProactiveMessageDao.create(
                db,
                user.id,
                chat.id,
                reason,
                deduplication_key,
                now.replace(tzinfo=None),
            )
            await db.commit()
            if await cls._dispatch(db, proactive_message):
                scheduled += 1

        if config.memory.enabled and config.memory.event_followups_enabled:
            scheduled += await cls._scan_memory_event_followups(db, now)
        return scheduled

    @classmethod
    async def _dispatch(
        cls: type['ProactiveMessageService'],
        db: AsyncSession,
        proactive_message: ProactiveMessage,
    ) -> bool:
        task_id = str(uuid4())
        try:
            from app.tasks.proactive_task import process_proactive_message_task

            process_proactive_message_task.apply_async(
                args=[str(proactive_message.id)],
                task_id=task_id,
                queue='proactive',
            )
            proactive_message.celery_task_id = task_id
            await db.commit()
            RedisTaskService.save_state(str(proactive_message.id), task_id, 'queued')
            logger.info(
                'proactive_message_scheduled proactive_id=%s user_id=%s chat_id=%s reason=%s task_id=%s',
                proactive_message.id,
                proactive_message.user_id,
                proactive_message.chat_id,
                proactive_message.reason,
                task_id,
            )
            return True
        except Exception as error:
            await ProactiveMessageDao.mark_failed(db, proactive_message, str(error))
            await db.commit()
            logger.exception('proactive_message_dispatch_failed proactive_id=%s', proactive_message.id)
            return False

    @classmethod
    async def _scan_memory_event_followups(
        cls: type['ProactiveMessageService'],
        db: AsyncSession,
        now: datetime,
    ) -> int:
        due_events = await MemoryEventDao.list_due_followups(
            db,
            now.replace(tzinfo=None),
            config.memory.event_followup_scan_limit,
        )
        scheduled = 0
        for event in due_events:
            if event.sensitivity != 'normal':
                continue
            profile = await UserProfileDao.get(db, event.user_id)
            if profile is None or not profile.proactive_enabled or cls._is_quiet_hours(profile, now):
                continue
            since = (now - timedelta(days=1)).replace(tzinfo=None)
            sent_count = await ProactiveMessageDao.count_sent_since(db, event.user_id, since)
            if sent_count >= profile.daily_proactive_limit:
                continue
            deduplication_key = cls._memory_event_deduplication_key(event.id)
            existing = await ProactiveMessageDao.get_by_deduplication_key(db, deduplication_key)
            if existing is not None:
                continue
            proactive_message = await ProactiveMessageDao.create(
                db,
                event.user_id,
                event.chat_id,
                'event_follow_up',
                deduplication_key,
                now.replace(tzinfo=None),
                content=event.title,
                source_message_id=event.source_message_id,
            )
            await db.commit()
            if await cls._dispatch(db, proactive_message):
                scheduled += 1
        return scheduled

    @classmethod
    async def _candidate_reason(
        cls: type['ProactiveMessageService'],
        db: AsyncSession,
        chat: Chat,
        user: User,
        profile: UserProfile,
        now: datetime,
    ) -> Optional[str]:
        if not profile.proactive_enabled or cls._is_quiet_hours(profile, now):
            return None
        since = (now - timedelta(days=1)).replace(tzinfo=None)
        sent_count = await ProactiveMessageDao.count_sent_since(db, user.id, since)
        if sent_count >= profile.daily_proactive_limit:
            return None
        last_message = await ProactiveMessageDao.get_last_message(db, chat.id)
        return cls._reason(last_message, now)

    @classmethod
    def _event_for_proactive(
        cls: type['ProactiveMessageService'],
        proactive_message: ProactiveMessage,
    ) -> Optional[UUID]:
        if proactive_message.reason != 'event_follow_up':
            return None
        prefix = 'memory_event:'
        if not proactive_message.deduplication_key.startswith(prefix):
            return None
        try:
            return UUID(proactive_message.deduplication_key[len(prefix):])
        except ValueError:
            return None

    @classmethod
    async def process(
        cls: type['ProactiveMessageService'],
        db: AsyncSession,
        proactive_message_id: UUID,
        task_id: str,
    ) -> ProactiveMessage:
        proactive_message = await ProactiveMessageDao.get_by_id(db, proactive_message_id)
        if proactive_message is None:
            raise LookupError('Proactive message not found')
        if proactive_message.status == 'sent':
            return proactive_message
        context = await ProactiveMessageDao.get_context(db, proactive_message)
        if context is None:
            await ProactiveMessageDao.mark_skipped(db, proactive_message, 'chat or user not found')
            await db.commit()
            return proactive_message
        chat, user, profile = context
        character = await CharacterVersionDao.get_active(db, chat.boyfriend_id)
        if character is None:
            await ProactiveMessageDao.mark_skipped(db, proactive_message, 'active character not found')
            await db.commit()
            return proactive_message

        now = cls._now()
        memory_event: Optional[MemoryEvent] = None
        event_id = cls._event_for_proactive(proactive_message)

        if proactive_message.reason == 'event_follow_up':
            if event_id is None:
                await ProactiveMessageDao.mark_skipped(db, proactive_message, 'invalid memory event key')
                await db.commit()
                return proactive_message
            memory_event = await MemoryEventDao.get_by_id(db, event_id)
            if (
                memory_event is None
                or memory_event.status != 'active'
                or not memory_event.should_follow_up
                or memory_event.followed_up_at is not None
                or memory_event.follow_up_at is None
                or memory_event.follow_up_at > now.replace(tzinfo=None)
                or memory_event.sensitivity != 'normal'
                or not profile.proactive_enabled
                or cls._is_quiet_hours(profile, now)
            ):
                await ProactiveMessageDao.mark_skipped(db, proactive_message, 'event follow-up no longer applicable')
                await db.commit()
                return proactive_message
        elif proactive_message.reason != 'reminder':
            if await cls._candidate_reason(db, chat, user, profile, now) != proactive_message.reason:
                await ProactiveMessageDao.mark_skipped(db, proactive_message, 'conditions changed before send')
                await db.commit()
                return proactive_message

        await ProactiveMessageDao.mark_running(db, proactive_message, task_id)
        await db.commit()

        try:
            history = await MessageDao.list_for_chat(db, chat.id)
            prompt_messages = [
                {'role': item.role, 'content': item.content}
                for item in history[-8:]
                if item.status == 'completed'
                and item.role in {'user', 'assistant'}
                and getattr(item, 'memory_visibility', 'normal') != 'blocked'
            ]
            character_context = (
                'Follow the active character configuration, style and boundaries. '
                'Critical character settings override generic instructions.\n\n'
                + character.system_prompt
                + GenderAndAddressingService.build_context(profile, character)
                + CompanionPromptService.capability_policy()
            )

            if proactive_message.reason == 'reminder':
                original_message = None
                if proactive_message.source_message_id is not None:
                    original_message = await MessageDao.get_by_id(db, proactive_message.source_message_id)
                original_text = original_message.content if original_message is not None else proactive_message.content
                system_prompt = (
                    character_context
                    + '\n\nThe scheduled reminder is due now. Produce the final reminder message, not a confirmation '
                    'that a reminder was created. Mention the action directly. Do not describe implementation details '
                    'or promise to remind later. Do not claim the user already completed the action. '
                    'Use the user language and at most two sentences.\n'
                    f'Original request: {original_text}\n'
                    f'Action due now: {proactive_message.content}'
                )
                prompt_messages.append({
                    'role': 'user',
                    'content': 'The reminder is due now. Write one ready-to-send reminder message.',
                })
            elif proactive_message.reason == 'event_follow_up' and memory_event is not None:
                memory_context = await MemoryService.build_long_term_context(
                    db,
                    user.id,
                    memory_event.title,
                    now,
                )
                system_prompt = (
                    character_context
                    + '\n\nSend a short natural follow-up after an event from the user life. '
                    'Do not expose storage, tracking, triggers, internal memory or database mechanics. '
                    'Do not assume the outcome. Ask how it went or naturally return to the event. '
                    'Use the user language and at most two sentences.\n'
                    f'Event: {memory_event.title}.\n'
                    f'Participants: {", ".join(memory_event.participants or [])}.\n'
                    + MemoryService.render_prompt_context(memory_context)
                )
                prompt_messages.append({
                    'role': 'user',
                    'content': 'It is appropriate to return to this event now. Write the ready-to-send check-in.',
                })
            else:
                system_prompt = (
                    character_context
                    + '\n\nSend a short, low-pressure proactive message. '
                    'Keep it natural, use the user language, and use at most two sentences. '
                    f'Reason: {proactive_message.reason}.'
                )

            reply = await GeminiAIService.generate_reply(system_prompt, prompt_messages)
            assistant = await MessageDao.create(
                db,
                chat.id,
                'assistant',
                reply,
                platform=chat.platform,
                message_type='proactive',
                status='completed',
            )
            await db.commit()
            if chat.platform == 'telegram' and user.telegram_id is not None:
                from app.services.telegram_service import TelegramService

                await TelegramService.send_message(user.telegram_id, reply)

            await ProactiveMessageDao.mark_sent(
                db,
                proactive_message,
                assistant.id,
                cls._now().replace(tzinfo=None),
            )
            if memory_event is not None:
                await MemoryEventDao.mark_followed_up(
                    db,
                    memory_event,
                    cls._now().replace(tzinfo=None),
                )
            await db.commit()
            RedisTaskService.save_state(str(proactive_message.id), task_id, 'completed')
            logger.info(
                'proactive_message_sent proactive_id=%s assistant_id=%s',
                proactive_message.id,
                assistant.id,
            )
            return proactive_message
        except Exception as error:
            await ProactiveMessageDao.mark_failed(db, proactive_message, str(error))
            await db.commit()
            logger.exception('proactive_message_processing_failed proactive_id=%s', proactive_message.id)
            raise
