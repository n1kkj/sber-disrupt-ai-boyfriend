from contextlib import asynccontextmanager
import uvicorn
import sqlalchemy as sa
from fastapi import FastAPI

from app.database import async_engine, async_session
from app.models.base_model import Base
from app.models import Boyfriend
from settings import APP_CONFIG
from app.routers import api_router


@asynccontextmanager
async def lifespan(main_app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    main_app.state.db = async_session
    async with async_session() as session:
        if await session.scalar(sa.select(Boyfriend).limit(1)) is None:
            session.add(Boyfriend(
                name='Алекс',
                description='Заботливый, внимательный и с хорошим чувством юмора.',
                system_prompt='Ты Алекс, заботливый виртуальный бойфренд. Общайся тепло, уважительно и естественно на языке пользователя. Не выдавай себя за реального человека, не поощряй зависимость и не обесценивай чувства. Если пользователь сообщает о непосредственной опасности или самоповреждении, мягко рекомендуй обратиться к близким и экстренным службам. Отвечай коротко, живо и по делу.',
            ))
            await session.commit()
    yield


APP_CONFIG['lifespan'] = lifespan

app = FastAPI(**APP_CONFIG)
app.include_router(api_router)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
