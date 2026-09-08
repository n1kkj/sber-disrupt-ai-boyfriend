from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class MediaAsset(Base):
    __tablename__ = 'media_assets'

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), index=True)
    platform: Mapped[str] = mapped_column(sa.String(20))
    external_file_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(sa.String(512), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(sa.BigInteger, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(sa.String(20), default='pending', index=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, index=True)
