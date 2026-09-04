from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.dao.chat_dao import ChatDao
from app.dao.message_dao import MessageDao
from app.database import get_db
from app.dependencies import current_user
from app.dto.schemas import BoyfriendResponse, ChatCreateRequest, ChatResponse, MessageRequest, MessageResponse
from app.models.boyfriend import Boyfriend
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.services.boyfriend_service import BoyfriendService
from app.services.chat_service import ChatService
from app.services.gemini_service import GeminiService

router = APIRouter(tags=['chat'])


@router.get('/boyfriends', response_model=List[BoyfriendResponse])
async def list_boyfriends(db: AsyncSession = Depends(get_db)) -> List[Boyfriend]:
    return await BoyfriendService(BoyfriendDao()).list_active(db)


@router.post('/chats', response_model=ChatResponse, status_code=201)
async def create_chat(payload: ChatCreateRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> Chat:
    boyfriend = await BoyfriendDao().get_active(db, payload.boyfriend_id)
    if boyfriend is None:
        raise HTTPException(status_code=404, detail='Boyfriend not found')
    chat = await ChatDao().create(db, user.id, boyfriend.id, payload.title)
    return await ChatDao().commit(db, chat)


@router.get('/chats', response_model=List[ChatResponse])
async def list_chats(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Chat]:
    return await ChatDao().list_for_user(db, user.id)


@router.get('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def list_messages(chat_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Message]:
    chat_dao = ChatDao()
    if await chat_dao.get(db, user.id, chat_id) is None:
        raise HTTPException(status_code=404, detail='Chat not found')
    return await MessageDao().list_for_chat(db, chat_id)


@router.post('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def send_message(chat_id: UUID, payload: MessageRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Message]:
    service = ChatService(ChatDao(), MessageDao(), GeminiService())
    try:
        user_message, assistant_message = await service.reply_to_message(db, user.id, chat_id, payload.content)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return [user_message, assistant_message]
