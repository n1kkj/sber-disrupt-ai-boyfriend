from fastapi import APIRouter

from app.views.auth_view import router as auth_router
from app.views.chat_view import router as chat_router
from app.views.telegram_view import router as telegram_router
from app.views.onboarding_view import router as onboarding_router
from app.views.media_view import router as media_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix='/api/v1')
api_router.include_router(chat_router, prefix='/api/v1')
api_router.include_router(telegram_router, prefix='/api/v1')
api_router.include_router(onboarding_router, prefix='/api/v1')
api_router.include_router(media_router, prefix='/api/v1')
