from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.boyfriend import BoyfriendResponse
from app.dto.chat import ChatCreateRequest, ChatResponse
from app.dto.message import MessageRequest, MessageResponse
from app.models.boyfriend import Boyfriend
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.services.boyfriend_service import BoyfriendService
from app.services.chat_service import ChatService
from app.services.message_service import MessageService

router = APIRouter(tags=['chat'])


@router.get('/boyfriends', response_model=List[BoyfriendResponse])
async def list_boyfriends(db: AsyncSession = Depends(get_db)) -> List[Boyfriend]:
    return await BoyfriendService.list_active(db)


@router.post('/chats', response_model=ChatResponse, status_code=201)
async def create_chat(payload: ChatCreateRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> Chat:
    try:
        return await ChatService.create_chat(db, user.id, payload.boyfriend_id, payload.title)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get('/chats', response_model=List[ChatResponse])
async def list_chats(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Chat]:
    return await ChatService.list_chats(db, user.id)


@router.get('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def list_messages(chat_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Message]:
    try:
        return await ChatService.list_messages(db, user.id, chat_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def send_message(
    chat_id: UUID,
    payload: MessageRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(default=None),
) -> List[Message]:
    try:
        user_message, assistant_message, _ = await MessageService.process_text(
            db,
            user.id,
            chat_id,
            payload.content,
            platform='web',
            idempotency_key=x_idempotency_key,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return [user_message, assistant_message]
