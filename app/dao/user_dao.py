from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserDao:
    @classmethod
    async def get_by_id(cls: type['UserDao'], db: AsyncSession, user_id: UUID) -> Optional[User]:
        return await db.scalar(sa.select(User).where(User.id == user_id))

    @classmethod
    async def get_by_email(cls: type['UserDao'], db: AsyncSession, email: str) -> Optional[User]:
        return await db.scalar(sa.select(User).where(User.email == email))

    @classmethod
    async def get_by_telegram_id(cls: type['UserDao'], db: AsyncSession, telegram_id: int) -> Optional[User]:
        return await db.scalar(sa.select(User).where(User.telegram_id == telegram_id))

    @classmethod
    async def create(cls: type['UserDao'], db: AsyncSession, email: str, password_hash: str, display_name: Optional[str], telegram_id: Optional[int] = None) -> User:
        user = User(email=email, password_hash=password_hash, display_name=display_name, telegram_id=telegram_id)
        db.add(user)
        await db.flush()
        return user

    @classmethod
    async def commit(cls: type['UserDao'], db: AsyncSession, user: User) -> User:
        await db.commit()
        await db.refresh(user)
        return user
