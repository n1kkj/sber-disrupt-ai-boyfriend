import secrets
from typing import Any, Dict, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

import settings
from app.clients.telegram import send_message, set_webhook
from app.database import get_db
from app.models.entities import Boyfriend, Chat, User
from app.security import hash_password
from app.services.chat import reply_to_message

router = APIRouter(prefix='/telegram', tags=['telegram'])


async def _get_or_create_chat(db: AsyncSession, telegram_id: int, username: Optional[str]) -> Chat:
    user = await db.scalar(sa.select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(email=f'telegram_{telegram_id}@local.invalid', password_hash=hash_password(secrets.token_urlsafe(24)), display_name=username, telegram_id=telegram_id)
        db.add(user)
        await db.flush()
    boyfriend = await db.scalar(sa.select(Boyfriend).where(Boyfriend.is_active.is_(True)).order_by(Boyfriend.created_at).limit(1))
    if boyfriend is None:
        raise RuntimeError('No active boyfriend configured')
    chat = await db.scalar(sa.select(Chat).where(Chat.user_id == user.id).order_by(Chat.created_at).limit(1))
    if chat is None:
        chat = Chat(user_id=user.id, boyfriend_id=boyfriend.id, title='Telegram chat')
        db.add(chat)
        await db.flush()
    return chat


@router.post('/webhook')
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db), x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)) -> Dict[str, bool]:
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail='Invalid webhook secret')
    update: Dict[str, Any] = await request.json()
    message = update.get('message') or update.get('edited_message')
    if not message or not message.get('text') or not message.get('chat', {}).get('id'):
        return {'ok': True}
    telegram_chat_id = int(message['chat']['id'])
    telegram_user = message.get('from', {})
    chat = await _get_or_create_chat(db, telegram_chat_id, telegram_user.get('username') or telegram_user.get('first_name'))
    await db.commit()
    try:
        _, answer = await reply_to_message(db, chat.user_id, chat.id, str(message['text']))
        await send_message(telegram_chat_id, answer.content)
    except Exception:
        await db.rollback()
        await send_message(telegram_chat_id, 'Не получилось ответить. Попробуй еще раз через минуту.')
    return {'ok': True}


@router.post('/set-webhook')
async def telegram_set_webhook(webhook_url: str, x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)) -> Dict[str, bool]:
    if settings.TELEGRAM_WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail='Invalid webhook secret')
    await set_webhook(webhook_url)
    return {'ok': True}
