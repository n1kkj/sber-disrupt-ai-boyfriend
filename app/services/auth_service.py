from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.user_dao import UserDao
from app.dao.onboarding_dao import OnboardingDao
from app.dao.user_profile_dao import UserProfileDao
from app.logging import logger
from app.security import SecurityService


class AuthService:
    @classmethod
    async def register(cls: type['AuthService'], db: AsyncSession, email: str, password: str, display_name: Optional[str]) -> str:
        logger.info('auth_service_register_started')
        normalized_email = email.strip().casefold()
        if await UserDao.get_by_email(db, normalized_email) is not None:
            logger.warning('auth_service_register_duplicate')
            raise ValueError('Email already registered')
        user = await UserDao.create(db, normalized_email, SecurityService.hash_password(password), display_name)
        await UserProfileDao.ensure(db, user.id)
        await OnboardingDao.ensure(db, user.id)
        await UserDao.commit(db, user)
        logger.info('auth_service_register_completed user_id=%s', user.id)
        return SecurityService.create_access_token(str(user.id))

    @classmethod
    async def login(cls: type['AuthService'], db: AsyncSession, email: str, password: str) -> str:
        logger.info('auth_service_login_started')
        user = await UserDao.get_by_email(db, email.strip().casefold())
        if user is None or not SecurityService.verify_password(password, user.password_hash):
            logger.warning('auth_service_login_invalid_credentials')
            raise ValueError('Invalid email or password')
        if SecurityService.needs_password_rehash(user.password_hash):
            user.password_hash = SecurityService.hash_password(password)
            await UserDao.commit(db, user)
        logger.info('auth_service_login_completed user_id=%s', user.id)
        return SecurityService.create_access_token(str(user.id))
