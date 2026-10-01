import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.dao.memory_fact_deletion_event_dao import MemoryFactDeletionEventDao
from app.dao.memory_item_dao import MemoryItemDao
from app.dao.memory_suppression_dao import MemorySuppressionDao
from app.services.memory_fact_service import MemoryFactService


def test_user_delete_is_soft_delete_with_analytics_event(monkeypatch) -> None:
    user_id = uuid4()
    fact_id = uuid4()
    item = SimpleNamespace(
        id=fact_id,
        user_id=user_id,
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='фильтр-кофе',
        status='active',
        source_message_id=None,
    )
    db = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())

    get_for_user = AsyncMock(return_value=item)
    create_suppression = AsyncMock()
    create_event = AsyncMock()
    mark_deleted = AsyncMock(return_value=item)

    monkeypatch.setattr(MemoryItemDao, 'get_for_user', get_for_user)
    monkeypatch.setattr(MemorySuppressionDao, 'create', create_suppression)
    monkeypatch.setattr(MemoryFactDeletionEventDao, 'create', create_event)
    monkeypatch.setattr(MemoryItemDao, 'mark_deleted', mark_deleted)

    result = asyncio.run(MemoryFactService.delete_user_fact(db, user_id, fact_id))

    assert result is item
    create_suppression.assert_awaited_once()
    create_event.assert_awaited_once_with(db, user_id, fact_id, 'user_api')
    mark_deleted.assert_awaited_once_with(db, item, source='user_api')
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(item)


def test_repeated_user_delete_is_idempotent(monkeypatch) -> None:
    user_id = uuid4()
    fact_id = uuid4()
    item = SimpleNamespace(
        id=fact_id,
        user_id=user_id,
        status='deleted_by_user',
        source_message_id=None,
    )
    db = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock())

    monkeypatch.setattr(MemoryItemDao, 'get_for_user', AsyncMock(return_value=item))
    create_event = AsyncMock()
    monkeypatch.setattr(MemoryFactDeletionEventDao, 'create', create_event)

    result = asyncio.run(MemoryFactService.delete_user_fact(db, user_id, fact_id))

    assert result is item
    create_event.assert_not_awaited()
    db.commit.assert_not_awaited()
