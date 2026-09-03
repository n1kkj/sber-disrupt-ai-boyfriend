from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base, aware_utcnow


class User(Base):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(sa.String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(256))
    display_name: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(sa.BigInteger, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=aware_utcnow)


class Boyfriend(Base):
    __tablename__ = 'boyfriends'

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(sa.String(120))
    description: Mapped[str] = mapped_column(sa.Text)
    system_prompt: Mapped[str] = mapped_column(sa.Text)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=aware_utcnow)


class Chat(Base):
    __tablename__ = 'chats'

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    boyfriend_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('boyfriends.id'))
    title: Mapped[Optional[str]] = mapped_column(sa.String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=aware_utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=aware_utcnow, onupdate=aware_utcnow)


class Message(Base):
    __tablename__ = 'messages'

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    chat_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey('chats.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(sa.String(20))
    content: Mapped[str] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=aware_utcnow, index=True)
