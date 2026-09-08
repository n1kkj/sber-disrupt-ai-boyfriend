from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.boyfriend import BoyfriendResponse
from app.dto.chat import ChatCreateRequest, ChatResponse
from app.dto.message import MessageRequest, MessageResponse, MessageTaskResponse
from app.logging import logger
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
    logger.info('chat_create_started user_id=%s boyfriend_id=%s', user.id, payload.boyfriend_id)
    try:
        chat = await ChatService.create_chat(db, user.id, payload.boyfriend_id, payload.title)
    except LookupError as error:
        logger.warning('chat_create_rejected user_id=%s reason=%s', user.id, error)
        raise HTTPException(status_code=404, detail=str(error))
    logger.info('chat_create_completed user_id=%s chat_id=%s', user.id, chat.id)
    return chat


@router.get('/chats', response_model=List[ChatResponse])
async def list_chats(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Chat]:
    return await ChatService.list_chats(db, user.id)


@router.get('/chats/{chat_id}/messages', response_model=List[MessageResponse])
async def list_messages(chat_id: UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> List[Message]:
    try:
        return await ChatService.list_messages(db, user.id, chat_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post('/chats/{chat_id}/messages', response_model=MessageTaskResponse, status_code=202)
async def send_message(
    chat_id: UUID,
    payload: MessageRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    x_idempotency_key: Optional[str] = Header(default=None),
) -> MessageTaskResponse:
    logger.info('chat_message_request_started user_id=%s chat_id=%s', user.id, chat_id)
    try:
        user_message, assistant_message, task_id, _ = await MessageService.enqueue_text(
            db,
            user.id,
            chat_id,
            payload.content,
            platform='web',
            idempotency_key=x_idempotency_key,
            scheduled_at=payload.scheduled_at,
        )
    except LookupError as error:
        logger.warning('chat_message_request_rejected chat_id=%s reason=%s', chat_id, error)
        raise HTTPException(status_code=404, detail=str(error))
    except RuntimeError as error:
        logger.error('chat_message_dispatch_failed chat_id=%s reason=%s', chat_id, error)
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        logger.warning('chat_message_request_invalid chat_id=%s reason=%s', chat_id, error)
        raise HTTPException(status_code=400, detail=str(error))
    logger.info('chat_message_request_accepted message_id=%s task_id=%s', user_message.id, task_id)
    return MessageTaskResponse(
        message=user_message,
        task_id=task_id,
        task_status='completed' if assistant_message is not None else user_message.status,
    )


@router.post('/chats/{chat_id}/messages/{message_id}/cancel', response_model=MessageTaskResponse)
async def cancel_message(
    chat_id: UUID,
    message_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageTaskResponse:
    logger.info('chat_message_cancel_started user_id=%s chat_id=%s message_id=%s', user.id, chat_id, message_id)
    try:
        message, task_id = await MessageService.cancel_message(db, user.id, chat_id, message_id)
    except LookupError as error:
        logger.warning('chat_message_cancel_rejected message_id=%s reason=%s', message_id, error)
        raise HTTPException(status_code=404, detail=str(error))
    logger.info('chat_message_cancel_completed message_id=%s task_id=%s status=%s', message_id, task_id, message.status)
    return MessageTaskResponse(message=message, task_id=task_id, task_status=message.status)
