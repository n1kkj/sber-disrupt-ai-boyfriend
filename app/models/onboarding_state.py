from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class OnboardingState(Base):
    __tablename__ = 'onboarding_states'

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    status: Mapped[str] = mapped_column(sa.String(30), default='in_progress')
    step: Mapped[str] = mapped_column(sa.String(50), default='companion_role')
    answers: Mapped[Dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    completed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow, onupdate=Base.utcnow)
