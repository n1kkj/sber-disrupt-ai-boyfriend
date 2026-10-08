from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class MemoryEvent(Base):
    __tablename__ = 'memory_events'
    __table_args__ = (
        sa.Index('ix_memory_events_user_status', 'user_id', 'status'),
        sa.Index('ix_memory_events_follow_up', 'follow_up_at', 'status'),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    chat_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('chats.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(sa.Text)
    when_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True, index=True)
    participants: Mapped[list] = mapped_column(sa.JSON, default=list)
    kind: Mapped[str] = mapped_column(sa.String(30), default='other')
    confidence: Mapped[float] = mapped_column(sa.Float)
    should_follow_up: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    follow_up_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True, index=True)
    followed_up_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    sensitivity: Mapped[str] = mapped_column(sa.String(20), default='normal')
    status: Mapped[str] = mapped_column(sa.String(20), default='active', index=True)
    source_fragment: Mapped[str] = mapped_column(sa.Text, default='')
    source_message_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey('messages.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, onupdate=Base.utcnow)
