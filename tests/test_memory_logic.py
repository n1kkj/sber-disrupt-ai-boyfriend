from datetime import datetime, timedelta
from uuid import uuid4

from app.dto.memory import DeletionRequest, EventCandidate
from app.models.memory_event import MemoryEvent
from app.models.memory_item import MemoryItem
from app.models.memory_suppression import MemorySuppression
from app.models.message import Message
from app.services.memory_service import MemoryService


def make_item(**overrides):
    data = dict(
        id=uuid4(),
        user_id=uuid4(),
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='фильтр-кофе',
        canonical_key='k',
        value_hash='v',
        confidence=0.99,
        stability='stable',
        sensitivity='normal',
        status='active',
        metadata_json={'source_text': 'Я люблю фильтр-кофе.'},
        created_at=datetime(2026, 9, 1),
        updated_at=datetime(2026, 9, 1),
        last_seen_at=datetime(2026, 9, 1),
    )
    data.update(overrides)
    return MemoryItem(**data)


def test_structured_delete_matches_canonical_fact():
    deletion = DeletionRequest(
        target_text='я люблю фильтр-кофе',
        scope='fact',
        kind='preference',
        subject='user',
        predicate='likes_drink',
        value='фильтр-кофе',
    )
    assert MemoryService.deletion_match_score(deletion, make_item()) == 1.0


def test_delete_falls_back_to_original_source_text():
    deletion = DeletionRequest(target_text='я люблю фильтр-кофе', scope='fact')
    assert MemoryService.deletion_match_score(deletion, make_item()) >= 0.75


def test_broad_person_delete_matches_entity_metadata():
    item = make_item(
        kind='relationship',
        subject='person:маша с работы',
        predicate='relation_to_user',
        value='коллега',
        metadata_json={'person_name': 'Маша', 'entities': ['Маша'], 'source_text': 'Маша с работы — моя коллега.'},
    )
    deletion = DeletionRequest(target_text='Маша', scope='all_matching', person_name='Маша')
    assert MemoryService.deletion_match_score(deletion, item) >= 0.9


def test_irrelevant_stable_fact_is_not_retrieved():
    item = make_item()
    assert MemoryService.select_memory_items([item], 'Посоветуй фильм на вечер', 8) == []


def test_relevant_fact_is_retrieved():
    item = make_item()
    assert MemoryService.select_memory_items([item], 'Какой кофе я люблю?', 8) == [item]


def test_blocked_message_never_returns_to_context():
    now = datetime(2026, 9, 19, 12, 0)
    blocked = Message(
        id=uuid4(), chat_id=uuid4(), role='user', content='секретный факт про кофе', status='completed',
        memory_visibility='blocked', created_at=now,
    )
    normal = Message(
        id=uuid4(), chat_id=blocked.chat_id, role='assistant', content='обычный ответ', status='completed',
        memory_visibility='normal', created_at=now + timedelta(seconds=1),
    )
    selected = MemoryService.select_context([blocked, normal], 'кофе', limit=8)
    assert blocked not in selected
    assert normal in selected


def test_short_term_only_is_recent_but_not_historical_retrieval():
    base = datetime(2026, 9, 19, 12, 0)
    private = Message(
        id=uuid4(), chat_id=uuid4(), role='user', content='люблю редкий чай', status='completed',
        memory_visibility='short_term_only', created_at=base,
    )
    fillers = [
        Message(
            id=uuid4(), chat_id=private.chat_id, role='assistant', content=f'ответ {i}', status='completed',
            memory_visibility='normal', created_at=base + timedelta(minutes=i + 1),
        )
        for i in range(10)
    ]
    selected = MemoryService.select_context([private] + fillers, 'редкий чай', limit=8)
    assert private not in selected


def test_forget_suppression_filters_old_raw_message_but_not_future_message():
    base = datetime(2026, 9, 19, 12, 0)
    old = Message(
        id=uuid4(), chat_id=uuid4(), role='user', content='Я люблю фильтр-кофе.', status='completed',
        memory_visibility='normal', created_at=base,
    )
    suppression = MemorySuppression(
        id=uuid4(), user_id=uuid4(), scope='fact', target_text='я люблю фильтр-кофе', created_at=base + timedelta(hours=1)
    )
    future = Message(
        id=uuid4(), chat_id=old.chat_id, role='user', content='Я снова люблю фильтр-кофе.', status='completed',
        memory_visibility='normal', created_at=base + timedelta(hours=2),
    )
    selected = MemoryService.select_context([old, future], 'фильтр-кофе', limit=8, suppressions=[suppression])
    assert old not in selected
    assert future in selected


def test_event_similarity_matches_reschedule():
    candidate = EventCandidate(
        action='update', title='встреча с Машей', participants=['Маша'], kind='meeting', confidence=0.95,
    )
    event = MemoryEvent(
        id=uuid4(), user_id=uuid4(), chat_id=uuid4(), title='встреча с Машей в кофейне',
        participants=['Маша'], kind='meeting', confidence=0.9, should_follow_up=True, sensitivity='normal',
        status='active', source_fragment='', created_at=datetime(2026, 9, 19), updated_at=datetime(2026, 9, 19),
    )
    assert MemoryService.event_similarity(candidate, event) >= 0.45


def test_unrelated_event_is_not_retrieved_just_because_query_mentions_today():
    now = datetime(2026, 9, 19, 12, 0)
    event = MemoryEvent(
        id=uuid4(),
        user_id=uuid4(),
        chat_id=uuid4(),
        title='Демонстрация Druk',
        when_at=now + timedelta(hours=2),
        participants=['Никита'],
        kind='meeting',
        confidence=0.99,
        should_follow_up=True,
        sensitivity='normal',
        status='active',
        source_fragment='',
        created_at=now,
        updated_at=now,
    )
    selected = MemoryService.select_events(
        [event],
        'Я сегодня просто хочу поговорить про фильм.',
        now,
        5,
    )
    assert selected == []


def test_explicit_schedule_query_can_retrieve_nearby_event_without_title_overlap():
    now = datetime(2026, 9, 19, 12, 0)
    event = MemoryEvent(
        id=uuid4(),
        user_id=uuid4(),
        chat_id=uuid4(),
        title='Демонстрация Druk',
        when_at=now + timedelta(hours=2),
        participants=['Никита'],
        kind='meeting',
        confidence=0.99,
        should_follow_up=True,
        sensitivity='normal',
        status='active',
        source_fragment='',
        created_at=now,
        updated_at=now,
    )
    selected = MemoryService.select_events([event], 'Что у меня запланировано?', now, 5)
    assert selected == [event]
