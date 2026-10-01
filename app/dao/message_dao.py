from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boyfriend import Boyfriend
from app.models.chat import Chat
from app.models.message import Message


class MessageDao:
    @classmethod
    async def get_by_id(cls: type['MessageDao'], db: AsyncSession, message_id: UUID) -> Optional[Message]:
        return await db.scalar(sa.select(Message).where(Message.id == message_id))

    @classmethod
    async def get_with_chat_boyfriend(
        cls: type['MessageDao'],
        db: AsyncSession,
        message_id: UUID,
    ) -> Optional[Tuple[Message, Chat, Boyfriend]]:
        result = await db.execute(
            sa.select(Message, Chat, Boyfriend)
            .join(Chat, Chat.id == Message.chat_id)
            .join(Boyfriend, Boyfriend.id == Chat.boyfriend_id)
            .where(Message.id == message_id)
        )
        return result.one_or_none()

    @classmethod
    async def list_for_chat(cls: type['MessageDao'], db: AsyncSession, chat_id: UUID) -> List[Message]:
        result = await db.scalars(sa.select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc()))
        return list(result)

    @classmethod
    async def list_recent_assistant_for_chat(
        cls: type['MessageDao'],
        db: AsyncSession,
        chat_id: UUID,
        limit: int = 5,
    ) -> List[Message]:
        result = await db.scalars(
            sa.select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.role == 'assistant',
                Message.status == 'completed',
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(result)

    @classmethod
    async def get_by_external_id(cls: type['MessageDao'], db: AsyncSession, platform: str, external_id: str) -> Optional[Message]:
        return await db.scalar(sa.select(Message).where(Message.platform == platform, Message.external_id == external_id))

    @classmethod
    async def get_by_idempotency_key(cls: type['MessageDao'], db: AsyncSession, chat_id: UUID, idempotency_key: str) -> Optional[Message]:
        return await db.scalar(sa.select(Message).where(Message.chat_id == chat_id, Message.idempotency_key == idempotency_key))

    @classmethod
    async def get_reply(cls: type['MessageDao'], db: AsyncSession, message_id: UUID) -> Optional[Message]:
        return await db.scalar(sa.select(Message).where(Message.reply_to_message_id == message_id, Message.role == 'assistant'))

    @classmethod
    async def is_telegram_reply_delivered(cls: type['MessageDao'], db: AsyncSession, message_id: UUID) -> bool:
        message = await cls.get_by_id(db, message_id)
        if message is None or message.platform != 'telegram':
            return False
        reply = await cls.get_reply(db, message_id)
        return reply is not None and reply.external_id is not None

    @classmethod
    async def count_recent_user_messages(
        cls: type['MessageDao'],
        db: AsyncSession,
        chat_id: UUID,
        created_at: datetime,
        window_seconds: int = 5,
    ) -> int:
        result = await db.scalar(
            sa.select(sa.func.count(Message.id)).where(
                Message.chat_id == chat_id,
                Message.role == 'user',
                Message.created_at >= created_at - timedelta(seconds=window_seconds),
                Message.created_at <= created_at,
            )
        )
        return int(result or 0)

    @classmethod
    async def create(
        cls: type['MessageDao'],
        db: AsyncSession,
        chat_id: UUID,
        role: str,
        content: str,
        platform: str = 'web',
        external_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        message_type: str = 'text',
        status: str = 'completed',
        reply_to_message_id: Optional[UUID] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Message:
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            platform=platform,
            external_id=external_id,
            idempotency_key=idempotency_key,
            message_type=message_type,
            status=status,
            reply_to_message_id=reply_to_message_id,
            scheduled_at=scheduled_at,
        )
        db.add(message)
        await db.flush()
        return message

    @classmethod
    async def mark_failed(cls: type['MessageDao'], db: AsyncSession, message: Message, error_message: str) -> Message:
        message.status = 'failed'
        message.error_message = error_message[:2000]
        await db.commit()
        await db.refresh(message)
        return message

    @classmethod
    async def set_external_id(
        cls: type['MessageDao'],
        db: AsyncSession,
        message: Message,
        external_id: str,
    ) -> Message:
        message.external_id = external_id
        await db.flush()
        return message

    @classmethod
    async def set_memory_visibility(
        cls: type['MessageDao'],
        db: AsyncSession,
        message: Message,
        visibility: str,
    ) -> Message:
        if visibility not in {'normal', 'short_term_only', 'blocked'}:
            raise ValueError('Unknown memory visibility')
        message.memory_visibility = visibility
        await db.flush()
        return message

    @classmethod
    async def commit_pair(cls: type['MessageDao'], db: AsyncSession, first: Message, second: Message) -> tuple[Message, Message]:
        first.status = 'completed'
        second.status = 'completed'
        await db.commit()
        await db.refresh(first)
        await db.refresh(second)
        return first, second
