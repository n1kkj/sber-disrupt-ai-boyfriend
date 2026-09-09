from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.onboarding_state import OnboardingState


class OnboardingDao:
    @classmethod
    async def get(cls: type['OnboardingDao'], db: AsyncSession, user_id: UUID) -> Optional[OnboardingState]:
        return await db.scalar(sa.select(OnboardingState).where(OnboardingState.user_id == user_id))

    @classmethod
    async def create_default(cls: type['OnboardingDao'], db: AsyncSession, user_id: UUID) -> OnboardingState:
        state = OnboardingState(user_id=user_id, answers={})
        db.add(state)
        await db.flush()
        return state

    @classmethod
    async def ensure(cls: type['OnboardingDao'], db: AsyncSession, user_id: UUID) -> OnboardingState:
        state = await cls.get(db, user_id)
        if state is not None:
            return state
        return await cls.create_default(db, user_id)

    @classmethod
    async def commit(cls: type['OnboardingDao'], db: AsyncSession, state: OnboardingState) -> OnboardingState:
        await db.commit()
        await db.refresh(state)
        return state

    @classmethod
    async def advance(
        cls: type['OnboardingDao'],
        db: AsyncSession,
        state: OnboardingState,
        status: str,
        step: str,
        answers: Dict[str, Any],
        completed_at: Optional[datetime],
    ) -> OnboardingState:
        state.status = status
        state.step = step
        state.answers = answers
        state.completed_at = completed_at
        await db.flush()
        return state

    @classmethod
    async def merge_more_complete(
        cls: type['OnboardingDao'],
        db: AsyncSession,
        target: OnboardingState,
        source: OnboardingState,
    ) -> bool:
        source_score = cls._score(source)
        target_score = cls._score(target)
        if source_score <= target_score:
            return False
        target.status = source.status
        target.step = source.step
        target.answers = dict(source.answers)
        target.completed_at = source.completed_at
        await db.flush()
        return True

    @classmethod
    def _score(cls: type['OnboardingDao'], state: OnboardingState) -> int:
        if state.status == 'completed':
            return 1000
        return len(state.answers)
