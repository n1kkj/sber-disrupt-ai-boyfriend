from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class MemoryEpisode(Base):
    __tablename__ = 'memory_episodes'
    __table_args__ = (
        sa.Index('ix_memory_episodes_user_status', 'user_id', 'status'),
        sa.Index('ix_memory_episodes_chat_created_at', 'chat_id', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    chat_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('chats.id', ondelete='CASCADE'), index=True)
    summary: Mapped[str] = mapped_column(sa.Text)
    people: Mapped[list] = mapped_column(sa.JSON, default=list)
    topics: Mapped[list] = mapped_column(sa.JSON, default=list)
    emotional_tone: Mapped[list] = mapped_column(sa.JSON, default=list)
    unresolved_threads: Mapped[list] = mapped_column(sa.JSON, default=list)
    retrieval_anchors: Mapped[list] = mapped_column(sa.JSON, default=list)
    sensitivity: Mapped[str] = mapped_column(sa.String(20), default='normal')
    status: Mapped[str] = mapped_column(sa.String(20), default='active', index=True)
    source_message_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey('messages.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
