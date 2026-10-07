"""Level 1: the pure rules. No database, no HTTP; each test runs in about a millisecond.

The objects below are built in memory and never saved. SQLAlchemy models work as
ordinary Python objects until you add them to a session.
"""

from datetime import timedelta

import pytest

from app.models import Attempt, AttemptAnswer
from app.services import attempts
from tests.factories import T0, make_passage, make_question

# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("seconds_later", "expected_elapsed"),
    [
        pytest.param(15, 115, id="normal beat"),
        pytest.param(30, 130, id="exactly 30s still counts"),
        pytest.param(31, 100, id="31s means the user was away"),
        pytest.param(4.5 * 3600, 100, id="came back hours later"),
        pytest.param(-10, 100, id="server clock went backwards"),
        pytest.param(14.6, 115, id="rounds to the nearest second"),
    ],
)
def test_apply_heartbeat(seconds_later: float, expected_elapsed: int) -> None:
    # Arrange
    attempt = Attempt(elapsed_seconds=100, last_seen_at=T0)
    now = T0 + timedelta(seconds=seconds_later)
    # Act
    attempts.apply_heartbeat(attempt, now)
    # Assert
    assert attempt.elapsed_seconds == expected_elapsed
    assert attempt.last_seen_at == now


def test_apply_heartbeat_accepts_naive_datetimes_from_sqlite() -> None:
    attempt = Attempt(elapsed_seconds=0, last_seen_at=T0.replace(tzinfo=None))
    attempts.apply_heartbeat(attempt, T0 + timedelta(seconds=10))
    assert attempt.elapsed_seconds == 10


@pytest.mark.parametrize(("seconds_later", "paused"), [(30, False), (31, True)])
def test_is_paused(seconds_later: int, paused: bool) -> None:
    attempt = Attempt(last_seen_at=T0)
    assert attempts.is_paused(attempt, T0 + timedelta(seconds=seconds_later)) is paused


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

QUESTIONS = [make_question(1, correct=1), make_question(2, correct=2)]


@pytest.mark.parametrize(
    ("answers", "expected_score"),
    [
        pytest.param({1: 11, 2: 22}, 2, id="all correct"),
        pytest.param({1: 11, 2: 21}, 1, id="one wrong"),
        pytest.param({1: 11}, 1, id="one skipped"),
        pytest.param({}, 0, id="nothing answered"),
        pytest.param({1: 22, 2: 22}, 1, id="correct option of ANOTHER question"),
        pytest.param({1: 999, 2: 22}, 1, id="option id that doesn't exist"),
    ],
)
def test_grade(answers: dict[int, int], expected_score: int) -> None:
    assert attempts.grade(QUESTIONS, answers) == expected_score


# ---------------------------------------------------------------------------
# What the pages show
# ---------------------------------------------------------------------------


def test_saved_answers_skips_answers_whose_option_was_removed() -> None:
    attempt = Attempt(
        answers=[
            AttemptAnswer(question_id=1, option_id=12),
            AttemptAnswer(
                question_id=2, option_id=None
            ),  # option deleted from the bank
        ]
    )
    assert attempts.saved_answers(attempt) == {1: 12}


def test_ordered_questions_use_the_saved_order() -> None:
    passage = make_passage(
        1, [make_question(1, correct=1), make_question(2, correct=2)]
    )
    attempt = Attempt(
        passage=passage, option_order={"1": [13, 11, 12], "2": [22, 23, 21]}
    )

    views = attempts.ordered_questions(attempt)

    assert [v.id for v in views] == [1, 2]  # questions keep their own order
    assert [o.id for o in views[0].options] == [13, 11, 12]
    assert [o.id for o in views[1].options] == [22, 23, 21]


def test_ordered_questions_survive_changes_to_the_question_bank() -> None:
    passage = make_passage(1, [make_question(1, correct=1)])
    # saved before option 12 was added, and while a since-deleted option 19 existed
    attempt = Attempt(passage=passage, option_order={"1": [13, 19, 11]})

    [view] = attempts.ordered_questions(attempt)

    assert [o.id for o in view.options] == [13, 11, 12]  # 19 dropped, 12 appended


def test_ordered_questions_never_reorder_the_models_own_list() -> None:
    passage = make_passage(1, [make_question(1, correct=1)])
    attempt = Attempt(passage=passage, option_order={"1": [13, 12, 11]})

    attempts.ordered_questions(attempt)

    assert [o.id for o in passage.questions[0].options] == [11, 12, 13]
