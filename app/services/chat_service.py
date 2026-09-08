from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.dao.chat_dao import ChatDao
from app.dao.message_dao import MessageDao
from app.models.boyfriend import Boyfriend
from app.models.chat import Chat
from app.models.message import Message
from app.logging import logger


class ChatService:
    @classmethod
    async def create_chat(
        cls: type['ChatService'],
        db: AsyncSession,
        user_id: UUID,
        boyfriend_id: UUID,
        title: Optional[str],
    ) -> Chat:
        boyfriend = await BoyfriendDao.get_active(db, boyfriend_id)
        if boyfriend is None:
            logger.warning('chat_service_boyfriend_not_found boyfriend_id=%s', boyfriend_id)
            raise LookupError('Boyfriend not found')
        chat = await ChatDao.create(db, user_id, boyfriend.id, title)
        chat = await ChatDao.commit(db, chat)
        logger.info('chat_service_created chat_id=%s user_id=%s', chat.id, user_id)
        return chat

    @classmethod
    async def list_chats(cls: type['ChatService'], db: AsyncSession, user_id: UUID) -> List[Chat]:
        return await ChatDao.list_for_user(db, user_id)

    @classmethod
    async def list_messages(cls: type['ChatService'], db: AsyncSession, user_id: UUID, chat_id: UUID) -> List[Message]:
        if await ChatDao.get(db, user_id, chat_id) is None:
            raise LookupError('Chat not found')
        return await MessageDao.list_for_chat(db, chat_id)
