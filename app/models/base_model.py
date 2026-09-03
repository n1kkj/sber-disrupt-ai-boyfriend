from datetime import datetime, UTC
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import as_declarative, declared_attr


@as_declarative()
class Base:
    metadata = sa.MetaData()
    id: Any
    __name__: str

    @declared_attr
    def __tablename__(self) -> str:
        return self.__name__.lower()


def aware_utcnow():
    return datetime.now(UTC).replace(tzinfo=None)
