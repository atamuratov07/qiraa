"""Level 3: the routes, through HTTP requests, as a browser and attempt.js would send them."""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attempt, Passage, User
from app.services import auth


def start(client: TestClient, passage_id: int = 1) -> int:
    response = client.post(f"/passages/{passage_id}/attempts")
    assert response.status_code == 303
    return int(response.headers["location"].removeprefix("/attempts/"))


def stored_attempt(db: Session, attempt_id: int) -> Attempt:
    db.expire_all()
    attempt = db.get(Attempt, attempt_id)
    assert attempt is not None
    return attempt


# ---------------------------------------------------------------------------
# The whole journey
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("passage")
def test_practice_from_start_to_result(logged_in: TestClient, db: Session) -> None:
    client = logged_in

    page = client.get("/passages/1")
    assert page.status_code == 200
    assert "2 вопроса" in page.text and "лучший результат" not in page.text

    attempt_id = start(client)
    page = client.get(f"/attempts/{attempt_id}")
    assert page.status_code == 200
    assert re.search(
        r'id="pause-overlay"\s+hidden', page.text
    )  # just started: not paused

    # autosave, as attempt.js sends it
    assert (
        client.put(
            f"/api/attempts/{attempt_id}/answers/1", json={"option_id": 12}
        ).status_code
        == 204
    )
    assert (
        client.put(
            f"/api/attempts/{attempt_id}/answers/1", json={"option_id": 11}
        ).status_code
        == 204
    )
    beat = client.post(f"/api/attempts/{attempt_id}/heartbeat")
    assert beat.status_code == 200 and beat.json()["elapsed_seconds"] >= 0

    # the submit form sends every pick as q<question id>=<option id>
    response = client.post(
        f"/attempts/{attempt_id}/submit", data={"q1": "11", "q2": "22"}
    )
    assert (response.status_code, response.headers["location"]) == (
        303,
        f"/attempts/{attempt_id}",
    )
    assert (
        stored_attempt(db, attempt_id).score,
        stored_attempt(db, attempt_id).total,
    ) == (2, 2)

    result = client.get(f"/attempts/{attempt_id}")
    assert result.status_code == 200 and "100% верно" in result.text
    assert "лучший результат 100% за 1 попытку" in client.get("/passages/1").text
    assert "Лучший результат 100% · 1 попытка" in client.get("/passages").text


# ---------------------------------------------------------------------------
# Open attempts
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("passage")
def test_open_attempt_is_resumed_not_duplicated(logged_in: TestClient) -> None:
    attempt_id = start(logged_in)
    assert start(logged_in) == attempt_id

    response = logged_in.get("/passages/1")
    assert (response.status_code, response.headers["location"]) == (
        303,
        f"/attempts/{attempt_id}",
    )

    logged_in.put(f"/api/attempts/{attempt_id}/answers/2", json={"option_id": 21})
    assert "Не завершён · отвечено 1/2" in logged_in.get("/passages").text


@pytest.mark.usefixtures("passage")
def test_discard_only_redirects_within_the_site(
    logged_in: TestClient, db: Session
) -> None:
    attempt_id = start(logged_in)
    response = logged_in.post(
        f"/attempts/{attempt_id}/discard", data={"next": "//evil.example"}
    )
    assert (response.status_code, response.headers["location"]) == (303, "/passages")
    assert db.scalars(select(Attempt)).all() == []

    attempt_id = start(logged_in)
    response = logged_in.post(
        f"/attempts/{attempt_id}/discard", data={"next": "/passages/1"}
    )
    assert response.headers["location"] == "/passages/1"


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("passage")
def test_submit_skips_malformed_form_fields(logged_in: TestClient, db: Session) -> None:
    attempt_id = start(logged_in)
    form = {
        "q1": "²",
        "qx": "5",
        "q2": "22",
        "unrelated": "x",
    }  # "²".isdigit() is True!
    assert (
        logged_in.post(f"/attempts/{attempt_id}/submit", data=form).status_code == 303
    )
    assert stored_attempt(db, attempt_id).score == 1


@pytest.mark.usefixtures("passage", "passage2")
def test_autosave_rejects_bad_answers(logged_in: TestClient) -> None:
    attempt_id = start(logged_in)
    url = f"/api/attempts/{attempt_id}/answers/1"

    response = logged_in.put(
        url, json={"option_id": 31}
    )  # option of passage 2's question
    assert (
        response.status_code == 400
        and "не относится к вопросу" in response.json()["detail"]
    )
    assert logged_in.put(url, json={"option_id": "x"}).status_code == 422  # Pydantic
    assert logged_in.put(url, json={}).status_code == 422


@pytest.mark.usefixtures("passage")
def test_submitted_attempt_is_read_only(logged_in: TestClient, db: Session) -> None:
    attempt_id = start(logged_in)
    logged_in.post(f"/attempts/{attempt_id}/submit", data={"q1": "11"})

    heartbeat = logged_in.post(f"/api/attempts/{attempt_id}/heartbeat")
    assert heartbeat.status_code == 409  # attempt.js reloads the page on 409
    autosave = logged_in.put(
        f"/api/attempts/{attempt_id}/answers/1", json={"option_id": 12}
    )
    assert autosave.status_code == 409
    discard = logged_in.post(f"/attempts/{attempt_id}/discard")
    assert discard.status_code == 409 and "text/html" in discard.headers["content-type"]
    resubmit = logged_in.post(f"/attempts/{attempt_id}/submit", data={"q1": "12"})
    assert resubmit.status_code == 303
    assert stored_attempt(db, attempt_id).score == 1


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


def test_someone_elses_attempt_is_404(
    client: TestClient, db: Session, user: User, other_user: User, passage: Passage
) -> None:
    client.cookies.set(auth.SESSION_COOKIE, auth.create_session(db, user))
    attempt_id = start(client)
    client.cookies.set(auth.SESSION_COOKIE, auth.create_session(db, other_user))

    page = client.get(f"/attempts/{attempt_id}")
    assert page.status_code == 404 and "text/html" in page.headers["content-type"]
    api = client.post(f"/api/attempts/{attempt_id}/heartbeat")
    assert (api.status_code, api.json()) == (404, {"detail": "Попытка не найдена"})
    assert client.post(f"/attempts/{attempt_id}/discard").status_code == 404


@pytest.mark.usefixtures("passage")
def test_logged_out_pages_redirect_and_api_says_401(client: TestClient) -> None:
    page = client.get("/passages/1")
    assert (page.status_code, page.headers["location"]) == (
        303,
        "/login?next=/passages/1",
    )
    api = client.post("/api/attempts/1/heartbeat")
    assert api.status_code == 401


def test_unknown_passage_is_404(logged_in: TestClient) -> None:
    assert logged_in.get("/passages/999").status_code == 404
    assert logged_in.post("/passages/999/attempts").status_code == 404
