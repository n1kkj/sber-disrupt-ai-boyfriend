from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.dao.chat_dao import ChatDao
from app.dao.message_dao import MessageDao
from app.models.message import Message
from app.services.gemini_service import GeminiAIService
from app.services.memory_service import MemoryService


class MessageService:
    @classmethod
    async def process_text(
        cls: type['MessageService'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        content: str,
        platform: str,
        external_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Message, Message, bool]:
        chat_boyfriend = await ChatDao.get_with_boyfriend(db, user_id, chat_id)
        if chat_boyfriend is None:
            raise LookupError('Chat not found')
        chat, boyfriend = chat_boyfriend
        existing = await cls._find_existing(db, chat_id, platform, external_id, idempotency_key)
        if existing is not None:
            reply = await MessageDao.get_reply(db, existing.id)
            if reply is not None:
                return existing, reply, False
            if existing.status == 'failed':
                existing.status = 'processing'
                existing.error_message = None
                await db.commit()
                await db.refresh(existing)
                user_message = existing
            else:
                raise RuntimeError('Message is already being processed')
        else:
            normalized_key = idempotency_key or str(uuid4())
            user_message = await MessageDao.create(
                db,
                chat_id,
                'user',
                content,
                platform=platform,
                external_id=external_id,
                idempotency_key=normalized_key,
                status='processing',
            )
            try:
                await db.commit()
            except IntegrityError as error:
                await db.rollback()
                duplicate = await cls._find_existing(db, chat_id, platform, external_id, idempotency_key)
                if duplicate is not None:
                    duplicate_reply = await MessageDao.get_reply(db, duplicate.id)
                    if duplicate_reply is not None:
                        return duplicate, duplicate_reply, False
                raise RuntimeError('Message with this idempotency key is already being processed') from error
            await db.refresh(user_message)

        try:
            history = await MessageDao.list_for_chat(db, chat.id)
            context = MemoryService.select_context(
                [item for item in history if item.status == 'completed'] + [user_message],
                content,
            )
            prompt_messages: List[Dict[str, str]] = [
                {'role': item.role, 'content': item.content}
                for item in context
                if item.role in {'user', 'assistant'}
            ]
            reply_text = await GeminiAIService.generate_reply(boyfriend.system_prompt, prompt_messages)
        except Exception as error:
            await MessageDao.mark_failed(db, user_message, str(error))
            raise

        assistant_message = await MessageDao.create(
            db,
            chat.id,
            'assistant',
            reply_text,
            platform=platform,
            message_type='text',
            status='completed',
            reply_to_message_id=user_message.id,
        )
        await ChatDao.touch(db, chat.id)
        user_message, assistant_message = await MessageDao.commit_pair(db, user_message, assistant_message)
        return user_message, assistant_message, True

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
