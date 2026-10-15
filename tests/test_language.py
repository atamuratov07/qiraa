import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import hash_password
from app.core.i18n import LOCALE_COOKIE

PASSWORD = "password1"


def saved_locale(engine: Engine, username: str) -> str | None:
    """Read from a new session, so only committed changes count."""
    with Session(engine) as fresh:
        return fresh.scalar(select(User.locale).where(User.username == username))


def menu_next(html: str) -> str:
    menu = html.split('action="/settings/language"')[1]
    match = re.search(r'name="next" value="([^"]*)"', menu)
    assert match is not None
    return match.group(1)


def test_switching_sets_the_cookie_and_returns_to_the_page(client: TestClient) -> None:
    response = client.post(
        "/settings/language", data={"locale": "uz", "next": "/login?next=/profile"}
    )

    assert (response.status_code, response.headers["location"]) == (
        303,
        "/login?next=/profile",
    )
    assert client.cookies[LOCALE_COOKIE] == "uz"
    page = client.get("/login?next=/profile").text
    assert '<html lang="uz">' in page and "<title>Kirish" in page


def test_a_logged_in_switch_is_saved_to_the_account(
    logged_in: TestClient, engine: Engine
) -> None:
    logged_in.post("/settings/language", data={"locale": "en"})

    assert saved_locale(engine, "peter") == "en"


def test_logging_in_brings_back_the_saved_language(
    client: TestClient, db: Session, user: User
) -> None:
    user.password_hash = hash_password(PASSWORD)
    user.locale = "uz"
    db.commit()

    client.post("/login", data={"username": "peter", "password": PASSWORD})

    assert client.cookies[LOCALE_COOKIE] == "uz"  # the client started with ru


def test_signing_up_saves_the_language_in_use(
    client: TestClient, engine: Engine
) -> None:
    form = {"username": "newcomer", "password": PASSWORD, "password_confirm": PASSWORD}
    assert client.post("/signup", data=form).status_code == 303

    assert saved_locale(engine, "newcomer") == "ru"


@pytest.mark.parametrize(
    ("form", "status", "location"),
    [
        ({"locale": "de", "next": "/profile"}, 400, None),
        ({"locale": "en", "next": "//evil.example"}, 303, "/passages"),
    ],
    ids=["unknown language", "next to another site"],
)
def test_bad_input(
    client: TestClient, form: dict[str, str], status: int, location: str | None
) -> None:
    response = client.post("/settings/language", data=form)

    assert (response.status_code, response.headers.get("location")) == (
        status,
        location,
    )


@pytest.mark.parametrize(
    ("referer", "expected"),
    [
        ("http://testserver/signup", "/signup"),
        (None, "/passages"),
        ("https://evil.example/signup", "/passages"),
        ("http://testserver/logout", "/passages"),
    ],
    ids=["the form's page", "no referer", "another site", "a POST-only page"],
)
def test_after_a_failed_post_the_menu_returns_to_the_form(
    client: TestClient, referer: str | None, expected: str
) -> None:
    headers = {"referer": referer} if referer else {}
    form = {"username": "x", "password": "1", "password_confirm": "2"}
    page = client.post("/signup", data=form, headers=headers)

    assert page.status_code == 400
    assert menu_next(page.text) == expected


def test_on_a_get_page_the_menu_returns_to_the_same_url(client: TestClient) -> None:
    assert menu_next(client.get("/login?next=/profile").text) == "/login?next=/profile"
