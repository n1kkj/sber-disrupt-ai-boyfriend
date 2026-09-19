import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.dao.memory_item_dao import MemoryItemDao
from app.dao.memory_suppression_dao import MemorySuppressionDao
from app.dao.user_dao import UserDao
from app.database import async_session
from app.models.memory_fact_deletion_event import MemoryFactDeletionEvent
from app.services.memory_fact_service import MemoryFactService


pytestmark = pytest.mark.skipif(
    os.getenv('RUN_DB_TESTS') != '1',
    reason='requires PostgreSQL with migrated schema',
)


def test_manual_fact_delete_keeps_row_for_analytics_and_hides_it_from_user() -> None:
    async def scenario() -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with async_session() as db:
            user = await UserDao.create(
                db,
                email=f'memory-delete-{uuid4()}@example.com',
                password_hash='test',
                display_name='Memory Delete Test',
            )
            item = await MemoryItemDao.create(
                db,
                user.id,
                'preference',
                'user',
                'likes_drink',
                'фильтр-кофе',
                'canonical-key-for-integration-test',
                'value-hash-for-integration-test',
                0.99,
                'stable',
                'normal',
                None,
                {'entities': []},
            )
            await db.commit()
            fact_id = item.id
            user_id = user.id

            visible_before = await MemoryFactService.list_user_facts(db, user_id)
            assert [fact.id for fact in visible_before] == [fact_id]

            await MemoryFactService.delete_user_fact(db, user_id, fact_id)

            visible_after = await MemoryFactService.list_user_facts(db, user_id)
            assert visible_after == []

            persisted = await MemoryItemDao.get_for_user(db, user_id, fact_id)
            assert persisted is not None
            assert persisted.status == 'deleted_by_user'
            assert persisted.deletion_source == 'user_api'
            assert persisted.deleted_at is not None

            deletion_event = await db.scalar(
                sa.select(MemoryFactDeletionEvent).where(
                    MemoryFactDeletionEvent.user_id == user_id,
                    MemoryFactDeletionEvent.memory_item_id == fact_id,
                )
            )
            assert deletion_event is not None
            assert deletion_event.source == 'user_api'

            suppressions = await MemorySuppressionDao.list_for_user(db, user_id)
            assert len(suppressions) == 1
            assert suppressions[0].target_text == 'фильтр-кофе'

            await db.delete(user)
            await db.commit()

    asyncio.run(scenario())
