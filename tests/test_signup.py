import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.core.config import get_settings

CODE = "open-sesame"


def sign_up(
    client: TestClient, username: str, code: str | None = None
) -> httpx.Response:
    form = {"username": username, "password": "password1", "password_confirm": "password1"}
    if code is not None:
        form["code"] = code
    return client.post("/signup", data=form)


def users(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)) or 0


@pytest.fixture
def code_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIGNUP_CODE", CODE)
    get_settings.cache_clear()


def test_without_a_configured_code_the_form_has_no_code_field(
    client: TestClient, db: Session
) -> None:
    assert 'name="code"' not in client.get("/signup").text
    assert sign_up(client, "newcomer").status_code == 303
    assert users(db) == 1


@pytest.mark.usefixtures("code_required")
def test_the_right_code_signs_up(client: TestClient, db: Session) -> None:
    assert 'name="code"' in client.get("/signup").text
    assert sign_up(client, "newcomer", f" {CODE} ").status_code == 303
    assert users(db) == 1


@pytest.mark.parametrize(
    "code",
    [None, "", "wrong", "код"],
    ids=["field missing", "empty", "wrong", "non-ASCII"],
)
@pytest.mark.usefixtures("code_required", "user")
def test_a_bad_code_is_refused_before_anything_else(
    client: TestClient, db: Session, code: str | None
) -> None:
    # "peter" is taken: the answer must still be about the code, never about the name.
    response = sign_up(client, "peter", code)

    assert response.status_code == 400
    assert "Неверный код приглашения." in response.text
    assert "занято" not in response.text
    assert users(db) == 1
