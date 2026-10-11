from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import ColumnElement, Index, MetaData
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    return datetime.now(UTC)


def unique_where(name: str, *columns: str, where: ColumnElement[bool]) -> Index:
    return Index(name, *columns, unique=True, postgresql_where=where)


class Base(DeclarativeBase):
    metadata: ClassVar[MetaData] = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
