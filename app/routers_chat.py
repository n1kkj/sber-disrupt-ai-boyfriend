from typing import List
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.schemas import BoyfriendResponse, ChatCreateRequest, ChatResponse, MessageRequest, MessageResponse
from app.models.entities import Boyfriend, Chat, Message, User
from app.services.chat import reply_to_message

router = APIRouter(tags=['chat'])


@router.get('/boyfriends', response_model=List[BoyfriendResponse])
async def list_boyfriends(db: AsyncSession = Depends(get_db)) -> List[Boyfriend]:
    result = await db.scalars(sa.select(Boyfriend).where(Boyfriend.is_active.is_(True)).order_by(Boyfriend.name))
    return list(result)


@router.post('/chats', response_model=ChatResponse, status_code=201)
async def create_chat(payload: ChatCreateRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> Chat:
    boyfriend = await db.scalar(sa.select(Boyfriend).where(Boyfriend.id == payload.boyfriend_id, Boyfriend.is_active.is_(True)))
    if boyfriend is None:
        raise HTTPException(status_code=404, detail='Boyfriend not found')
    chat = Chat(user_id=user.id, boyfriend_id=boyfriend.id, title=payload.title)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


@router.get('/chats', response_model=List[ChatResponse])
async def list_chats(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Chat]:
    result = await db.scalars(sa.select(Chat).where(Chat.user_id == user.id).order_by(Chat.updated_at.desc()))
    return list(result)


@router.get('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def list_messages(chat_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Message]:
    if await db.scalar(sa.select(Chat.id).where(Chat.id == chat_id, Chat.user_id == user.id)) is None:
        raise HTTPException(status_code=404, detail='Chat not found')
    result = await db.scalars(sa.select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc()))
    return list(result)


@router.post('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def send_message(chat_id: UUID, payload: MessageRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Message]:
    try:
        user_message, assistant_message = await reply_to_message(db, user.id, chat_id, payload.content)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return [user_message, assistant_message]
