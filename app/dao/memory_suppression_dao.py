from typing import List
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.memory import DeletionRequest
from app.models.memory_suppression import MemorySuppression


class MemorySuppressionDao:
    @classmethod
    async def list_for_user(
        cls: type['MemorySuppressionDao'],
        db: AsyncSession,
        user_id: UUID,
        limit: int = 100,
    ) -> List[MemorySuppression]:
        result = await db.scalars(
            sa.select(MemorySuppression)
            .where(MemorySuppression.user_id == user_id)
            .order_by(MemorySuppression.created_at.desc())
            .limit(limit)
        )
        return list(result)

    @classmethod
    async def create(
        cls: type['MemorySuppressionDao'],
        db: AsyncSession,
        user_id: UUID,
        deletion: DeletionRequest,
    ) -> MemorySuppression:
        suppression = MemorySuppression(
            user_id=user_id,
            scope=deletion.scope,
            target_text=deletion.target_text[:2000],
            person_name=deletion.person_name,
            event_title=deletion.event_title,
        )
        db.add(suppression)
        await db.flush()
        return suppression
