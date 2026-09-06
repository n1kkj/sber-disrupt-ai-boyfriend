import asyncio
import json
import secrets
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.dao.boyfriend_dao import BoyfriendDao
from app.dao.chat_dao import ChatDao
from app.dao.user_dao import UserDao
from app.models.chat import Chat
from app.security import SecurityService
from app.services.chat_service import ChatService
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
    async def delete_webhook(cls: type['TelegramService']) -> None:
        if not config.telegram.bot_token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
        await asyncio.to_thread(cls._delete_webhook)

    @classmethod
    async def process_update(cls: type['TelegramService'], db: AsyncSession, update: Dict[str, Any]) -> None:
        message = update.get('message') or update.get('edited_message')
        if not message or not message.get('text') or not message.get('chat', {}).get('id'):
            return
        telegram_chat_id = int(message['chat']['id'])
        telegram_user = message.get('from', {})
        try:
            chat = await cls.get_or_create_chat(db, telegram_chat_id, telegram_user.get('username') or telegram_user.get('first_name'))
            _, answer = await ChatService.reply_to_message(db, chat.user_id, chat.id, str(message['text']))
            await cls.send_message(telegram_chat_id, answer.content)
        except Exception:
            await db.rollback()
            await cls.send_message(telegram_chat_id, 'Не получилось ответить. Попробуй еще раз через минуту.')

    @classmethod
    async def polling_loop(cls: type['TelegramService'], session_factory: async_sessionmaker, stop_event: asyncio.Event) -> None:
        offset = 0
        while not stop_event.is_set():
            try:
                updates = await asyncio.to_thread(cls._get_updates, offset)
                for update in updates:
                    offset = max(offset, int(update['update_id']) + 1)
                    async with session_factory() as session:
                        await cls.process_update(session, update)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(3)

    @classmethod
    def _set_webhook(cls: type['TelegramService'], webhook_url: str) -> None:
        payload = {'url': webhook_url}
        if config.telegram.webhook_secret:
            payload['secret_token'] = config.telegram.webhook_secret
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/setWebhook', json=payload, timeout=20).raise_for_status()

    @classmethod
    def _delete_webhook(cls: type['TelegramService']) -> None:
        requests.post(f'https://api.telegram.org/bot{config.telegram.bot_token}/deleteWebhook', timeout=20).raise_for_status()

    @classmethod
    def _get_updates(cls: type['TelegramService'], offset: int) -> List[Dict[str, Any]]:
        response = requests.get(
            f'https://api.telegram.org/bot{config.telegram.bot_token}/getUpdates',
            params={
                'offset': offset,
                'timeout': config.telegram.polling_timeout,
                'allowed_updates': json.dumps(['message', 'edited_message']),
            },
            timeout=config.telegram.polling_timeout + 10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('ok'):
            raise RuntimeError(f'Telegram getUpdates failed: {data}')
        return data.get('result', [])
