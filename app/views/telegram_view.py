from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.chat_service import ChatService
from app.services.telegram_service import TelegramService
from settings import config

router = APIRouter(prefix='/telegram', tags=['telegram'])


@router.post('/webhook')
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db), x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)) -> Dict[str, bool]:
    if config.telegram.webhook_secret and x_telegram_bot_api_secret_token != config.telegram.webhook_secret:
        raise HTTPException(status_code=403, detail='Invalid webhook secret')
    update: Dict[str, Any] = await request.json()
    message = update.get('message') or update.get('edited_message')
    if not message or not message.get('text') or not message.get('chat', {}).get('id'):
        return {'ok': True}
    telegram_chat_id = int(message['chat']['id'])
    telegram_user = message.get('from', {})
    chat = await TelegramService.get_or_create_chat(db, telegram_chat_id, telegram_user.get('username') or telegram_user.get('first_name'))
    try:
        _, answer = await ChatService.reply_to_message(db, chat.user_id, chat.id, str(message['text']))
        await TelegramService.send_message(telegram_chat_id, answer.content)
    except Exception:
        await db.rollback()
        await TelegramService.send_message(telegram_chat_id, 'Не получилось ответить. Попробуй еще раз через минуту.')
    return {'ok': True}


@router.post('/set-webhook')
async def telegram_set_webhook(webhook_url: str, x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)) -> Dict[str, bool]:
    if config.telegram.webhook_secret and x_telegram_bot_api_secret_token != config.telegram.webhook_secret:
        raise HTTPException(status_code=403, detail='Invalid webhook secret')
    await TelegramService.set_webhook(webhook_url)
    return {'ok': True}
