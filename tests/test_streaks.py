"""Streaks: the pure date rules first, then submitting quizzes through the service."""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import Passage, User
from app.services import attempts, streaks
from app.timeutils import local_day
from tests.factories import T0


def october(day: int) -> date:
    return date(2026, 10, day)


# ---------------------------------------------------------------------------
# local_day: Tashkent is UTC+5, so 19:00 UTC is already the next day there
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        pytest.param(
            datetime(2026, 10, 7, 23, 16, tzinfo=UTC),
            october(8),
            id="04:16 in Tashkent",
        ),
        pytest.param(
            datetime(2026, 10, 7, 18, 59, tzinfo=UTC),
            october(7),
            id="23:59 in Tashkent",
        ),
        pytest.param(
            datetime(2026, 10, 7, 19, 0, tzinfo=UTC),
            october(8),
            id="midnight in Tashkent",
        ),
        pytest.param(
            datetime(2026, 10, 7, 23, 16), october(8), id="naive, as SQLite returns it"
        ),
    ],
)
def test_local_day(moment: datetime, expected: date) -> None:
    assert local_day(moment) == expected


# ---------------------------------------------------------------------------
# record_activity: (current, longest, last_active_on) after a quiz on `today`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("last", "current", "longest", "today", "expected"),
    [
        pytest.param(None, 0, 0, october(7), (1, 1, october(7)), id="first quiz ever"),
        pytest.param(
            october(7),
            3,
            5,
            october(7),
            (3, 5, october(7)),
            id="second quiz the same day",
        ),
        pytest.param(
            october(7), 3, 5, october(8), (4, 5, october(8)), id="the next day"
        ),
        pytest.param(
            october(7),
            5,
            5,
            october(8),
            (6, 6, october(8)),
            id="the next day beats the record",
        ),
        pytest.param(
            october(7), 3, 5, october(9), (1, 5, october(9)), id="missed a day"
        ),
        pytest.param(
            date(2026, 9, 30),
            2,
            2,
            october(1),
            (3, 3, october(1)),
            id="across a month end",
        ),
        pytest.param(
            date(2026, 12, 31),
            2,
            2,
            date(2027, 1, 1),
            (3, 3, date(2027, 1, 1)),
            id="across a year end",
        ),
        pytest.param(
            october(8), 3, 5, october(7), (3, 5, october(8)), id="clock went backwards"
        ),
    ],
)
def test_record_activity(
    last: date | None,
    current: int,
    longest: int,
    today: date,
    expected: tuple[int, int, date],
) -> None:
    user = User(last_active_on=last, current_streak=current, longest_streak=longest)
    streaks.record_activity(user, today)
    assert (user.current_streak, user.longest_streak, user.last_active_on) == expected


# ---------------------------------------------------------------------------
# visible_streak: last practised 7 Oct with a streak of 4
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("last", "today", "shown"),
    [
        pytest.param(october(7), october(7), 4, id="practised today"),
        pytest.param(october(7), october(8), 4, id="practised yesterday: still alive"),
        pytest.param(october(7), october(9), 0, id="missed yesterday: gone"),
        pytest.param(None, october(9), 0, id="never practised"),
    ],
)
def test_visible_streak(last: date | None, today: date, shown: int) -> None:
    user = User(last_active_on=last, current_streak=4, longest_streak=4)
    assert streaks.visible_streak(user, today) == shown


# ---------------------------------------------------------------------------
# Through submit(): the streak is saved in the same commit as the score
# ---------------------------------------------------------------------------


def submit_quiz(db: Session, user: User, passage: Passage, now: datetime) -> None:
    attempt = attempts.load_attempt(db, user, attempts.start(db, user, passage, now).id)
    assert attempt is not None
    attempts.submit(db, attempt, {1: 11}, now)


def stored_streak(db: Session, user: User) -> tuple[int, int, date | None]:
    db.expire_all()
    fresh = db.get(User, user.id)
    assert fresh is not None
    return (fresh.current_streak, fresh.longest_streak, fresh.last_active_on)


def test_submitting_counts_each_day_once(
    db: Session, user: User, passage: Passage
) -> None:
    submit_quiz(db, user, passage, T0)  # 7 Oct, 15:00 in Tashkent
    assert stored_streak(db, user) == (1, 1, october(7))

    submit_quiz(db, user, passage, T0 + timedelta(hours=2))  # same day
    assert stored_streak(db, user) == (1, 1, october(7))

    submit_quiz(db, user, passage, T0 + timedelta(days=1))  # 8 Oct
    assert stored_streak(db, user) == (2, 2, october(8))

    submit_quiz(db, user, passage, T0 + timedelta(days=3))  # 10 Oct: 9 Oct was missed
    assert stored_streak(db, user) == (1, 2, october(10))


def test_a_quiz_after_local_midnight_counts_for_the_new_day(
    db: Session, user: User, passage: Passage
) -> None:
    submit_quiz(db, user, passage, datetime(2026, 10, 7, 23, 16, tzinfo=UTC))
    assert stored_streak(db, user) == (1, 1, october(8))


def test_unfinished_and_discarded_attempts_dont_count(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    attempts.save_answer(db, attempt, 1, 11)
    attempts.discard(db, attempt)
    attempts.start(db, user, passage, T0)  # left open
    assert stored_streak(db, user) == (0, 0, None)
