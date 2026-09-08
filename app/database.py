from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import Request
from sqlalchemy.pool import NullPool

from app.logging import logger
from settings import config

async_engine = create_async_engine(
    config.sqlalchemy_database_url,
    echo=config.debug,
    future=True,
    poolclass=NullPool,
)

async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db(request: Request) -> AsyncSession:
    logger.debug('database_session_opened')
    try:
        async with request.app.state.db() as session:
            yield session
    except Exception:
        logger.exception('database_session_failed')
        raise
    finally:
        logger.debug('database_session_closed')
