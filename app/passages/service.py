from psycopg.errors import UniqueViolation
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.core.permissions import editable, load_visible, visible
from app.passages.models import Passage
from app.passages.schemas import LETTERS, PassageIn, QuestionIn
from app.passages.views import ManagedPassage, PassageCard, UnfinishedInfo
from app.practice.models import Attempt, Option, Question


class SlugTaken(Exception):
    """Another passage in the same area already has this slug."""

    def __init__(self, slug: str) -> None:
        super().__init__(slug)
        self.slug: str = slug


def load_passage(db: Session, user: User, passage_id: int) -> Passage | None:
    return load_visible(
        db,
        user,
        Passage,
        passage_id,
        selectinload(Passage.questions).selectinload(Question.options),
    )


def passage_in(passage: Passage) -> PassageIn:
    return PassageIn.model_validate(
        {
            "title": passage.title,
            "level": passage.level,
            "text": passage.text,
            "translation_ru": passage.translation_ru,
            "glossary": dict(passage.glossary),
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


def build_questions(items: list[QuestionIn]) -> list[Question]:
    questions: list[Question] = []

    for position, q in enumerate(items, start=1):
        options = [
            Option(position=i, text=text, is_correct=(i - 1 == q.correct_index))
            for i, text in enumerate(q.options, start=1)
        ]

        questions.append(
            Question(
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
    passage.glossary = data.glossary

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
    common = common and user.is_admin
    slug = passage.slug

    try:
        apply_passage(db, passage, data)

        if not common and passage.is_common and passage.owner_id is None:
            passage.owner_id = user.id
        passage.is_common = common

        db.commit()

    except IntegrityError as e:
        db.rollback()

        if isinstance(e.orig, UniqueViolation) and slug is not None:
            raise SlugTaken(slug) from e

        raise


def delete_passage(db: Session, passage: Passage) -> None:
    db.delete(passage)
    db.commit()


def managed_passages(db: Session, user: User) -> list[ManagedPassage]:
    rows = db.execute(
        select(Passage, func.count(Question.id))
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
        .where(Attempt.user_id == user.id, Attempt.submitted_at.is_(None))
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
