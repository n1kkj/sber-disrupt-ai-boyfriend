from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class CharacterVersion(Base):
    __tablename__ = 'character_versions'
    __table_args__ = (
        sa.UniqueConstraint('boyfriend_id', 'version', name='uq_character_versions_boyfriend_version'),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    boyfriend_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('boyfriends.id', ondelete='CASCADE'), index=True)
    version: Mapped[int] = mapped_column(sa.Integer)
    display_name: Mapped[str] = mapped_column(sa.String(120))
    style: Mapped[str] = mapped_column(sa.Text)
    boundaries: Mapped[str] = mapped_column(sa.Text)
    system_prompt: Mapped[str] = mapped_column(sa.Text)
    role_type: Mapped[str] = mapped_column(sa.String(30), default='boyfriend')
    gender: Mapped[str] = mapped_column(sa.String(30), default='male')
    pronouns: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    voice_profile: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    prompt_version: Mapped[str] = mapped_column(sa.String(80), default='v1')
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true(), index=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
