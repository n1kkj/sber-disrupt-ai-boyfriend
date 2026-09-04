from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.user_dao import UserDao
from app.database import get_db
from app.dependencies import current_user
from app.dto.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.models.user import User
from app.security import SecurityService
from app.services.auth_service import AuthService

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    try:
        token = await AuthService(UserDao(), SecurityService()).register(db, str(payload.email).lower(), payload.password, payload.display_name)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return AuthResponse(access_token=token)


@router.post('/login', response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    try:
        token = await AuthService(UserDao(), SecurityService()).login(db, str(payload.email).lower(), payload.password)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error))
    return AuthResponse(access_token=token)


@router.get('/me', response_model=UserResponse)
async def me(user: User = Depends(current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
