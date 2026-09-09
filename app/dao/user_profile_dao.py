from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_profile import UserProfile


class UserProfileDao:
    @classmethod
    async def get(cls: type['UserProfileDao'], db: AsyncSession, user_id: UUID) -> Optional[UserProfile]:
        return await db.scalar(sa.select(UserProfile).where(UserProfile.user_id == user_id))

    @classmethod
    async def create_default(cls: type['UserProfileDao'], db: AsyncSession, user_id: UUID) -> UserProfile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
        return profile

    @classmethod
    async def ensure(cls: type['UserProfileDao'], db: AsyncSession, user_id: UUID) -> UserProfile:
        profile = await cls.get(db, user_id)
        if profile is not None:
            return profile
        return await cls.create_default(db, user_id)

    @classmethod
    async def commit(cls: type['UserProfileDao'], db: AsyncSession, profile: UserProfile) -> UserProfile:
        await db.commit()
        await db.refresh(profile)
        return profile

    @classmethod
    async def update_preferences(
        cls: type['UserProfileDao'],
        db: AsyncSession,
        profile: UserProfile,
        companion_role: Optional[str],
        companion_gender: Optional[str],
        user_gender: Optional[str],
        user_pronouns: Optional[str],
        preferred_address: Optional[str],
        language: Optional[str],
        timezone: Optional[str],
    ) -> UserProfile:
        if companion_role is not None:
            profile.companion_role = companion_role
        if companion_gender is not None:
            profile.companion_gender = companion_gender
        if user_gender is not None:
            profile.user_gender = user_gender
        if user_pronouns is not None:
            profile.user_pronouns = user_pronouns
        if preferred_address is not None:
            profile.preferred_address = preferred_address
        if language is not None:
            profile.language = language
        if timezone is not None:
            profile.timezone = timezone
        await db.flush()
        return profile

    @classmethod
    async def sync_companion_from_onboarding(
        cls: type['UserProfileDao'],
        db: AsyncSession,
        profile: UserProfile,
        companion_gender: str,
    ) -> UserProfile:
        normalized_gender = 'female' if companion_gender == 'female' else 'male'
        profile.companion_gender = normalized_gender
        profile.companion_role = 'girlfriend' if normalized_gender == 'female' else 'boyfriend'
        await db.flush()
        return profile

    @classmethod
    async def copy_preferences(
        cls: type['UserProfileDao'],
        db: AsyncSession,
        target: UserProfile,
        source: UserProfile,
    ) -> UserProfile:
        target.companion_role = source.companion_role
        target.companion_gender = source.companion_gender
        target.user_gender = source.user_gender
        target.user_pronouns = source.user_pronouns
        target.preferred_address = source.preferred_address
        target.language = source.language
        target.timezone = source.timezone
        target.quiet_hours_start = source.quiet_hours_start
        target.quiet_hours_end = source.quiet_hours_end
        target.proactive_enabled = source.proactive_enabled
        target.daily_proactive_limit = source.daily_proactive_limit
        await db.flush()
        return target
