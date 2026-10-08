"""The profile page: its numbers (service level), then the pages that show them (HTTP)."""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, AttemptAnswer, Passage, User
from app.services import auth
from app.services.profile import CALENDAR_DAYS, profile_context
from app.templating import local_date, plural, ru_date
from app.views import ProfileStats
from tests.factories import T0

NIGHT = datetime(2026, 10, 7, 23, 16, tzinfo=UTC)  # 04:16 on 8 Oct in Tashkent
NOW = datetime(2026, 10, 8, 6, 0, tzinfo=UTC)  # 11:00 on 8 Oct in Tashkent


def submitted(
    user: User, passage: Passage, score: int, total: int, at: datetime
) -> Attempt:
    return Attempt(
        user_id=user.id,
        passage_id=passage.id,
        option_order={},
        started_at=at,
        last_seen_at=at,
        elapsed_seconds=90,
        submitted_at=at,
        score=score,
        total=total,
    )


# ---------------------------------------------------------------------------
# profile_context
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("passage", "passage2")
def test_profile_of_a_new_user(db: Session, user: User) -> None:
    ctx = profile_context(db, user, NOW)

    assert ctx["stats"] == ProfileStats(
        attempts=0, answered=0, accuracy=None, passages_done=0, passages_total=2
    )
    assert (ctx["streak"], ctx["longest_streak"], ctx["recent"]) == (0, 0, [])
    assert ctx["calendar"] is not None
    assert len(ctx["calendar"]) == CALENDAR_DAYS
    assert sum(day.count for day in ctx["calendar"]) == 0
    assert ctx["delete_error"] is None


def test_profile_numbers_and_calendar(
    db: Session, user: User, other_user: User, passage: Passage, passage2: Passage
) -> None:
    db.add_all(
        [
            submitted(user, passage, 3, 5, NIGHT),
            submitted(user, passage, 5, 5, datetime(2026, 10, 6, 10, tzinfo=UTC)),
            submitted(user, passage2, 2, 4, datetime(2026, 9, 1, 10, tzinfo=UTC)),
            Attempt(  # still open: counted nowhere
                user_id=user.id,
                passage_id=passage2.id,
                option_order={},
                started_at=NIGHT,
                last_seen_at=NIGHT,
            ),
            submitted(other_user, passage2, 1, 1, NIGHT),  # someone else's
        ]
    )
    db.commit()

    ctx = profile_context(db, user, NOW)

    # 3 + 5 + 2 = 10 correct of 5 + 5 + 4 = 14 answered; 100 * 10 / 14 = 71.4 -> 71
    assert ctx["stats"] == ProfileStats(
        attempts=3, answered=14, accuracy=71, passages_done=2, passages_total=2
    )
    assert [a.score for a in ctx["recent"]] == [3, 5, 2]  # newest first

    calendar = ctx["calendar"]
    assert calendar is not None
    assert (calendar[0].date, calendar[-1].date) == (
        date(2026, 9, 4),
        date(2026, 10, 8),
    )
    per_day = {day.date: day.count for day in calendar}
    assert per_day[date(2026, 10, 8)] == 1  # the 04:16 quiz, not on 7 Oct
    assert per_day[date(2026, 10, 7)] == 0
    assert per_day[date(2026, 10, 6)] == 1
    assert (
        date(2026, 9, 1) not in per_day
    )  # too old for the calendar, still in the totals


def test_profile_shows_the_visible_streak_not_the_stored_one(
    db: Session, user: User
) -> None:
    user.current_streak, user.longest_streak = 4, 6
    user.last_active_on = date(2026, 10, 5)  # three days before NOW: the streak is over
    db.commit()

    ctx = profile_context(db, user, NOW)

    assert (ctx["streak"], ctx["longest_streak"]) == (0, 6)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def test_profile_page_before_and_after_a_quiz(
    logged_in: TestClient, db: Session, user: User, passage: Passage
) -> None:
    page = logged_in.get("/profile")
    assert page.status_code == 200 and "Пока ничего нет" in page.text

    start = logged_in.post("/passages/1/attempts")
    attempt_url = start.headers["location"]
    logged_in.post(f"{attempt_url}/submit", data={"q1": "11", "q2": "21"})

    page = logged_in.get("/profile")
    assert page.status_code == 200
    assert "50%" in page.text  # accuracy: 1 of 2
    assert f'href="{attempt_url}"' in page.text  # listed under Recent quizzes
    assert "Пока ничего нет" not in page.text


@pytest.mark.usefixtures("passage")
def test_passage_list_shows_the_streak(logged_in: TestClient) -> None:
    page = logged_in.get("/passages")
    assert 'text-muted">0</span>' in page.text  # grey 0 before any quiz

    attempt_url = logged_in.post("/passages/1/attempts").headers["location"]
    logged_in.post(f"{attempt_url}/submit", data={"q1": "11"})

    page = logged_in.get("/passages")
    assert 'text-gold">1</span>' in page.text


def test_wrong_password_on_delete_shows_the_real_profile(
    logged_in: TestClient, db: Session, user: User, passage: Passage
) -> None:
    db.add(submitted(user, passage, 2, 2, T0))
    db.commit()

    page = logged_in.post("/account/delete", data={"password": "wrong-password"})

    assert page.status_code == 400
    assert "Неверный пароль." in page.text
    assert "100%" in page.text  # real accuracy, not placeholder zeros


def test_local_date_filter_shows_the_tashkent_date() -> None:
    assert local_date(NIGHT, "%d %b") == "08 окт"
    assert (
        local_date(NIGHT.replace(tzinfo=None)) == "8 окт 2026"
    )  # naive, as from SQLite


def test_deleting_a_result(
    logged_in: TestClient, db: Session, user: User, passage: Passage
) -> None:
    attempt_url = logged_in.post("/passages/1/attempts").headers["location"]
    logged_in.post(f"{attempt_url}/submit", data={"q1": "11", "q2": "22"})
    assert (
        f'action="{attempt_url}/delete"' in logged_in.get("/profile").text
    )  # the × is there

    response = logged_in.post(f"{attempt_url}/delete", data={"next": "/profile"})

    assert (response.status_code, response.headers["location"]) == (303, "/profile")
    assert db.scalars(select(Attempt)).all() == []
    assert db.scalars(select(AttemptAnswer)).all() == []  # its answers went with it
    assert (
        "Пока ничего нет" in logged_in.get("/profile").text
    )  # totals and the list are recomputed
    db.expire_all()
    assert (user.current_streak, user.last_active_on is not None) == (
        1,
        True,
    )  # streak kept


def test_cannot_delete_someone_elses_result(
    client: TestClient, db: Session, user: User, other_user: User, passage: Passage
) -> None:
    db.add(submitted(user, passage, 1, 2, T0))
    db.commit()
    client.cookies.set(auth.SESSION_COOKIE, auth.create_session(db, other_user))

    response = client.post("/attempts/1/delete", data={"next": "/profile"})

    assert response.status_code == 404
    assert len(db.scalars(select(Attempt)).all()) == 1


@pytest.mark.usefixtures("passage")
def test_delete_only_redirects_within_the_site(logged_in: TestClient) -> None:
    attempt_url = logged_in.post("/passages/1/attempts").headers["location"]
    logged_in.post(f"{attempt_url}/submit", data={"q1": "11"})
    response = logged_in.post(f"{attempt_url}/delete", data={"next": "//evil.example"})
    assert response.headers["location"] == "/profile"


def test_ru_date_uses_russian_names() -> None:
    assert ru_date(date(2026, 10, 8), "%a, %-d %b") == "чт, 8 окт"


@pytest.mark.parametrize(
    ("n", "word"),
    [
        (0, "дней"),
        (1, "день"),
        (2, "дня"),
        (4, "дня"),
        (5, "дней"),
        (11, "дней"),
        (14, "дней"),
        (21, "день"),
        (22, "дня"),
        (111, "дней"),
        (101, "день"),
    ],
)
def test_plural(n: int, word: str) -> None:
    assert plural(n, "день", "дня", "дней") == word
