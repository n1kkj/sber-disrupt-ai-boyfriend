from datetime import datetime
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_link_token import TelegramLinkToken


class TelegramLinkTokenDao:
    @classmethod
    async def create(cls: type['TelegramLinkTokenDao'], db: AsyncSession, token_hash: str, expires_at: datetime, user_id: Optional[UUID] = None, telegram_id: Optional[int] = None) -> TelegramLinkToken:
        token = TelegramLinkToken(token_hash=token_hash, expires_at=expires_at, user_id=user_id, telegram_id=telegram_id)
        db.add(token)
        await db.flush()
        return token

    @classmethod
    async def get_active(cls: type['TelegramLinkTokenDao'], db: AsyncSession, token_hash: str, now: datetime) -> Optional[TelegramLinkToken]:
        return await db.scalar(sa.select(TelegramLinkToken).where(TelegramLinkToken.token_hash == token_hash, TelegramLinkToken.used_at.is_(None), TelegramLinkToken.expires_at > now))

    @classmethod
    async def commit(cls: type['TelegramLinkTokenDao'], db: AsyncSession, token: TelegramLinkToken) -> TelegramLinkToken:
        await db.commit()
        await db.refresh(token)
        return token
