import random
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Literal

from psycopg.errors import UniqueViolation
from sqlalchemy import ColumnElement, func, select
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
from app.core.permissions import editable, set_common, visible
from app.grammar.models import GrammarOption, GrammarQuestion
from app.grammar.schemas import GrammarEntry
from app.grammar.views import GrammarPage, ManagedQuestion, PoolCounts
from app.practice.models import Attempt, AttemptContent, OptionCopy, QuestionCopy
from app.practice.views import UnfinishedInfo

type Pool = Literal["all", "mine"]


class EmptyPool(Exception):
    pass


def pool_filter(user: User, pool: Pool) -> ColumnElement[bool]:
    if pool == "mine":
        return GrammarQuestion.owner_id == user.id

    return visible(GrammarQuestion, user)


def pool_counts(db: Session, user: User) -> PoolCounts:
    total, mine = db.execute(
        select(
            func.count(), func.count().filter(GrammarQuestion.owner_id == user.id)
        ).where(visible(GrammarQuestion, user))
    ).one()

    return PoolCounts(total, mine)


def question_in(question: GrammarQuestion) -> QuestionIn:
    return QuestionIn.model_validate(
        {
            "prompt": question.prompt,
            "options": [o.text for o in question.options],
            "answer": LETTERS[[o.is_correct for o in question.options].index(True)],
            "explanation": question.explanation,
        }
    )


def build_options(data: QuestionIn) -> list[GrammarOption]:
    return [
        GrammarOption(position=i, text=text, is_correct=(i - 1 == data.correct_index))
        for i, text in enumerate(data.options, start=1)
    ]


def apply_question(db: Session, question: GrammarQuestion, data: QuestionIn) -> None:
    question.prompt = data.prompt
    question.explanation = data.explanation

    if question.options:
        question.options.clear()
        db.flush()

    question.options.extend(build_options(data))


def create_question(
    db: Session, user: User, data: QuestionIn, *, common: bool
) -> GrammarQuestion:
    common = common and user.is_admin

    question = GrammarQuestion(owner_id=user.id, is_common=common)
    apply_question(db, question, data)
    db.add(question)

    db.commit()
    return question


def update_question(
    db: Session,
    user: User,
    question: GrammarQuestion,
    data: QuestionIn,
    *,
    common: bool,
) -> None:
    slug = question.slug

    try:
        apply_question(db, question, data)
        set_common(question, user, common)
        db.commit()

    except IntegrityError as e:
        db.rollback()

        if isinstance(e.orig, UniqueViolation) and slug is not None:
            raise SlugTaken(slug) from e

        raise


def delete_question(db: Session, question: GrammarQuestion) -> None:
    db.delete(question)
    db.commit()


def import_grammar(
    db: Session, entries: list[GrammarEntry], *, owner: User | None, common: bool
) -> ImportReport:
    check_importer(owner, common)

    existing = {
        q.slug: q
        for q in db.scalars(
            select(GrammarQuestion)
            .where(
                slug_scope(GrammarQuestion, owner, common),
                GrammarQuestion.slug.in_([entry.slug for entry in entries]),
            )
            .options(selectinload(GrammarQuestion.options))
        )
    }

    added: list[GrammarQuestion] = []
    updated: list[GrammarQuestion] = []
    for entry in entries:
        question = existing.get(entry.slug)
        if question is not None:
            apply_question(db, question, entry)
            updated.append(question)
        else:
            question = GrammarQuestion(
                slug=entry.slug, owner_id=owner.id if owner else None, is_common=common
            )
            apply_question(db, question, entry)
            db.add(question)
            added.append(question)

    commit_import(db)

    return ImportReport(imported(added), imported(updated))


def imported(questions: list[GrammarQuestion]) -> list[ImportedItem]:
    return [ImportedItem(q.id, q.slug or "", q.prompt) for q in questions]


def open_session_for(db: Session, user: User) -> Attempt | None:
    return db.scalar(
        select(Attempt)
        .where(
            Attempt.user_id == user.id,
            Attempt.kind == "grammar",
            Attempt.submitted_at.is_(None),
        )
        .options(selectinload(Attempt.answers))
    )


def copy_questions(
    questions: Sequence[GrammarQuestion],
    shuffle: Callable[[list[OptionCopy]], None] = random.shuffle,
) -> list[QuestionCopy]:
    copies: list[QuestionCopy] = []

    for q in questions:
        options: list[OptionCopy] = [
            {"id": o.id, "text": o.text, "is_correct": o.is_correct} for o in q.options
        ]
        shuffle(options)
        copies.append(
            {
                "id": q.id,
                "prompt": q.prompt,
                "explanation": q.explanation,
                "options": options,
            }
        )

    return copies


def start_session(
    db: Session,
    user: User,
    pool: Pool,
    size: int,
    now: datetime,
    sample: Callable[[Sequence[int], int], list[int]] = random.sample,
) -> Attempt:
    existing = open_session_for(db, user)
    if existing is not None:
        return existing

    ids = db.scalars(select(GrammarQuestion.id).where(pool_filter(user, pool))).all()
    if not ids:
        raise EmptyPool

    chosen = sample(ids, min(size, len(ids)))
    rows = {
        q.id: q
        for q in db.scalars(
            select(GrammarQuestion)
            .where(GrammarQuestion.id.in_(chosen))
            .options(selectinload(GrammarQuestion.options))
        )
    }

    content: AttemptContent = {
        "title": None,
        "level": "",
        "text": "",
        "translation_ru": None,
        "questions": copy_questions([rows[i] for i in chosen]),
    }

    attempt = Attempt(
        kind="grammar",
        user_id=user.id,
        content=content,
        started_at=now,
        last_seen_at=now,
        elapsed_seconds=0,
    )
    db.add(attempt)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = open_session_for(db, user)
        if winner is None:
            raise
        return winner

    return attempt


def start_page(db: Session, user: User, *, empty_pool: bool = False) -> GrammarPage:
    session = open_session_for(db, user)
    unfinished = None
    if session is not None:
        unfinished = UnfinishedInfo(
            id=session.id,
            answered=len(session.answers),
            total=len(session.content["questions"]),
            elapsed_seconds=session.elapsed_seconds,
        )

    return {
        "user": user,
        "counts": pool_counts(db, user),
        "unfinished": unfinished,
        "empty_pool": empty_pool,
    }


def managed_questions(db: Session, user: User) -> list[ManagedQuestion]:
    questions = db.scalars(
        select(GrammarQuestion)
        .where(editable(GrammarQuestion, user))
        .order_by(GrammarQuestion.is_common, GrammarQuestion.id.desc())
    ).all()

    return [
        ManagedQuestion(id=q.id, prompt=q.prompt, slug=q.slug, is_common=q.is_common)
        for q in questions
    ]
