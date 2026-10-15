import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.core.timeutils import as_utc, local_day
from app.passages.models import Passage
from app.practice.models import Attempt, AttemptAnswer, Option, Question
from app.practice.views import QuestionView
from app.profile.streaks import record_activity

AWAY_LIMIT = timedelta(seconds=30)


class AttemptClosed(Exception):
    """The attempt is already submitted, so it can't be changed."""


class BadAnswer(ValueError):
    """The option doesn't belong to that question, or the question isn't in this attempt."""


def apply_heartbeat(attempt: Attempt, now: datetime) -> None:
    gap = (now - as_utc(attempt.last_seen_at)).total_seconds()

    if 0 <= gap <= AWAY_LIMIT.total_seconds():
        attempt.elapsed_seconds += round(gap)

    attempt.last_seen_at = now


def is_paused(attempt: Attempt, now: datetime) -> bool:
    return now - as_utc(attempt.last_seen_at) > AWAY_LIMIT


def grade(questions: list[Question], answers: dict[int, int]) -> int:
    return sum(
        1
        for q in questions
        if answers.get(q.id) in {o.id for o in q.options if o.is_correct}
    )


def saved_answers(attempt: Attempt) -> dict[int, int]:
    return {
        a.question_id: a.option_id for a in attempt.answers if a.option_id is not None
    }


def ordered_questions(attempt: Attempt) -> list[QuestionView]:
    views: list[QuestionView] = []
    for q in attempt.passage.questions:
        by_id = {o.id: o for o in q.options}
        saved_order = attempt.option_order.get(str(q.id), [])

        ordered = [by_id[oid] for oid in saved_order if oid in by_id]
        ordered += [o for o in q.options if o.id not in set(saved_order)]

        views.append(
            QuestionView(
                id=q.id, prompt=q.prompt, explanation=q.explanation, options=ordered
            )
        )

    return views


def _shuffled_option_order(passage: Passage) -> dict[str, list[int]]:
    order: dict[str, list[int]] = {}

    for q in passage.questions:
        option_ids = [o.id for o in q.options]
        random.shuffle(option_ids)
        order[str(q.id)] = option_ids

    return order


def _require_open(attempt: Attempt) -> None:
    if attempt.submitted_at is not None:
        raise AttemptClosed(f"Attempt {attempt.id} is already submitted.")


def open_attempt_for(db: Session, user: User, passage: Passage) -> Attempt | None:
    return db.scalar(
        select(Attempt).where(
            Attempt.user_id == user.id,
            Attempt.passage_id == passage.id,
            Attempt.submitted_at.is_(None),
        )
    )


def load_attempt(
    db: Session, user: User, attempt_id: int, *, with_content: bool = True
) -> Attempt | None:
    options = (
        [
            selectinload(Attempt.passage)
            .selectinload(Passage.questions)
            .selectinload(Question.options),
            selectinload(Attempt.answers),
        ]
        if with_content
        else []
    )

    attempt = db.get(Attempt, attempt_id, options=options)
    if attempt is None or attempt.user_id != user.id:
        return None

    return attempt


def start(db: Session, user: User, passage: Passage, now: datetime) -> Attempt:
    existing = open_attempt_for(db, user, passage)
    if existing is not None:
        return existing

    attempt = Attempt(
        user_id=user.id,
        passage_id=passage.id,
        option_order=_shuffled_option_order(passage),
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


def save_answer(
    db: Session, attempt: Attempt, question_id: int, option_id: int
) -> None:
    _require_open(attempt)
    attempt_id = (
        attempt.id
    )  # read now: after a rollback, the object is reloaded on access

    belongs = db.scalar(
        select(Option.id)
        .join(Option.question)
        .where(
            Option.id == option_id,
            Option.question_id == question_id,
            Question.passage_id == attempt.passage_id,
        )
    )

    if belongs is None:
        raise BadAnswer(
            f"Option {option_id} does not belong to question {question_id}."
        )

    _set_answer(db, attempt_id, question_id, option_id)

    try:
        db.commit()
    except IntegrityError:
        # Two fast clicks both found no row and both inserted; the other one won. Update it.
        db.rollback()
        _set_answer(db, attempt_id, question_id, option_id)
        db.commit()


def _set_answer(db: Session, attempt_id: int, question_id: int, option_id: int) -> None:
    row = db.scalar(
        select(AttemptAnswer).where(
            AttemptAnswer.attempt_id == attempt_id,
            AttemptAnswer.question_id == question_id,
        )
    )
    if row is None:
        db.add(
            AttemptAnswer(
                attempt_id=attempt_id, question_id=question_id, option_id=option_id
            )
        )
    else:
        row.option_id = option_id


def heartbeat(db: Session, attempt: Attempt, now: datetime) -> int:
    _require_open(attempt)
    apply_heartbeat(attempt, now)
    db.commit()

    return attempt.elapsed_seconds


def submit(
    db: Session, attempt: Attempt, answers: dict[int, int], now: datetime
) -> None:
    if attempt.submitted_at is not None:
        return

    questions = attempt.passage.questions
    saved = {a.question_id: a for a in attempt.answers}

    for q in questions:
        chosen = answers.get(q.id)
        if chosen is None or chosen not in {o.id for o in q.options}:
            continue

        if q.id in saved:
            saved[q.id].option_id = chosen
        else:
            attempt.answers.append(AttemptAnswer(question_id=q.id, option_id=chosen))

    apply_heartbeat(attempt, now)

    attempt.total = len(questions)
    attempt.score = grade(questions, saved_answers(attempt))
    attempt.submitted_at = now

    user = db.get(User, attempt.user_id)
    assert user is not None
    record_activity(user, local_day(now))

    db.commit()


def discard(db: Session, attempt: Attempt) -> None:
    _require_open(attempt)

    db.delete(attempt)
    db.commit()


def delete(db: Session, attempt: Attempt) -> None:
    db.delete(attempt)
    db.commit()
