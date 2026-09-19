from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class MemoryItem(Base):
    __tablename__ = 'memory_items'
    __table_args__ = (
        sa.UniqueConstraint('user_id', 'canonical_key', 'value_hash', name='uq_memory_items_user_key_value'),
        sa.Index('ix_memory_items_user_status', 'user_id', 'status'),
        sa.Index('ix_memory_items_user_canonical_key', 'user_id', 'canonical_key'),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(sa.String(30))
    subject: Mapped[str] = mapped_column(sa.String(255))
    predicate: Mapped[str] = mapped_column(sa.String(255))
    value: Mapped[str] = mapped_column(sa.Text)
    canonical_key: Mapped[str] = mapped_column(sa.String(40))
    value_hash: Mapped[str] = mapped_column(sa.String(40))
    confidence: Mapped[float] = mapped_column(sa.Float)
    stability: Mapped[str] = mapped_column(sa.String(20))
    sensitivity: Mapped[str] = mapped_column(sa.String(20), default='normal')
    status: Mapped[str] = mapped_column(sa.String(20), default='active', index=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    source_message_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey('messages.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    deletion_source: Mapped[Optional[str]] = mapped_column(sa.String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, onupdate=Base.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
