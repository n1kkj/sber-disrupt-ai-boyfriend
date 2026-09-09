import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.boyfriend_dao import BoyfriendDao
from app.dao.chat_dao import ChatDao
from app.dao.telegram_link_token_dao import TelegramLinkTokenDao
from app.dao.user_dao import UserDao
from app.dao.onboarding_dao import OnboardingDao
from app.dao.user_profile_dao import UserProfileDao
from app.models.telegram_link_token import TelegramLinkToken
from app.models.user import User
from app.models.base_model import Base
from app.logging import logger
from settings import config


class AccountLinkService:
    @classmethod
    async def create_for_user(cls: type['AccountLinkService'], db: AsyncSession, user_id: UUID) -> Tuple[str, datetime]:
        logger.info('account_link_token_created_for_user user_id=%s', user_id)
        raw_token = secrets.token_urlsafe(32)
        expires_at = Base.utcnow() + timedelta(minutes=config.telegram.link_token_ttl_minutes)
        token = await TelegramLinkTokenDao.create(db, cls._hash_token(raw_token), expires_at, user_id=user_id)
        await TelegramLinkTokenDao.commit(db, token)
        return raw_token, expires_at

    @classmethod
    async def create_for_telegram(cls: type['AccountLinkService'], db: AsyncSession, telegram_id: int) -> Tuple[str, datetime]:
        logger.info('account_link_token_created_for_telegram chat_suffix=%s', str(telegram_id)[-4:])
        raw_token = secrets.token_urlsafe(32)
        expires_at = Base.utcnow() + timedelta(minutes=config.telegram.link_token_ttl_minutes)
        token = await TelegramLinkTokenDao.create(db, cls._hash_token(raw_token), expires_at, telegram_id=telegram_id)
        await TelegramLinkTokenDao.commit(db, token)
        return raw_token, expires_at

    @classmethod
    async def claim_by_telegram(cls: type['AccountLinkService'], db: AsyncSession, raw_token: str, telegram_id: int) -> User:
        logger.info('account_link_claim_by_telegram_started chat_suffix=%s', str(telegram_id)[-4:])
        token = await cls._get_token(db, raw_token)
        if token.user_id is None or token.telegram_id is not None:
            raise ValueError('Invalid website linking token')
        user = await UserDao.get_by_id(db, token.user_id)
        if user is None:
            raise ValueError('Website user not found')
        await cls._attach_telegram_user(db, user, telegram_id)
        token.used_at = Base.utcnow()
        await TelegramLinkTokenDao.commit(db, token)
        logger.info('account_link_claim_by_telegram_completed user_id=%s', user.id)
        return user

    @classmethod
    async def claim_by_user(cls: type['AccountLinkService'], db: AsyncSession, raw_token: str, user_id: UUID) -> User:
        logger.info('account_link_claim_by_user_started user_id=%s', user_id)
        token = await cls._get_token(db, raw_token)
        if token.telegram_id is None or token.user_id is not None:
            raise ValueError('Invalid Telegram linking token')
        user = await UserDao.get_by_id(db, user_id)
        if user is None:
            raise ValueError('Website user not found')
        await cls._attach_telegram_user(db, user, token.telegram_id)
        token.used_at = Base.utcnow()
        await TelegramLinkTokenDao.commit(db, token)
        logger.info('account_link_claim_by_user_completed user_id=%s', user.id)
        return user

    @classmethod
    async def _get_token(cls: type['AccountLinkService'], db: AsyncSession, raw_token: str) -> TelegramLinkToken:
        token = await TelegramLinkTokenDao.get_active(db, cls._hash_token(raw_token), Base.utcnow())
        if token is None:
            raise ValueError('Link token is invalid or expired')
        return token

    @classmethod
    async def _attach_telegram_user(cls: type['AccountLinkService'], db: AsyncSession, target_user: User, telegram_id: int) -> None:
        if target_user.telegram_id is not None and target_user.telegram_id != telegram_id:
            raise ValueError('Website account is already linked to another Telegram account')
        target_profile = await UserProfileDao.ensure(db, target_user.id)
        source_user = await UserDao.get_by_telegram_id(db, telegram_id)
        if source_user is not None and source_user.id != target_user.id:
            if target_user.telegram_id is not None:
                raise ValueError('Telegram account is already linked to another website account')
            source_profile = await UserProfileDao.ensure(db, source_user.id)
            source_onboarding = await OnboardingDao.ensure(db, source_user.id)
            target_onboarding = await OnboardingDao.ensure(db, target_user.id)
            source_selected = await OnboardingDao.merge_more_complete(
                db,
                target_onboarding,
                source_onboarding,
            )
            if source_selected:
                await UserProfileDao.copy_preferences(db, target_profile, source_profile)
                logger.info(
                    'account_link_onboarding_merged source_user_id=%s target_user_id=%s source_selected=true',
                    source_user.id,
                    target_user.id,
                )
            await ChatDao.transfer_to_user(db, source_user.id, target_user.id)
            await UserDao.delete(db, source_user)
        await UserDao.set_telegram_id(db, target_user, telegram_id)
        await UserProfileDao.ensure(db, target_user.id)
        await OnboardingDao.ensure(db, target_user.id)
        boyfriend = await BoyfriendDao.get_first_active(db)
        if boyfriend is None:
            raise RuntimeError('No active companion configured')
        await ChatDao.ensure_for_platform(db, target_user.id, boyfriend.id, 'web', 'Web chat')
        await ChatDao.ensure_for_platform(db, target_user.id, boyfriend.id, 'telegram', 'Telegram chat')
        selected_boyfriend = await BoyfriendDao.get_for_gender(db, target_profile.companion_gender)
        if selected_boyfriend is not None:
            chats = await ChatDao.list_for_user(db, target_user.id)
            for chat in chats:
                await ChatDao.set_boyfriend(db, chat, selected_boyfriend.id)
        logger.info('account_link_platform_chats_ready user_id=%s', target_user.id)

    @classmethod
    def _hash_token(cls: type['AccountLinkService'], raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()
