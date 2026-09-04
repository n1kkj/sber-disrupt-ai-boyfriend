from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.dao.boyfriend_dao import BoyfriendDao
from app.database import async_engine, async_session
from app.models.base_model import Base
from app.views.router import api_router
from settings import config


class ApplicationLifecycle:
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __call__(self, main_app: FastAPI) -> AsyncIterator[None]:
        async with async_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        main_app.state.db = self.session_factory
        async with self.session_factory() as session:
            await BoyfriendDao().ensure_default(session)
        yield


app = FastAPI(title=config.app_title, debug=config.debug, lifespan=ApplicationLifecycle(async_session))
app.include_router(api_router)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
