from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.memory_fact_deletion_event_dao import MemoryFactDeletionEventDao
from app.dao.memory_item_dao import MemoryItemDao
from app.dao.memory_suppression_dao import MemorySuppressionDao
from app.dao.message_dao import MessageDao
from app.dto.memory import DeletionRequest
from app.logging import logger
from app.models.memory_item import MemoryItem


class MemoryFactService:
    @classmethod
    async def list_user_facts(
        cls: type['MemoryFactService'],
        db: AsyncSession,
        user_id: UUID,
    ) -> List[MemoryItem]:
        return await MemoryItemDao.list_user_visible(db, user_id)

    @classmethod
    async def delete_user_fact(
        cls: type['MemoryFactService'],
        db: AsyncSession,
        user_id: UUID,
        fact_id: UUID,
    ) -> MemoryItem:
        item = await MemoryItemDao.get_for_user(db, user_id, fact_id)
        if item is None:
            raise LookupError('Memory fact not found')

        # DELETE is idempotent. A non-active fact is already detached from the user's memory.
        if item.status != 'active':
            return item

        deletion = DeletionRequest(
            target_text=item.value,
            scope='fact',
            kind=item.kind,
            subject=item.subject,
            predicate=item.predicate,
            value=item.value,
            confidence=1.0,
            reason='user_deleted_via_api',
        )
        await MemorySuppressionDao.create(db, user_id, deletion)
        await MemoryFactDeletionEventDao.create(db, user_id, item.id, 'user_api')
        await MemoryItemDao.mark_deleted(db, item, source='user_api')

        # Raw chat history is a second retrieval source. Hide the source turn as well,
        # otherwise a fact removed from structured memory could still resurface from history.
        if item.source_message_id is not None:
            source_message = await MessageDao.get_by_id(db, item.source_message_id)
            if source_message is not None:
                await MessageDao.set_memory_visibility(db, source_message, 'blocked')

        await db.commit()
        await db.refresh(item)
        logger.info('memory_fact_user_deleted user_id=%s fact_id=%s', user_id, fact_id)
        return item
