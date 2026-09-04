from typing import List
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageDao:
    async def list_for_chat(self, db: AsyncSession, chat_id: UUID) -> List[Message]:
        result = await db.scalars(sa.select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc()))
        return list(result)

    async def create(self, db: AsyncSession, chat_id: UUID, role: str, content: str) -> Message:
        message = Message(chat_id=chat_id, role=role, content=content)
        db.add(message)
        await db.flush()
        return message

    async def commit_pair(self, db: AsyncSession, first: Message, second: Message) -> tuple[Message, Message]:
        await db.commit()
        await db.refresh(first)
        await db.refresh(second)
        return first, second
