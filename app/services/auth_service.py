from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.user_dao import UserDao
from app.models.user import User
from app.security import SecurityService


class AuthService:
    @classmethod
    async def register(cls: type['AuthService'], db: AsyncSession, email: str, password: str, display_name: Optional[str]) -> str:
        if await UserDao.get_by_email(db, email) is not None:
            raise ValueError('Email already registered')
        user = await UserDao.create(db, email, SecurityService.hash_password(password), display_name)
        await UserDao.commit(db, user)
        return SecurityService.create_access_token(str(user.id))

    @classmethod
    async def login(cls: type['AuthService'], db: AsyncSession, email: str, password: str) -> str:
        user = await UserDao.get_by_email(db, email)
        if user is None or not SecurityService.verify_password(password, user.password_hash):
            raise ValueError('Invalid email or password')
        return SecurityService.create_access_token(str(user.id))
