import asyncio
import secrets
from typing import Optional

import requests
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.dao.chat_dao import ChatDao
from app.dao.user_dao import UserDao
from app.models.chat import Chat
from app.security import SecurityService
from settings import config


class TelegramService:
    @classmethod
    async def get_or_create_chat(cls: type['TelegramService'], db: AsyncSession, telegram_id: int, username: Optional[str]) -> Chat:
        user = await UserDao.get_by_telegram_id(db, telegram_id)
        if user is None:
            user = await UserDao.create(db, f'telegram_{telegram_id}@local.invalid', SecurityService.hash_password(secrets.token_urlsafe(24)), username, telegram_id)
        chat = await ChatDao.get_first_for_user(db, user.id)
        if chat is not None:
            return chat
        boyfriend = await BoyfriendDao.get_first_active(db)
        if boyfriend is None:
            raise RuntimeError('No active boyfriend configured')
        chat = await ChatDao.create(db, user.id, boyfriend.id, 'Telegram chat')
        return await ChatDao.commit(db, chat)

    @classmethod
    async def send_message(cls: type['TelegramService'], chat_id: int, text: str) -> None:
        if not config.telegram.bot_token:
            return
        await asyncio.to_thread(cls._send_message, chat_id, text)

    @classmethod
    def _send_message(cls: type['TelegramService'], chat_id: int, text: str) -> None:
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage', json={'chat_id': chat_id, 'text': text}, timeout=20).raise_for_status()

    @classmethod
    async def set_webhook(cls: type['TelegramService'], webhook_url: str) -> None:
        if not config.telegram.bot_token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
        await asyncio.to_thread(cls._set_webhook, webhook_url)

    @classmethod
    def _set_webhook(cls: type['TelegramService'], webhook_url: str) -> None:
        payload = {'url': webhook_url}
        if config.telegram.webhook_secret:
            payload['secret_token'] = config.telegram.webhook_secret
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/setWebhook', json=payload, timeout=20).raise_for_status()
