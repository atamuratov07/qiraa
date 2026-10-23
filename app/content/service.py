from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, not_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.errors import ContentError, LineError
from app.core.base import Owned


class NotAllowed(Exception):
    """Only admins import common content."""


@dataclass(frozen=True)
class ImportedItem:
    id: int
    slug: str
    title: str


@dataclass(frozen=True)
class ImportReport:
    added: list[ImportedItem]
    updated: list[ImportedItem]


def check_importer(owner: User | None, common: bool) -> None:
    if common and owner is not None and not owner.is_admin:
        raise NotAllowed
    if owner is None and not common:
        raise ValueError("a private import needs an owner")


def slug_scope(
    model: type[Owned], owner: User | None, common: bool
) -> ColumnElement[bool]:
    if common:
        return model.is_common.expression

    assert owner is not None
    return and_(model.owner_id == owner.id, not_(model.is_common))


def commit_import(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        conflict = LineError(None, "", "import_conflict", "Import conflict", {})
        raise ContentError([conflict]) from e
