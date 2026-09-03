from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI

from app.database import async_engine, async_session
from app.models.base_model import Base
from settings import APP_CONFIG
from app.routers import api_router


@asynccontextmanager
async def lifespan(main_app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    main_app.state.db = async_session
    yield


APP_CONFIG['lifespan'] = lifespan

app = FastAPI(**APP_CONFIG)
app.include_router(api_router)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
