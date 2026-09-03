from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import Request

import settings

async_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.db() as session:
        yield session
