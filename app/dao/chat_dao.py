from typing import List, Optional, Tuple
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boyfriend import Boyfriend
from app.models.chat import Chat
from app.models.base_model import Base


class ChatDao:
    @classmethod
    async def get(cls: type['ChatDao'], db: AsyncSession, user_id: UUID, chat_id: UUID) -> Optional[Chat]:
        return await db.scalar(sa.select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))

    @classmethod
    async def get_with_boyfriend(cls: type['ChatDao'], db: AsyncSession, user_id: UUID, chat_id: UUID) -> Optional[Tuple[Chat, Boyfriend]]:
        result = await db.execute(sa.select(Chat, Boyfriend).join(Boyfriend, Boyfriend.id == Chat.boyfriend_id).where(Chat.id == chat_id, Chat.user_id == user_id))
        return result.one_or_none()

    @classmethod
    async def list_for_user(cls: type['ChatDao'], db: AsyncSession, user_id: UUID) -> List[Chat]:
        result = await db.scalars(sa.select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc()))
        return list(result)

    @classmethod
    async def create(cls: type['ChatDao'], db: AsyncSession, user_id: UUID, boyfriend_id: UUID, title: Optional[str]) -> Chat:
        chat = Chat(user_id=user_id, boyfriend_id=boyfriend_id, title=title)
        db.add(chat)
        await db.flush()
        return chat

    @classmethod
    async def commit(cls: type['ChatDao'], db: AsyncSession, chat: Chat) -> Chat:
        await db.commit()
        await db.refresh(chat)
        return chat

    @classmethod
    async def get_first_for_user(cls: type['ChatDao'], db: AsyncSession, user_id: UUID) -> Optional[Chat]:
        return await db.scalar(sa.select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at).limit(1))

    @classmethod
    async def transfer_to_user(cls: type['ChatDao'], db: AsyncSession, source_user_id: UUID, target_user_id: UUID) -> None:
        await db.execute(sa.update(Chat).where(Chat.user_id == source_user_id).values(user_id=target_user_id))
        await db.flush()

    @classmethod
    async def touch(cls: type['ChatDao'], db: AsyncSession, chat_id: UUID) -> None:
        await db.execute(sa.update(Chat).where(Chat.id == chat_id).values(updated_at=Base.utcnow()))
        await db.flush()
