import asyncio
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.dao.boyfriend_dao import BoyfriendDao
from app.database import async_engine, async_session
from app.logging import logger
from app.middleware import RequestLoggingMiddleware
from app.models.base_model import Base
from app.services.telegram_service import TelegramService
from app.views.router import api_router
from settings import config


class ApplicationLifecycle:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    @asynccontextmanager
    async def __call__(self, main_app: FastAPI) -> AsyncIterator[None]:
        logger.info('application_starting mode=%s debug=%s', config.telegram.mode, config.debug)
        polling_task = None
        stop_event = asyncio.Event()
        try:
            async with async_engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            logger.info('database_schema_ready')
            main_app.state.db = self.session_factory
            async with self.session_factory() as session:
                await BoyfriendDao.ensure_default_pair(session)
            logger.info('default_companion_ready')
            if config.telegram.mode.lower() == 'polling':
                if not config.telegram.bot_token:
                    logger.error('polling_start_failed reason=telegram_bot_token_missing')
                    raise RuntimeError('TELEGRAM_BOT_TOKEN is required when TELEGRAM_MODE=polling')
                polling_task = asyncio.create_task(TelegramService.polling_loop(self.session_factory, stop_event))
                logger.info('telegram_polling_started')
            yield
            logger.info('application_shutdown_started')
        except Exception:
            logger.exception('application_lifecycle_failed')
            raise
        finally:
            if polling_task is not None:
                stop_event.set()
                polling_task.cancel()
                with suppress(asyncio.CancelledError):
                    await polling_task
                logger.info('telegram_polling_stopped')
            logger.info('application_stopped')


app = FastAPI(title=config.app_title, debug=config.debug, lifespan=ApplicationLifecycle(async_session))
app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
