import random
from collections.abc import Callable
from datetime import datetime

from psycopg.errors import UniqueViolation
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.content.schemas import LETTERS, QuestionIn
from app.content.service import (
    ImportedItem,
    ImportReport,
    SlugTaken,
    check_importer,
    commit_import,
    slug_scope,
)
from app.core.permissions import editable, load_visible, set_common, visible
from app.passages.models import Passage, PassageOption, PassageQuestion
from app.passages.schemas import PassageEntry, PassageIn
from app.passages.views import ManagedPassage, PassageCard
from app.practice.models import Attempt, AttemptContent, OptionCopy, QuestionCopy
from app.practice.views import UnfinishedInfo


def load_passage(db: Session, user: User, passage_id: int) -> Passage | None:
    return load_visible(
        db,
        user,
        Passage,
        passage_id,
        selectinload(Passage.questions).selectinload(PassageQuestion.options),
    )


def passage_in(passage: Passage) -> PassageIn:
    return PassageIn.model_validate(
        {
            "title": passage.title,
            "level": passage.level,
            "text": passage.text,
            "translation_ru": passage.translation_ru,
            "questions": [
                {
                    "prompt": q.prompt,
                    "options": [o.text for o in q.options],
                    "answer": LETTERS[[o.is_correct for o in q.options].index(True)],
                    "explanation": q.explanation,
                }
                for q in passage.questions
            ],
        }
    )


def build_questions(items: list[QuestionIn]) -> list[PassageQuestion]:
    questions: list[PassageQuestion] = []

    for position, q in enumerate(items, start=1):
        options = [
            PassageOption(position=i, text=text, is_correct=(i - 1 == q.correct_index))
            for i, text in enumerate(q.options, start=1)
        ]

        questions.append(
            PassageQuestion(
                position=position,
                prompt=q.prompt,
                explanation=q.explanation,
                options=options,
            )
        )

    return questions


def apply_passage(db: Session, passage: Passage, data: PassageIn) -> None:
    passage.title = data.title
    passage.level = data.level
    passage.text = data.text
    passage.translation_ru = data.translation_ru

    if passage.questions:
        passage.questions.clear()
        db.flush()

    passage.questions.extend(build_questions(data.questions))


def create_passage(
    db: Session, user: User, data: PassageIn, *, common: bool
) -> Passage:
    common = common and user.is_admin

    passage = Passage(owner_id=user.id, is_common=common)
    apply_passage(db, passage, data)
    db.add(passage)

    db.commit()
    return passage


def update_passage(
    db: Session, user: User, passage: Passage, data: PassageIn, *, common: bool
) -> None:
    slug = passage.slug

    try:
        apply_passage(db, passage, data)
        set_common(passage, user, common)
        db.commit()

    except IntegrityError as e:
        db.rollback()

        if isinstance(e.orig, UniqueViolation) and slug is not None:
            raise SlugTaken(slug) from e

        raise


def delete_passage(db: Session, passage: Passage) -> None:
    db.delete(passage)
    db.commit()


def import_passages(
    db: Session, entries: list[PassageEntry], *, owner: User | None, common: bool
) -> ImportReport:
    check_importer(owner, common)

    existing = {
        p.slug: p
        for p in db.scalars(
            select(Passage)
            .where(
                slug_scope(Passage, owner, common),
                Passage.slug.in_([entry.slug for entry in entries]),
            )
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

    commit_import(db)

    return ImportReport(imported(added), imported(updated))


def imported(passages: list[Passage]) -> list[ImportedItem]:
    return [ImportedItem(p.id, p.slug or "", p.display_title) for p in passages]


def managed_passages(db: Session, user: User) -> list[ManagedPassage]:
    rows = db.execute(
        select(Passage, func.count(PassageQuestion.id))
        .outerjoin(Passage.questions)
        .where(editable(Passage, user))
        .group_by(Passage.id)
        .order_by(Passage.is_common, Passage.level, Passage.title)
    ).all()

    return [
        ManagedPassage(
            id=p.id,
            title=p.display_title,
            level=p.level,
            slug=p.slug,
            is_common=p.is_common,
            question_count=q_count,
        )
        for p, q_count in rows
    ]


def copy_passage(
    passage: Passage, shuffle: Callable[[list[OptionCopy]], None] = random.shuffle
) -> AttemptContent:
    questions: list[QuestionCopy] = []
    for q in passage.questions:
        options: list[OptionCopy] = [
            {"id": o.id, "text": o.text, "is_correct": o.is_correct} for o in q.options
        ]
        shuffle(options)
        questions.append(
            {
                "id": q.id,
                "prompt": q.prompt,
                "explanation": q.explanation,
                "options": options,
            }
        )

    return {
        "title": passage.title,
        "level": passage.level,
        "text": passage.text,
        "translation_ru": passage.translation_ru,
        "questions": questions,
    }


def open_attempt_for(db: Session, user: User, passage: Passage) -> Attempt | None:
    return db.scalar(
        select(Attempt).where(
            Attempt.user_id == user.id,
            Attempt.passage_id == passage.id,
            Attempt.submitted_at.is_(None),
        )
    )


def visible_passage_id(db: Session, user: User, attempt: Attempt) -> int | None:
    if attempt.passage_id is None:
        return None

    return db.scalar(
        select(Passage.id).where(
            Passage.id == attempt.passage_id, visible(Passage, user)
        )
    )


def start_attempt(db: Session, user: User, passage: Passage, now: datetime) -> Attempt:
    existing = open_attempt_for(db, user, passage)
    if existing is not None:
        return existing

    attempt = Attempt(
        kind="passage",
        user_id=user.id,
        passage_id=passage.id,
        content=copy_passage(passage),
        started_at=now,
        last_seen_at=now,
        elapsed_seconds=0,
    )
    db.add(attempt)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = open_attempt_for(db, user, passage)
        if winner is None:
            raise
        return winner

    return attempt


def _best_and_tries_query(user: User) -> Select[int | None, int, int]:
    return (
        select(
            Attempt.passage_id,
            func.max(Attempt.score * 100 / Attempt.total),
            func.count(),
        )
        .where(
            Attempt.user_id == user.id,
            Attempt.submitted_at.is_not(None),
            Attempt.total > 0,
        )
        .group_by(Attempt.passage_id)
    )


def passage_stats(db: Session, user: User, passage: Passage) -> tuple[int | None, int]:
    row = db.execute(
        _best_and_tries_query(user).where(Attempt.passage_id == passage.id)
    ).first()

    if row is None:
        return None, 0

    _passage_id, best, tries = row
    return int(best), tries


def passage_cards(db: Session, user: User) -> list[PassageCard]:
    passages = db.scalars(
        select(Passage)
        .where(visible(Passage, user))
        .options(selectinload(Passage.questions))
        .order_by(Passage.level, Passage.title)
    ).all()
    question_count = {p.id: len(p.questions) for p in passages}

    stats: dict[int | None, tuple[int, int]] = {
        passage_id: (int(best), tries)
        for passage_id, best, tries in db.execute(_best_and_tries_query(user)).all()
    }

    open_attempts = db.scalars(
        select(Attempt)
        .where(
            Attempt.kind == "passage",
            Attempt.user_id == user.id,
            Attempt.submitted_at.is_(None),
        )
        .options(selectinload(Attempt.answers))
    ).all()
    unfinished = {
        a.passage_id: UnfinishedInfo(
            id=a.id,
            answered=len(a.answers),
            total=len(a.content["questions"]),
            elapsed_seconds=a.elapsed_seconds,
        )
        for a in open_attempts
    }

    cards: list[PassageCard] = []
    for p in passages:
        best, tries = stats.get(p.id, (None, 0))
        cards.append(
            PassageCard(
                id=p.id,
                title=p.display_title,
                level=p.level,
                question_count=question_count[p.id],
                best=best,
                tries=tries,
                unfinished=unfinished.get(p.id),
            )
        )

    return cards
