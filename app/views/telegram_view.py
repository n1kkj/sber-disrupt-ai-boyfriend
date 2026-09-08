from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging import logger
from app.services.telegram_service import TelegramService
from settings import config

router = APIRouter(prefix='/telegram', tags=['telegram'])


@router.post('/webhook')
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db), x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)) -> Dict[str, bool]:
    logger.info('telegram_webhook_received')
    if config.telegram.webhook_secret and x_telegram_bot_api_secret_token != config.telegram.webhook_secret:
        logger.warning('telegram_webhook_rejected reason=invalid_secret')
        raise HTTPException(status_code=403, detail='Invalid webhook secret')
    update: Dict[str, Any] = await request.json()
    await TelegramService.process_update(db, update)
    logger.info('telegram_webhook_processed update_id=%s', update.get('update_id'))
    return {'ok': True}


@router.post('/set-webhook')
async def telegram_set_webhook(webhook_url: str, x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)) -> Dict[str, bool]:
    logger.info('telegram_set_webhook_requested')
    if config.telegram.webhook_secret and x_telegram_bot_api_secret_token != config.telegram.webhook_secret:
        logger.warning('telegram_set_webhook_rejected reason=invalid_secret')
        raise HTTPException(status_code=403, detail='Invalid webhook secret')
    await TelegramService.set_webhook(webhook_url)
    return {'ok': True}
