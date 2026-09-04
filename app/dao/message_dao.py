from typing import List
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageDao:
    @classmethod
    async def list_for_chat(cls: type['MessageDao'], db: AsyncSession, chat_id: UUID) -> List[Message]:
        result = await db.scalars(sa.select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc()))
        return list(result)

    @classmethod
    async def create(cls: type['MessageDao'], db: AsyncSession, chat_id: UUID, role: str, content: str) -> Message:
        message = Message(chat_id=chat_id, role=role, content=content)
        db.add(message)
        await db.flush()
        return message

    @classmethod
    async def commit_pair(cls: type['MessageDao'], db: AsyncSession, first: Message, second: Message) -> tuple[Message, Message]:
        await db.commit()
        await db.refresh(first)
        await db.refresh(second)
        return first, second
