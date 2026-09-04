from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.user_dao import UserDao
from app.models.user import User
from app.security import SecurityService


class AuthService:
    def __init__(self, user_dao: UserDao, security_service: SecurityService) -> None:
        self.user_dao = user_dao
        self.security_service = security_service

    async def register(self, db: AsyncSession, email: str, password: str, display_name: Optional[str]) -> str:
        if await self.user_dao.get_by_email(db, email) is not None:
            raise ValueError('Email already registered')
        user = await self.user_dao.create(db, email, self.security_service.hash_password(password), display_name)
        await self.user_dao.commit(db, user)
        return self.security_service.create_access_token(str(user.id))

    async def login(self, db: AsyncSession, email: str, password: str) -> str:
        user = await self.user_dao.get_by_email(db, email)
        if user is None or not self.security_service.verify_password(password, user.password_hash):
            raise ValueError('Invalid email or password')
        return self.security_service.create_access_token(str(user.id))
