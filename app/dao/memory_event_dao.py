from datetime import datetime
from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_event import MemoryEvent


class MemoryEventDao:
    @classmethod
    async def get_by_id(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        event_id: UUID,
    ) -> Optional[MemoryEvent]:
        return await db.scalar(sa.select(MemoryEvent).where(MemoryEvent.id == event_id))

    @classmethod
    async def list_active(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[MemoryEvent]:
        query = sa.select(MemoryEvent).where(
            MemoryEvent.user_id == user_id,
            MemoryEvent.status == 'active',
        )
        if chat_id is not None:
            query = query.where(MemoryEvent.chat_id == chat_id)
        result = await db.scalars(query.order_by(MemoryEvent.updated_at.desc()).limit(limit))
        return list(result)

    @classmethod
    async def list_due_followups(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        now: datetime,
        limit: int,
    ) -> List[MemoryEvent]:
        result = await db.scalars(
            sa.select(MemoryEvent)
            .where(
                MemoryEvent.status == 'active',
                MemoryEvent.should_follow_up.is_(True),
                MemoryEvent.follow_up_at.is_not(None),
                MemoryEvent.follow_up_at <= now,
                MemoryEvent.followed_up_at.is_(None),
            )
            .order_by(MemoryEvent.follow_up_at.asc())
            .limit(limit)
        )
        return list(result)

    @classmethod
    async def create(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        user_id: UUID,
        chat_id: UUID,
        title: str,
        when_at: Optional[datetime],
        participants: list,
        kind: str,
        confidence: float,
        should_follow_up: bool,
        follow_up_at: Optional[datetime],
        sensitivity: str,
        source_fragment: str,
        source_message_id: UUID,
    ) -> MemoryEvent:
        event = MemoryEvent(
            user_id=user_id,
            chat_id=chat_id,
            title=title,
            when_at=when_at,
            participants=participants,
            kind=kind,
            confidence=confidence,
            should_follow_up=should_follow_up,
            follow_up_at=follow_up_at,
            sensitivity=sensitivity,
            source_fragment=source_fragment[:1000],
            status='active',
            source_message_id=source_message_id,
        )
        db.add(event)
        await db.flush()
        return event

    @classmethod
    async def update(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        event: MemoryEvent,
        title: str,
        when_at: Optional[datetime],
        participants: list,
        kind: str,
        confidence: float,
        should_follow_up: bool,
        follow_up_at: Optional[datetime],
        sensitivity: str,
        source_fragment: str,
        source_message_id: UUID,
    ) -> MemoryEvent:
        event.title = title or event.title
        event.when_at = when_at if when_at is not None else event.when_at
        event.participants = participants or event.participants
        event.kind = kind or event.kind
        event.confidence = max(event.confidence, confidence)
        event.should_follow_up = should_follow_up
        event.follow_up_at = follow_up_at
        event.followed_up_at = None
        event.sensitivity = sensitivity
        event.source_fragment = source_fragment[:1000] or event.source_fragment
        event.source_message_id = source_message_id
        await db.flush()
        return event

    @classmethod
    async def mark_cancelled(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        event: MemoryEvent,
    ) -> MemoryEvent:
        event.status = 'cancelled'
        event.should_follow_up = False
        await db.flush()
        return event

    @classmethod
    async def mark_deleted(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        event: MemoryEvent,
    ) -> MemoryEvent:
        event.status = 'deleted'
        event.should_follow_up = False
        await db.flush()
        return event

    @classmethod
    async def mark_followed_up(
        cls: type['MemoryEventDao'],
        db: AsyncSession,
        event: MemoryEvent,
        now: datetime,
    ) -> MemoryEvent:
        event.followed_up_at = now
        await db.flush()
        return event
