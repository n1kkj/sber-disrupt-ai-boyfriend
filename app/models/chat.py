from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class Chat(Base):
    __tablename__ = 'chats'
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    boyfriend_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('boyfriends.id'))
    title: Mapped[Optional[str]] = mapped_column(sa.String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, onupdate=Base.utcnow)
