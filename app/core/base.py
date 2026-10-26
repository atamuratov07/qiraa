from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import (
    CheckConstraint,
    ColumnElement,
    ForeignKey,
    Index,
    MetaData,
    false,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class Owned:
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    is_common: Mapped[bool] = mapped_column(server_default=false())


def common_or_owned() -> CheckConstraint:
    return CheckConstraint("is_common OR owner_id IS NOT NULL", name="common_or_owned")
