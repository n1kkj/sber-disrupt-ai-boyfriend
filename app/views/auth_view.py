from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.auth import AuthResponse, LoginRequest, RegisterRequest
from app.dto.telegram import TelegramClaimRequest, TelegramLinkResponse
from app.dto.user import UserResponse
from app.models.user import User
from app.services.account_link_service import AccountLinkService
from app.services.auth_service import AuthService
from settings import config

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    try:
        token = await AuthService.register(db, str(payload.email).lower(), payload.password, payload.display_name)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return AuthResponse(access_token=token)


@router.post('/login', response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    try:
        token = await AuthService.login(db, str(payload.email).lower(), payload.password)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error))
    return AuthResponse(access_token=token)


@router.get('/me', response_model=UserResponse)
async def me(user: User = Depends(current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post('/telegram/link', response_model=TelegramLinkResponse)
async def create_telegram_link(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> TelegramLinkResponse:
    if not config.telegram.bot_username:
        raise HTTPException(status_code=503, detail='TELEGRAM_BOT_USERNAME is not configured')
    token, expires_at = await AccountLinkService.create_for_user(db, user.id)
    return TelegramLinkResponse(url=f'https://t.me/{config.telegram.bot_username}?start=link_{token}', expires_at=expires_at)


@router.post('/telegram/claim', response_model=UserResponse)
async def claim_telegram_link(payload: TelegramClaimRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> UserResponse:
    try:
        linked_user = await AccountLinkService.claim_by_user(db, payload.token, user.id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return UserResponse.model_validate(linked_user)
