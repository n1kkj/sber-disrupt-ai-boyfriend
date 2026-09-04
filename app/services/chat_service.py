from typing import Dict, List, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.chat_dao import ChatDao
from app.dao.message_dao import MessageDao
from app.models.message import Message
from app.services.gemini_service import GeminiService
from app.services.memory_service import MemoryService


class ChatService:
    @classmethod
    async def reply_to_message(cls: type['ChatService'], db: AsyncSession, user_id: UUID, chat_id: UUID, content: str) -> Tuple[Message, Message]:
        chat_boyfriend = await ChatDao.get_with_boyfriend(db, user_id, chat_id)
        if chat_boyfriend is None:
            raise LookupError('Chat not found')
        chat, boyfriend = chat_boyfriend
        history = await MessageDao.list_for_chat(db, chat.id)
        user_message = await MessageDao.create(db, chat.id, 'user', content)
        context = MemoryService.select_context(history + [user_message], content)
        prompt_messages: List[Dict[str, str]] = [{'role': item.role, 'content': item.content} for item in context]
        reply = await GeminiService.generate_reply(boyfriend.system_prompt, prompt_messages)
        assistant_message = await MessageDao.create(db, chat.id, 'assistant', reply)
        return await MessageDao.commit_pair(db, user_message, assistant_message)
