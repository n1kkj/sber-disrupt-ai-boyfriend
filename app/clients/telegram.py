import asyncio

import requests

import settings


def _send_message(chat_id: int, text: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    requests.post(
        f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage',
        json={'chat_id': chat_id, 'text': text},
        timeout=20,
    ).raise_for_status()


async def send_message(chat_id: int, text: str) -> None:
    await asyncio.to_thread(_send_message, chat_id, text)


def _set_webhook(webhook_url: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured')
    response = requests.post(
        f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook',
        json={
            'url': webhook_url,
            **({'secret_token': settings.TELEGRAM_WEBHOOK_SECRET} if settings.TELEGRAM_WEBHOOK_SECRET else {}),
        },
        timeout=20,
    )
    response.raise_for_status()


async def set_webhook(webhook_url: str) -> None:
    await asyncio.to_thread(_set_webhook, webhook_url)
