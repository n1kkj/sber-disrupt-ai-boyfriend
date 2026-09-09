from datetime import datetime, time
from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class UserProfile(Base):
    __tablename__ = 'user_profiles'

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    companion_role: Mapped[str] = mapped_column(sa.String(30), default='boyfriend')
    companion_gender: Mapped[str] = mapped_column(sa.String(30), default='male')
    user_gender: Mapped[str] = mapped_column(sa.String(30), default='unspecified')
    user_pronouns: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    preferred_address: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    language: Mapped[str] = mapped_column(sa.String(12), default='ru')
    timezone: Mapped[str] = mapped_column(sa.String(64), default='Europe/Moscow')
    quiet_hours_start: Mapped[Optional[time]] = mapped_column(sa.Time, nullable=True)
    quiet_hours_end: Mapped[Optional[time]] = mapped_column(sa.Time, nullable=True)
    proactive_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    daily_proactive_limit: Mapped[int] = mapped_column(sa.Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, onupdate=Base.utcnow)
