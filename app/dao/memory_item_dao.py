from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_item import MemoryItem


class MemoryItemDao:
    @classmethod
    async def get_for_user(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        user_id: UUID,
        item_id: UUID,
    ) -> Optional[MemoryItem]:
        return await db.scalar(
            sa.select(MemoryItem).where(
                MemoryItem.id == item_id,
                MemoryItem.user_id == user_id,
            )
        )

    @classmethod
    async def list_user_visible(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        user_id: UUID,
    ) -> List[MemoryItem]:
        result = await db.scalars(
            sa.select(MemoryItem)
            .where(
                MemoryItem.user_id == user_id,
                MemoryItem.status == 'active',
            )
            .order_by(MemoryItem.updated_at.desc(), MemoryItem.created_at.desc())
        )
        return list(result)

    @classmethod
    async def list_active(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        user_id: UUID,
        limit: int = 200,
    ) -> List[MemoryItem]:
        result = await db.scalars(
            sa.select(MemoryItem)
            .where(MemoryItem.user_id == user_id, MemoryItem.status == 'active')
            .order_by(MemoryItem.updated_at.desc())
            .limit(limit)
        )
        return list(result)

    @classmethod
    async def list_active_for_key(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        user_id: UUID,
        canonical_key: str,
    ) -> List[MemoryItem]:
        result = await db.scalars(
            sa.select(MemoryItem).where(
                MemoryItem.user_id == user_id,
                MemoryItem.canonical_key == canonical_key,
                MemoryItem.status == 'active',
            )
        )
        return list(result)

    @classmethod
    async def get_by_key_value(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        user_id: UUID,
        canonical_key: str,
        value_hash: str,
    ) -> Optional[MemoryItem]:
        return await db.scalar(
            sa.select(MemoryItem).where(
                MemoryItem.user_id == user_id,
                MemoryItem.canonical_key == canonical_key,
                MemoryItem.value_hash == value_hash,
            )
        )

    @classmethod
    async def create(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        user_id: UUID,
        kind: str,
        subject: str,
        predicate: str,
        value: str,
        canonical_key: str,
        value_hash: str,
        confidence: float,
        stability: str,
        sensitivity: str,
        source_message_id: Optional[UUID],
        metadata_json: Optional[dict] = None,
    ) -> MemoryItem:
        item = MemoryItem(
            user_id=user_id,
            kind=kind,
            subject=subject,
            predicate=predicate,
            value=value,
            canonical_key=canonical_key,
            value_hash=value_hash,
            confidence=confidence,
            stability=stability,
            sensitivity=sensitivity,
            status='active',
            metadata_json=metadata_json,
            source_message_id=source_message_id,
        )
        db.add(item)
        await db.flush()
        return item

    @classmethod
    async def reactivate(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        item: MemoryItem,
        confidence: float,
        stability: str,
        sensitivity: str,
        source_message_id: Optional[UUID],
        metadata_json: Optional[dict],
        now: datetime,
    ) -> MemoryItem:
        item.status = 'active'
        item.confidence = max(item.confidence, confidence)
        item.stability = stability
        item.sensitivity = sensitivity
        item.source_message_id = source_message_id
        item.metadata_json = metadata_json
        item.last_seen_at = now
        item.deleted_at = None
        item.deletion_source = None
        await db.flush()
        return item

    @classmethod
    async def refresh(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        item: MemoryItem,
        confidence: float,
        now: datetime,
    ) -> MemoryItem:
        item.confidence = max(item.confidence, confidence)
        item.last_seen_at = now
        await db.flush()
        return item

    @classmethod
    async def mark_superseded(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        item: MemoryItem,
    ) -> MemoryItem:
        item.status = 'superseded'
        await db.flush()
        return item

    @classmethod
    async def mark_deleted(
        cls: type['MemoryItemDao'],
        db: AsyncSession,
        item: MemoryItem,
        source: str = 'dialogue',
    ) -> MemoryItem:
        item.status = 'deleted_by_user' if source == 'user_api' else 'deleted'
        item.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        item.deletion_source = source
        await db.flush()
        return item
