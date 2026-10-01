import json
import re
import secrets
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.character_version_dao import CharacterVersionDao
from app.dao.reaction_event_dao import ReactionEventDao
from app.logging import logger
from app.models.chat import Chat
from app.models.character_version import CharacterVersion
from app.models.message import Message
from app.models.reaction_event import ReactionEvent
from app.models.user_profile import UserProfile
from app.services.companion_prompt_service import CompanionPromptService
from app.services.gender_addressing_service import GenderAndAddressingService
from app.services.gemini_service import GeminiAIService
from settings import config


class ReactionService:
    _titles = {
        '👍': 'like',
        '👎': 'dislike',
        '❤': 'love',
        '❤️': 'love',
        '🔥': 'fire',
        '😂': 'funny',
        '😢': 'sad',
        '😡': 'angry',
        '🤔': 'thoughtful',
        '🎉': 'celebration',
        '🥰': 'affection',
        '😍': 'admiration',
        '😘': 'kiss',
        '👏': 'applause',
        '🙏': 'gratitude',
        '💯': 'approval',
        '✨': 'sparkle',
        '😎': 'cool',
        '🙈': 'shy',
        '😮': 'surprise',
        '🤗': 'hug',
        '💔': 'heartbreak',
        '😴': 'sleepy',
        '🤍': 'white_love',
        '💖': 'sparkling_love',
        '🌟': 'star',
    }
    _allowed_emojis = tuple(_titles.keys())

    @classmethod
    def title_for_emoji(cls: type['ReactionService'], emoji: str) -> str:
        return cls._titles.get(emoji, 'other')

    @classmethod
    async def process_telegram_update(
        cls: type['ReactionService'],
        db: AsyncSession,
        user_id: UUID,
        chat: Chat,
        update: Dict[str, Any],
    ) -> int:
        reaction_update = update.get('message_reaction') or {}
        telegram_chat_id = reaction_update.get('chat', {}).get('id')
        telegram_message_id = reaction_update.get('message_id')
        if telegram_chat_id is None or telegram_message_id is None:
            return 0
        external_message_id = f'{telegram_chat_id}:{telegram_message_id}'
        message = await ReactionEventDao.get_message_for_user(
            db,
            user_id,
            chat.id,
            external_message_id,
        )
        if message is None:
            logger.warning('Реакция Telegram не сопоставлена message_id=%s', telegram_message_id)
            return 0
        old_reactions = cls._extract_emojis(reaction_update.get('old_reaction'))
        new_reactions = cls._extract_emojis(reaction_update.get('new_reaction'))
        events_count = 0
        for emoji in old_reactions:
            if emoji not in new_reactions:
                event = await cls._create_event(
                    db,
                    user_id,
                    chat.id,
                    message.id,
                    'user',
                    'remove',
                    emoji,
                    f'telegram:{update.get("update_id")}:{telegram_message_id}:remove:{emoji}',
                )
                events_count += int(event is not None)
        for emoji in new_reactions:
            if emoji not in old_reactions:
                event = await cls._create_event(
                    db,
                    user_id,
                    chat.id,
                    message.id,
                    'user',
                    'add',
                    emoji,
                    f'telegram:{update.get("update_id")}:{telegram_message_id}:add:{emoji}',
                )
                events_count += int(event is not None)
        await db.commit()
        logger.info('Реакции пользователя сохранены chat_id=%s count=%s', chat.id, events_count)
        return events_count

    @classmethod
    async def react_to_user_message(
        cls: type['ReactionService'],
        db: AsyncSession,
        message: Message,
        chat: Chat,
        profile: UserProfile,
        telegram_chat_id: int,
        allow_sticker: bool = True,
    ) -> Optional[ReactionEvent]:
        if message.platform != 'telegram' or message.role != 'user' or not message.external_id:
            return None
        character = await CharacterVersionDao.get_active(db, chat.boyfriend_id)
        if character is None:
            return None
        decision = await cls._choose_reaction(character, profile, message.content)
        emoji = decision.get('emoji')
        should_react = decision.get('should_react') is True and emoji in cls._allowed_emojis
        should_send_sticker = allow_sticker and decision.get('send_sticker') is True
        sticker_file_ids = [item.strip() for item in config.telegram.sticker_file_ids.split(',') if item.strip()]
        if not should_react and not (should_send_sticker and sticker_file_ids):
            return None
        telegram_message_id = cls._telegram_message_id(message.external_id)
        if telegram_message_id is None:
            return None
        from app.services.telegram_service import TelegramService

        event = None
        if should_react:
            await TelegramService.set_message_reaction(telegram_chat_id, telegram_message_id, emoji)
            external_event_id = f'model:{message.id}:{emoji}'
            event = await cls._create_event(
                db,
                chat.user_id,
                chat.id,
                message.id,
                'assistant',
                'add',
                emoji,
                external_event_id,
                {'source': 'model', 'reason': decision.get('reason', '')},
            )
        if should_send_sticker and sticker_file_ids:
            await TelegramService.send_sticker(
                telegram_chat_id,
                secrets.choice(sticker_file_ids),
                telegram_message_id,
            )
        await db.commit()
        return event

    @classmethod
    async def build_shadow_context(
        cls: type['ReactionService'],
        db: AsyncSession,
        chat_id: UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        events = await ReactionEventDao.list_for_chat(db, chat_id, limit)
        return [
            {
                'event': 'reaction',
                'actor_type': event.actor_type,
                'event_type': event.event_type,
                'title': event.title,
                'emoji': event.emoji,
                'message_id': str(event.message_id),
                'created_at': event.created_at.isoformat(),
            }
            for event in reversed(events)
        ]

    @classmethod
    async def _choose_reaction(
        cls: type['ReactionService'],
        character: CharacterVersion,
        profile: UserProfile,
        user_text: str,
    ) -> Dict[str, Any]:
        system_prompt = (
            character.system_prompt
            + GenderAndAddressingService.build_context(profile, character)
            + CompanionPromptService.capability_policy()
            + '\n\nОпредели, уместно ли персонажу поставить реакцию на сообщение пользователя. '
            'Выбирай реакцию только если она естественно отражает эмоцию персонажа. '
            'Верни только один JSON без текста до и после: '
            '{"should_react":true,"emoji":"👍","send_sticker":false,"reason":"..."}. '
            f'Допустимые emoji: {", ".join(cls._allowed_emojis)}. '
            'Разнообразь уместные реакции и не выбирай постоянно один и тот же emoji. '
            'Стикер предлагай только при сильной эмоциональной уместности. '
            'Если реакция и стикер не нужны, верни {"should_react":false,"send_sticker":false}. '
        )
        try:
            result = await GeminiAIService.generate_reply(
                system_prompt,
                [{'role': 'user', 'content': user_text}],
            )
            cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', result.strip(), flags=re.IGNORECASE)
            object_start = cleaned.find('{')
            if object_start < 0:
                raise ValueError('В ответе модели не найден JSON')
            parsed, _ = json.JSONDecoder().raw_decode(cleaned[object_start:])
            return parsed if isinstance(parsed, dict) else {'should_react': False}
        except Exception:
            logger.exception('Не удалось определить реакцию персонажа')
            return {'should_react': False}

    @classmethod
    async def _create_event(
        cls: type['ReactionService'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        message_id: UUID,
        actor_type: str,
        event_type: str,
        emoji: str,
        external_event_id: str,
        metadata_json: Optional[dict] = None,
    ) -> Optional[ReactionEvent]:
        existing = await ReactionEventDao.get_by_external_id(db, external_event_id)
        if existing is not None:
            return None
        return await ReactionEventDao.create(
            db,
            user_id,
            chat_id,
            message_id,
            actor_type,
            event_type,
            emoji,
            cls.title_for_emoji(emoji),
            external_event_id,
            metadata_json,
        )

    @classmethod
    def _extract_emojis(cls: type['ReactionService'], reactions: Any) -> List[str]:
        if not isinstance(reactions, list):
            return []
        return [
            item.get('emoji')
            for item in reactions
            if isinstance(item, dict) and item.get('type') == 'emoji' and item.get('emoji') in cls._allowed_emojis
        ]

    @classmethod
    def _telegram_message_id(cls: type['ReactionService'], external_id: str) -> Optional[int]:
        try:
            return int(external_id.rsplit(':', 1)[-1])
        except ValueError:
            return None
