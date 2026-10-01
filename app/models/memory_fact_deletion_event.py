from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import Base


class MemoryFactDeletionEvent(Base):
    __tablename__ = 'memory_fact_deletion_events'
    __table_args__ = (
        sa.Index('ix_memory_fact_deletion_events_user_created_at', 'user_id', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        index=True,
    )
    memory_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey('memory_items.id', ondelete='CASCADE'),
        index=True,
    )
    source: Mapped[str] = mapped_column(sa.String(30))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=Base.utcnow)
