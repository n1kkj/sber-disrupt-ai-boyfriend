import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.dao.memory_item_dao import MemoryItemDao
from app.dto.memory import (
    AutomaticMemoryMutationPlan,
    DeletionRequest,
    FactCandidate,
    MemoryAnalysis,
    PersonCandidate,
)
from app.services.memory_extraction_service import MemoryExtractionService


def test_active_fact_schema_has_no_automatic_supersession_fields() -> None:
    assert 'replace_existing' not in FactCandidate.model_fields
    assert 'supersedes_predicates' not in FactCandidate.model_fields


def test_active_memory_analysis_has_no_deletion_channel() -> None:
    assert 'deletions' not in MemoryAnalysis.model_fields


def test_automatic_mutation_scaffold_is_retained_but_separate() -> None:
    assert 'deletions' in AutomaticMemoryMutationPlan.model_fields
    deletion = DeletionRequest(
        target_text='я люблю фильтр-кофе',
        scope='fact',
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='фильтр-кофе',
    )
    plan = AutomaticMemoryMutationPlan(deletions=[deletion])
    assert plan.deletions == [deletion]


def test_same_turn_deletion_matcher_scaffold_is_still_available() -> None:
    fact = FactCandidate(
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='фильтр-кофе',
        confidence=0.99,
        stability='stable',
        sensitivity='normal',
        store=True,
        reason='explicit preference',
    )
    deletion = DeletionRequest(
        target_text='я люблю фильтр-кофе',
        scope='fact',
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='фильтр-кофе',
    )
    assert MemoryExtractionService._fact_matches_same_turn_deletion(fact, [deletion])


def test_store_fact_does_not_supersede_other_active_values(monkeypatch) -> None:
    user_id = uuid4()
    source_message = SimpleNamespace(id=uuid4(), content='Теперь люблю капучино')
    db = SimpleNamespace()

    fact = FactCandidate(
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='капучино',
        confidence=0.99,
        stability='stable',
        sensitivity='normal',
        store=True,
        reason='explicit preference',
    )

    monkeypatch.setattr(MemoryItemDao, 'get_by_key_value', AsyncMock(return_value=None))
    create = AsyncMock()
    monkeypatch.setattr(MemoryItemDao, 'create', create)
    mark_superseded = AsyncMock()
    monkeypatch.setattr(MemoryItemDao, 'mark_superseded', mark_superseded)

    asyncio.run(
        MemoryExtractionService._store_fact(
            db,
            user_id,
            source_message,
            fact,
            MemoryExtractionService._now_naive(),
        )
    )

    create.assert_awaited_once()
    mark_superseded.assert_not_awaited()


def test_person_matcher_scaffold_is_still_available() -> None:
    person = PersonCandidate(
        name='Маша',
        relation_to_user='коллега',
        disambiguator='Маша с работы',
        confidence=0.95,
    )
    deletion = DeletionRequest(
        target_text='всё про Машу',
        scope='all_matching',
        person_name='Маша',
    )
    assert MemoryExtractionService._person_matches_same_turn_deletion(person, [deletion])
