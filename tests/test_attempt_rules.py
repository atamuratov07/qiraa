"""Level 1: the pure rules. No database, no HTTP; each test runs in about a millisecond.

The objects below are built in memory and never saved. SQLAlchemy models work as
ordinary Python objects until you add them to a session.
"""

from datetime import timedelta

import pytest

from app.practice.models import Attempt
from app.practice.service import (
    apply_heartbeat,
    copy_passage,
    grade,
    has_option,
    is_paused,
)
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
    apply_heartbeat(attempt, now)
    # Assert
    assert attempt.elapsed_seconds == expected_elapsed
    assert attempt.last_seen_at == now


def test_apply_heartbeat_accepts_naive_datetimes() -> None:
    attempt = Attempt(elapsed_seconds=0, last_seen_at=T0.replace(tzinfo=None))
    apply_heartbeat(attempt, T0 + timedelta(seconds=10))
    assert attempt.elapsed_seconds == 10


@pytest.mark.parametrize(("seconds_later", "paused"), [(30, False), (31, True)])
def test_is_paused(seconds_later: int, paused: bool) -> None:
    attempt = Attempt(last_seen_at=T0)
    assert is_paused(attempt, T0 + timedelta(seconds=seconds_later)) is paused


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

CONTENT = copy_passage(
    make_passage(1, [make_question(1, correct=1), make_question(2, correct=2)]),
    shuffle=lambda options: None,
)


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
    assert grade(CONTENT["questions"], answers) == expected_score


@pytest.mark.parametrize(
    ("question_id", "option_id", "expected"),
    [(1, 12, True), (1, 22, False), (3, 31, False)],
    ids=["its own option", "another question's option", "not in this attempt"],
)
def test_has_option(question_id: int, option_id: int, expected: bool) -> None:
    assert has_option(CONTENT, question_id, option_id) is expected


# ---------------------------------------------------------------------------
# The copy an attempt keeps
# ---------------------------------------------------------------------------


def test_copy_passage_keeps_the_questions_in_order_and_shuffles_options() -> None:
    passage = make_passage(
        1, [make_question(1, correct=1), make_question(2, correct=2)]
    )

    content = copy_passage(passage, shuffle=lambda options: options.reverse())

    assert (content["title"], content["level"]) == ("نص 1", "A2")
    assert [q["id"] for q in content["questions"]] == [1, 2]
    assert content["questions"][0]["options"] == [
        {"id": 13, "text": "خيار 3", "is_correct": False},
        {"id": 12, "text": "خيار 2", "is_correct": False},
        {"id": 11, "text": "خيار 1", "is_correct": True},
    ]
