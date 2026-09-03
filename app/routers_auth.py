import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import current_user
from app.dto.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.models.entities import User
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    email = str(payload.email).lower()
    if await db.scalar(sa.select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail='Email already registered')
    user = User(email=email, password_hash=hash_password(payload.password), display_name=payload.display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthResponse(access_token=create_access_token(str(user.id)))


@router.post('/login', response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = await db.scalar(sa.select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password')
    return AuthResponse(access_token=create_access_token(str(user.id)))


@router.get('/me', response_model=UserResponse)
async def me(user: User = Depends(current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
