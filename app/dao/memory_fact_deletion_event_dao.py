from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_fact_deletion_event import MemoryFactDeletionEvent


class MemoryFactDeletionEventDao:
    @classmethod
    async def create(
        cls: type['MemoryFactDeletionEventDao'],
        db: AsyncSession,
        user_id: UUID,
        memory_item_id: UUID,
        source: str,
    ) -> MemoryFactDeletionEvent:
        event = MemoryFactDeletionEvent(
            user_id=user_id,
            memory_item_id=memory_item_id,
            source=source,
        )
        db.add(event)
        await db.flush()
        return event
