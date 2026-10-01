from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class MemorySuppression(Base):
    __tablename__ = 'memory_suppressions'
    __table_args__ = (
        sa.Index('ix_memory_suppressions_user_created_at', 'user_id', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    scope: Mapped[str] = mapped_column(sa.String(30))
    target_text: Mapped[str] = mapped_column(sa.Text)
    person_name: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    event_title: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
