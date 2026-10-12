from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, and_, not_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.base import ExecutableOption

from app.core.base import Owned

if TYPE_CHECKING:
    from app.auth.models import User


def visible(model: type[Owned], user: User) -> ColumnElement[bool]:
    return or_(model.is_common, model.owner_id == user.id)


def editable(model: type[Owned], user: User) -> ColumnElement[bool]:
    if user.is_admin:
        return or_(model.is_common, model.owner_id == user.id)

    return and_(model.owner_id == user.id, not_(model.is_common))


def load_visible[M: Owned](
    db: Session, user: User, model: type[M], row_id: int, *options: ExecutableOption
) -> M | None:
    return _load(db, model, row_id, visible(model, user), options)


def load_editable[M: Owned](
    db: Session, user: User, model: type[M], row_id: int, *options: ExecutableOption
) -> M | None:
    return _load(db, model, row_id, editable(model, user), options)


def _load[M: Owned](
    db: Session,
    model: type[M],
    row_id: int,
    rule: ColumnElement[bool],
    options: tuple[ExecutableOption, ...],
) -> M | None:
    return db.scalar(select(model).filter_by(id=row_id).where(rule).options(*options))
