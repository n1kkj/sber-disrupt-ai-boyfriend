from fastapi import APIRouter

from app.routers_auth import router as auth_router
from app.routers_chat import router as chat_router
from app.routers_telegram import router as telegram_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix='/api/v1')
api_router.include_router(chat_router, prefix='/api/v1')
api_router.include_router(telegram_router, prefix='/api/v1')
