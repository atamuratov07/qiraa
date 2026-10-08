"""Level 2: the service functions against a real (empty, per-test) database."""

from datetime import timedelta

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app import timeutils
from app.models import Attempt, AttemptAnswer, Passage, User
from app.services import attempts
from tests.factories import T0


def saved_rows(db: Session) -> list[tuple[int, int | None]]:
    db.expire_all()
    rows = db.scalars(select(AttemptAnswer).order_by(AttemptAnswer.question_id)).all()
    return [(r.question_id, r.option_id) for r in rows]


def loaded(db: Session, user: User, attempt: Attempt) -> Attempt:
    result = attempts.load_attempt(db, user, attempt.id)
    assert result is not None
    return result


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


def test_start_creates_an_attempt_with_every_question_shuffled(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)

    assert attempt.id is not None
    assert timeutils.as_utc(attempt.started_at) == T0
    assert (attempt.elapsed_seconds, attempt.submitted_at) == (0, None)
    assert sorted(attempt.option_order) == ["1", "2"]
    assert sorted(attempt.option_order["1"]) == [
        11,
        12,
        13,
    ]  # a reordering of the same ids
    assert sorted(attempt.option_order["2"]) == [21, 22, 23]


def test_start_twice_returns_the_same_open_attempt(
    db: Session, user: User, passage: Passage
) -> None:
    first = attempts.start(db, user, passage, T0)
    second = attempts.start(db, user, passage, T0)
    assert second.id == first.id
    assert len(db.scalars(select(Attempt)).all()) == 1


def test_start_after_submitting_creates_a_new_attempt(
    db: Session, user: User, passage: Passage
) -> None:
    first = loaded(db, user, attempts.start(db, user, passage, T0))
    attempts.submit(db, first, {}, T0)
    assert attempts.start(db, user, passage, T0).id != first.id


def test_double_click_race_returns_the_winning_attempt(
    db: Session, user: User, passage: Passage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two requests both check "no open attempt yet", then both insert.

    We recreate that: the other request's attempt already exists, but our first check
    is made to miss it. The partial unique index must reject our insert, and start()
    must return the other request's attempt instead of failing.
    """
    winner = Attempt(
        user_id=user.id,
        passage_id=passage.id,
        option_order={},
        started_at=T0,
        last_seen_at=T0,
    )
    db.add(winner)
    db.commit()

    real_check = attempts.open_attempt_for
    calls = 0

    def check_that_misses_once(*args: object) -> Attempt | None:
        nonlocal calls
        calls += 1
        return None if calls == 1 else real_check(db, user, passage)

    # monkeypatch replaces the function for this test only, then puts the original back
    monkeypatch.setattr(attempts, "open_attempt_for", check_that_misses_once)

    result = attempts.start(db, user, passage, T0)

    assert result.id == winner.id
    assert calls == 2
    assert len(db.scalars(select(Attempt)).all()) == 1


# ---------------------------------------------------------------------------
# load_attempt
# ---------------------------------------------------------------------------


def test_load_attempt_only_returns_your_own(
    db: Session, user: User, other_user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    assert attempts.load_attempt(db, user, attempt.id) is not None
    assert attempts.load_attempt(db, other_user, attempt.id) is None
    assert attempts.load_attempt(db, user, 999) is None


# ---------------------------------------------------------------------------
# save_answer
# ---------------------------------------------------------------------------


def test_save_answer_inserts_once_then_updates(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    attempts.save_answer(db, attempt, 1, 11)
    attempts.save_answer(db, attempt, 1, 12)
    attempts.save_answer(db, attempt, 1, 13)
    assert saved_rows(db) == [(1, 13)]


def test_save_answer_race_between_two_fast_clicks(
    db: Session,
    engine: Engine,
    user: User,
    passage: Passage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Click 1 and click 2 both find "no answer yet" and both insert.

    We play click 1 ourselves: just before click 2's insert, a separate session (another
    request) saves option 11 and commits. Click 2 then inserts too, the unique constraint
    on (attempt_id, question_id) rejects it, and save_answer must retry as an update.
    """
    attempt = attempts.start(db, user, passage, T0)
    real_set_answer = attempts._set_answer  # pyright: ignore[reportPrivateUsage]
    calls = 0

    def other_request_wins_first(
        session: Session, attempt_id: int, qid: int, oid: int
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            with Session(engine) as other_request:
                other_request.add(
                    AttemptAnswer(attempt_id=attempt_id, question_id=qid, option_id=11)
                )
                other_request.commit()
            # our request already decided "no row yet", so it inserts
            session.add(
                AttemptAnswer(attempt_id=attempt_id, question_id=qid, option_id=oid)
            )
        else:
            real_set_answer(session, attempt_id, qid, oid)

    monkeypatch.setattr(attempts, "_set_answer", other_request_wins_first)

    attempts.save_answer(db, attempt, 1, 12)

    assert calls == 2  # first try hit the constraint, the retry updated
    assert saved_rows(db) == [(1, 12)]  # one row, and the later click wins


@pytest.mark.parametrize(
    ("question_id", "option_id"),
    [
        pytest.param(3, 31, id="question from another passage"),
        pytest.param(1, 21, id="option of another question"),
        pytest.param(1, 999, id="option that doesn't exist"),
    ],
)
def test_save_answer_rejects_options_that_dont_belong(
    db: Session,
    user: User,
    passage: Passage,
    passage2: Passage,
    question_id: int,
    option_id: int,
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    with pytest.raises(attempts.BadAnswer):
        attempts.save_answer(db, attempt, question_id, option_id)
    assert saved_rows(db) == []


# ---------------------------------------------------------------------------
# heartbeat
# ---------------------------------------------------------------------------


def test_heartbeat_saves_and_returns_elapsed(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    assert attempts.heartbeat(db, attempt, T0 + timedelta(seconds=15)) == 15
    assert attempts.heartbeat(db, attempt, T0 + timedelta(seconds=30)) == 30
    db.expire_all()
    stored = db.get(Attempt, attempt.id)
    assert stored is not None and stored.elapsed_seconds == 30


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------


def test_submit_grades_and_closes(db: Session, user: User, passage: Passage) -> None:
    attempt = loaded(db, user, attempts.start(db, user, passage, T0))

    attempts.submit(db, attempt, {1: 11, 2: 22}, T0 + timedelta(seconds=20))

    assert (attempt.score, attempt.total) == (2, 2)
    assert attempt.elapsed_seconds == 20
    assert attempt.submitted_at is not None
    assert timeutils.as_utc(attempt.submitted_at) == T0 + timedelta(seconds=20)
    assert saved_rows(db) == [(1, 11), (2, 22)]


def test_submit_keeps_autosaved_answers_and_ignores_bad_ids(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    attempts.save_answer(db, attempt, 2, 21)  # autosaved earlier (wrong answer)
    attempt = loaded(db, user, attempt)

    # q1 correct; q2 missing from the form; question 99 doesn't exist
    attempts.submit(db, attempt, {1: 11, 99: 5}, T0)

    assert (attempt.score, attempt.total) == (1, 2)
    assert saved_rows(db) == [(1, 11), (2, 21)]


def test_submit_ignores_an_option_of_another_question(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = loaded(db, user, attempts.start(db, user, passage, T0))
    attempts.submit(db, attempt, {1: 22, 2: 22}, T0)  # 22 is q2's correct option
    assert attempt.score == 1
    assert saved_rows(db) == [(2, 22)]


def test_submitted_attempt_cannot_change(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = loaded(db, user, attempts.start(db, user, passage, T0))
    attempts.submit(db, attempt, {1: 11}, T0)

    attempts.submit(db, attempt, {1: 12, 2: 22}, T0)  # a second submit does nothing
    assert attempt.score == 1

    with pytest.raises(attempts.AttemptClosed):
        attempts.save_answer(db, attempt, 1, 12)
    with pytest.raises(attempts.AttemptClosed):
        attempts.heartbeat(db, attempt, T0)
    with pytest.raises(attempts.AttemptClosed):
        attempts.discard(db, attempt)


# ---------------------------------------------------------------------------
# discard
# ---------------------------------------------------------------------------


def test_discard_deletes_the_attempt_and_its_answers(
    db: Session, user: User, passage: Passage
) -> None:
    attempt = attempts.start(db, user, passage, T0)
    attempts.save_answer(db, attempt, 1, 11)

    attempts.discard(db, attempt)

    assert db.scalars(select(Attempt)).all() == []
    assert saved_rows(db) == []


def test_deleting_a_user_deletes_their_attempts(
    db: Session, user: User, passage: Passage
) -> None:
    """Checks the models' ON DELETE CASCADE, which account deletion relies on."""
    attempt = attempts.start(db, user, passage, T0)
    attempts.save_answer(db, attempt, 1, 11)

    db.delete(user)
    db.commit()

    assert db.scalars(select(Attempt)).all() == []
    assert saved_rows(db) == []


# ---------------------------------------------------------------------------
# The passage list
# ---------------------------------------------------------------------------


def test_passage_cards_for_a_new_user(
    db: Session, user: User, passage: Passage, passage2: Passage
) -> None:
    cards = attempts.passage_cards(db, user)
    assert [(c.id, c.question_count, c.best, c.tries, c.unfinished) for c in cards] == [
        (1, 2, None, 0, None),
        (2, 1, None, 0, None),
    ]


def test_passage_cards_show_best_tries_and_unfinished(
    db: Session, user: User, other_user: User, passage: Passage, passage2: Passage
) -> None:
    half = loaded(db, user, attempts.start(db, user, passage, T0))
    attempts.submit(db, half, {1: 11}, T0)  # 50%
    full = loaded(db, user, attempts.start(db, user, passage, T0))
    attempts.submit(db, full, {1: 11, 2: 22}, T0)  # 100%
    still_open = attempts.start(db, user, passage, T0)
    attempts.save_answer(db, still_open, 1, 11)
    attempts.start(db, other_user, passage2, T0)  # someone else's: must not show up

    cards = {c.id: c for c in attempts.passage_cards(db, user)}

    assert (cards[1].best, cards[1].tries) == (100, 2)
    assert cards[1].unfinished is not None
    assert (cards[1].unfinished.id, cards[1].unfinished.answered) == (still_open.id, 1)
    assert (cards[2].best, cards[2].tries, cards[2].unfinished) == (None, 0, None)
    assert attempts.passage_stats(db, user, passage) == (100, 2)
    assert attempts.passage_stats(db, user, passage2) == (None, 0)
