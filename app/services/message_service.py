import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.chat_dao import ChatDao
from app.dao.character_version_dao import CharacterVersionDao
from app.dao.memory_suppression_dao import MemorySuppressionDao
from app.dao.message_dao import MessageDao
from app.dao.onboarding_dao import OnboardingDao
from app.dao.user_profile_dao import UserProfileDao
from app.dao.user_dao import UserDao
from app.logging import logger
from app.models.message import Message
from app.services.companion_prompt_service import CompanionPromptService
from app.services.gemini_service import GeminiAIService
from app.services.gender_addressing_service import GenderAndAddressingService
from app.services.memory_service import MemoryService
from app.services.onboarding_service import OnboardingService
from app.services.redis_task_service import RedisTaskService
from app.services.reminder_service import ReminderService
from app.services.safety_service import SafetyService


class MessageService:
    @classmethod
    async def attach_external_id(
        cls: type['MessageService'],
        db: AsyncSession,
        message_id: UUID,
        external_id: str,
    ) -> None:
        message = await MessageDao.get_by_id(db, message_id)
        if message is None:
            raise LookupError('Message not found')
        await MessageDao.set_external_id(db, message, external_id)
        await db.commit()

    @classmethod
    async def enqueue_text(
        cls: type['MessageService'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        content: str,
        platform: str,
        external_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        message_type: str = 'text',
    ) -> Tuple[Message, Optional[Message], Optional[str], bool]:
        logger.info(
            'message_enqueue_started user_id=%s chat_id=%s platform=%s external_id_present=%s scheduled=%s',
            user_id,
            chat_id,
            platform,
            external_id is not None,
            scheduled_at is not None,
        )
        if await ChatDao.get_with_boyfriend(db, user_id, chat_id) is None:
            logger.warning('message_enqueue_chat_not_found user_id=%s chat_id=%s', user_id, chat_id)
            raise LookupError('Chat not found')
        if scheduled_at is not None:
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            if scheduled_at <= datetime.now(timezone.utc):
                raise ValueError('scheduled_at must be in the future')
        existing = await cls._find_existing(db, chat_id, platform, external_id, idempotency_key)
        if existing is not None:
            assistant = await MessageDao.get_reply(db, existing.id)
            if assistant is not None:
                logger.info('message_enqueue_duplicate_completed message_id=%s', existing.id)
                return existing, assistant, None, False
            if existing.status in {'queued', 'processing'}:
                task_id = await asyncio.to_thread(RedisTaskService.get_task_id, str(existing.id))
                logger.info(
                    'message_enqueue_duplicate_pending message_id=%s status=%s task_id=%s',
                    existing.id,
                    existing.status,
                    task_id,
                )
                return existing, None, task_id, False
            existing.status = 'queued'
            existing.error_message = None
            existing.message_type = message_type
            existing.scheduled_at = scheduled_at.replace(tzinfo=None) if scheduled_at is not None else None
            user_message = existing
        else:
            user_message = await MessageDao.create(
                db,
                chat_id,
                'user',
                content,
                platform=platform,
                external_id=external_id,
                idempotency_key=idempotency_key or str(uuid4()),
                message_type=message_type,
                status='queued',
                scheduled_at=scheduled_at.replace(tzinfo=None) if scheduled_at is not None else None,
            )
        await db.commit()
        await db.refresh(user_message)

        task_id = str(uuid4())
        await asyncio.to_thread(
            RedisTaskService.save_state,
            str(user_message.id),
            task_id,
            'queued',
        )
        try:
            from app.tasks.message_task import process_message_task

            process_message_task.apply_async(
                args=[str(user_message.id)],
                task_id=task_id,
                queue='messages',
                eta=scheduled_at,
            )
        except Exception as error:
            logger.exception('message_task_dispatch_failed message_id=%s task_id=%s', user_message.id, task_id)
            await MessageDao.mark_failed(db, user_message, str(error))
            await asyncio.to_thread(
                RedisTaskService.save_state,
                str(user_message.id),
                task_id,
                'failed',
                str(error),
            )
            raise
        logger.info('message_task_dispatched message_id=%s task_id=%s', user_message.id, task_id)
        return user_message, None, task_id, True

    @classmethod
    async def process_message(
        cls: type['MessageService'],
        db: AsyncSession,
        message_id: UUID,
    ) -> Tuple[Message, Optional[Message], Optional[int], bool]:
        logger.info('message_processing_started message_id=%s', message_id)
        message_data = await MessageDao.get_with_chat_boyfriend(db, message_id)
        if message_data is None:
            logger.warning('message_processing_not_found message_id=%s', message_id)
            raise LookupError('Message not found')
        message, chat, boyfriend = message_data
        user = await UserDao.get_by_id(db, chat.user_id)
        profile = await UserProfileDao.ensure(db, chat.user_id)
        onboarding = await OnboardingDao.get(db, chat.user_id)
        if onboarding is not None:
            onboarding_gender = onboarding.answers.get('companion_gender')
            if isinstance(onboarding_gender, str):
                if onboarding_gender != profile.companion_gender:
                    await UserProfileDao.sync_companion_from_onboarding(db, profile, onboarding_gender)
                await OnboardingService.sync_companion(db, chat.user_id, onboarding_gender)
                await db.commit()
                await db.refresh(profile)
                refreshed_message_data = await MessageDao.get_with_chat_boyfriend(db, message_id)
                if refreshed_message_data is not None:
                    message, chat, boyfriend = refreshed_message_data
                logger.info(
                    'message_profile_synced_from_onboarding user_id=%s companion_gender=%s',
                    chat.user_id,
                    profile.companion_gender,
                )
        character = await CharacterVersionDao.get_active(db, boyfriend.id)
        if character is None:
            character = await CharacterVersionDao.ensure_default(db, boyfriend.id, boyfriend.name, boyfriend.system_prompt)
        telegram_id = user.telegram_id if message.platform == 'telegram' and user is not None else None
        telegram_connected = user is not None and not user.is_telegram_only
        if message.status == 'cancelled':
            logger.info('message_processing_cancelled message_id=%s', message_id)
            return message, None, telegram_id, telegram_connected
        assistant = await MessageDao.get_reply(db, message.id)
        if assistant is not None:
            logger.info('message_processing_already_completed message_id=%s assistant_id=%s', message_id, assistant.id)
            return message, assistant, telegram_id, telegram_connected

        message.status = 'processing'
        message.error_message = None
        await db.commit()
        await db.refresh(message)

        try:
            safety = await SafetyService.check_input(message.content)
            if safety.decision != 'allow':
                await MessageDao.set_memory_visibility(db, message, 'blocked')
                if safety.decision == 'crisis':
                    reply_text = SafetyService.crisis_response()
                else:
                    reply_text = 'С этим запросом я не буду продолжать, но могу помочь перевести разговор в безопасное русло.'
                assistant = await MessageDao.create(
                    db,
                    chat.id,
                    'assistant',
                    reply_text,
                    platform=message.platform,
                    message_type='text',
                    status='completed',
                    reply_to_message_id=message.id,
                )
                await ChatDao.touch(db, chat.id)
                message, assistant = await MessageDao.commit_pair(db, message, assistant)
                logger.info('message_safety_handled message_id=%s decision=%s', message.id, safety.decision)
                return message, assistant, telegram_id, telegram_connected

            reminder = await ReminderService.analyze_and_schedule(db, chat, profile, message)
            history = await MessageDao.list_for_chat(db, chat.id)
            suppressions = await MemorySuppressionDao.list_for_user(db, chat.user_id)
            context = MemoryService.select_context(
                [item for item in history if item.status == 'completed'] + [message],
                message.content,
                suppressions=suppressions,
            )
            prompt_messages: List[Dict[str, str]] = [
                {'role': item.role, 'content': item.content}
                for item in context
                if item.role in {'user', 'assistant'}
            ]
            memory_context = await MemoryService.build_long_term_context(
                db,
                chat.user_id,
                message.content,
                datetime.now(timezone.utc),
            )
            system_prompt = (
                'Сначала определи стиль и пол компаньона по критическим настройкам ниже. '
                'Если базовый prompt противоречит им, всегда соблюдай критические настройки.\n\n'
                + character.system_prompt
                + GenderAndAddressingService.build_context(profile, character)
                + CompanionPromptService.capability_policy()
                + '\n\nПравила диалога Druk: отвечай естественно, спокойно и по делу. '
                'Если пользователь выговаривается, не спеши давать советы и не превращай разговор в терапию. '
                'Предпочитай одну уместную мысль длинному универсальному списку. Задавай вопрос только если он '
                'реально двигает разговор дальше. Не поощряй зависимость, эксклюзивность или изоляцию от близких.'
                + MemoryService.render_prompt_context(memory_context)
            )
            if reminder is not None:
                system_prompt += (
                    '\n\nСистемное событие: напоминание успешно создано и поставлено в очередь. '
                    f'Оно будет отправлено пользователю в запланированное время: {reminder.scheduled_at.isoformat()} UTC. '
                    'Обязательно подтверди пользователю, что ты напомнишь ему. Не говори, что у тебя нет технической возможности '
                    'отправлять сообщения по расписанию.'
                )
            reply_text = await GeminiAIService.generate_reply(system_prompt, prompt_messages)
            audit = await SafetyService.audit_output(message.content, reply_text, memory_context)
            if not audit.approved or audit.rewrite_needed:
                reply_text = await SafetyService.rewrite_output(message.content, reply_text, memory_context, audit)
        except Exception as error:
            logger.exception('message_ai_processing_failed message_id=%s', message_id)
            await MessageDao.mark_failed(db, message, str(error))
            raise

        assistant = await MessageDao.create(
            db,
            chat.id,
            'assistant',
            reply_text,
            platform=message.platform,
            message_type='text',
            status='completed',
            reply_to_message_id=message.id,
        )
        await ChatDao.touch(db, chat.id)
        message, assistant = await MessageDao.commit_pair(db, message, assistant)
        logger.info('message_processing_completed message_id=%s assistant_id=%s', message.id, assistant.id)
        return message, assistant, telegram_id, telegram_connected

    @classmethod
    async def cancel_message(
        cls: type['MessageService'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        message_id: UUID,
    ) -> Tuple[Message, Optional[str]]:
        logger.info('message_cancel_requested user_id=%s chat_id=%s message_id=%s', user_id, chat_id, message_id)
        if await ChatDao.get(db, user_id, chat_id) is None:
            logger.warning('message_cancel_chat_not_found user_id=%s chat_id=%s', user_id, chat_id)
            raise LookupError('Chat not found')
        message = await MessageDao.get_by_id(db, message_id)
        if message is None or message.chat_id != chat_id or message.role != 'user':
            logger.warning('message_cancel_not_found message_id=%s', message_id)
            raise LookupError('Message not found')
        task_id = await asyncio.to_thread(RedisTaskService.get_task_id, str(message.id))
        if message.status in {'queued', 'processing'}:
            message.status = 'cancelled'
            await db.commit()
            if task_id is not None:
                from app.celery_app import celery_app

                await asyncio.to_thread(celery_app.control.revoke, task_id, terminate=False)
            await asyncio.to_thread(
                RedisTaskService.save_state,
                str(message.id),
                task_id or '',
                'cancelled',
            )
            logger.info('message_cancelled message_id=%s task_id=%s', message.id, task_id)
        else:
            logger.info('message_cancel_ignored message_id=%s status=%s', message.id, message.status)
        return message, task_id

    @classmethod
    async def _find_existing(
        cls: type['MessageService'],
        db: AsyncSession,
        chat_id: UUID,
        platform: str,
        external_id: Optional[str],
        idempotency_key: Optional[str],
    ) -> Optional[Message]:
        if external_id is not None:
            existing = await MessageDao.get_by_external_id(db, platform, external_id)
            if existing is not None and existing.chat_id == chat_id:
                return existing
        if idempotency_key is not None:
            return await MessageDao.get_by_idempotency_key(db, chat_id, idempotency_key)
        return None
