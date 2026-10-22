from dataclasses import dataclass

from sqlalchemy import and_, not_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.content.errors import ContentError, LineError
from app.content.schemas import PassageEntry
from app.passages.models import Passage
from app.passages.service import apply_passage


class NotAllowed(Exception):
    """Only admins import common content."""


@dataclass(frozen=True)
class ImportedPassage:
    id: int
    slug: str
    title: str


@dataclass(frozen=True)
class ImportReport:
    added: list[ImportedPassage]
    updated: list[ImportedPassage]


def import_passages(
    db: Session, entries: list[PassageEntry], *, owner: User | None, common: bool
) -> ImportReport:
    if common and owner is not None and not owner.is_admin:
        raise NotAllowed
    if owner is None and not common:
        raise ValueError("a private import needs an owner")

    if common:
        scope = Passage.is_common
    else:
        assert owner is not None
        scope = and_(Passage.owner_id == owner.id, not_(Passage.is_common))

    existing = {
        p.slug: p
        for p in db.scalars(
            select(Passage)
            .where(scope, Passage.slug.in_([entry.slug for entry in entries]))
            .options(selectinload(Passage.questions))
        )
    }

    added: list[Passage] = []
    updated: list[Passage] = []
    for entry in entries:
        passage = existing.get(entry.slug)
        if passage is not None:
            apply_passage(db, passage, entry)
            updated.append(passage)
        else:
            passage = Passage(
                slug=entry.slug, owner_id=owner.id if owner else None, is_common=common
            )
            apply_passage(db, passage, entry)
            db.add(passage)
            added.append(passage)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        conflict = LineError(None, "", "import_conflict", "Import conflict", {})
        raise ContentError([conflict]) from e

    return ImportReport(report(added), report(updated))


def report(passages: list[Passage]) -> list[ImportedPassage]:
    return [ImportedPassage(p.id, p.slug or "", p.display_title) for p in passages]
