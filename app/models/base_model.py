from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import as_declarative, declared_attr


@as_declarative()
class Base:
    metadata = sa.MetaData()
    id: Any
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
