from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (
        sa.Index(
            'uq_messages_platform_external_id',
            'platform',
            'external_id',
            unique=True,
            postgresql_where=sa.text('external_id IS NOT NULL'),
        ),
        sa.Index(
            'uq_messages_chat_idempotency_key',
            'chat_id',
            'idempotency_key',
            unique=True,
            postgresql_where=sa.text('idempotency_key IS NOT NULL'),
        ),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    chat_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('chats.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(sa.String(20))
    content: Mapped[str] = mapped_column(sa.Text)
    platform: Mapped[str] = mapped_column(sa.String(20), default='web', index=True)
    external_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    message_type: Mapped[str] = mapped_column(sa.String(20), default='text')
    status: Mapped[str] = mapped_column(sa.String(20), default='completed', index=True)
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    reply_to_message_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey('messages.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, index=True)
