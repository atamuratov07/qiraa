"""Level 3: the import page, through HTTP requests as a browser sends them."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.content.loader import MAX_BYTES, parse
from app.content.prompt import EXAMPLE
from app.passages.models import Passage

URL = "/manage/import"
PASSAGE = """\
passages:
  - slug: b1-media
    title: الإعلام
    text: الفقرة.
    questions:
      - prompt: سؤال؟
        options: [أ, ب]
        answer: {answer}
"""


def stored(db: Session) -> list[tuple[str | None, int | None, bool]]:
    db.expire_all()
    query = select(Passage.slug, Passage.owner_id, Passage.is_common)
    return list(db.execute(query).all())


def test_logged_out_goes_to_login(client: TestClient) -> None:
    response = client.get(URL)
    assert response.headers["location"] == "/login?next=/manage/import"


def test_the_common_checkbox_is_for_admins_only(
    client: TestClient, db: Session, user: User, admin: User
) -> None:
    client.cookies.set(SESSION_COOKIE, create_session(db, user))
    assert 'name="common"' not in client.get(URL).text
    client.cookies.set(SESSION_COOKIE, create_session(db, admin))
    assert 'name="common"' in client.get(URL).text


def test_a_pasted_file_is_imported_privately(
    logged_in: TestClient, db: Session, user: User
) -> None:
    # common=on from a non-admin is ignored
    response = logged_in.post(
        URL, data={"text": PASSAGE.format(answer="B"), "common": "on"}
    )

    assert response.status_code == 200
    assert "Добавлен 1 текст" in response.text
    [(slug, owner_id, is_common)] = stored(db)
    assert (slug, owner_id, is_common) == ("b1-media", user.id, False)
    assert "الإعلام" in logged_in.get("/passages").text

    again = logged_in.post(URL, data={"text": PASSAGE.format(answer="A")})
    assert "Обновлён 1 текст" in again.text and len(stored(db)) == 1


def test_an_admin_imports_common_passages(
    client: TestClient, db: Session, admin: User
) -> None:
    client.cookies.set(SESSION_COOKIE, create_session(db, admin))
    client.post(URL, data={"text": PASSAGE.format(answer="B"), "common": "on"})

    assert stored(db) == [("b1-media", admin.id, True)]


def test_errors_show_their_line_and_keep_the_text(
    logged_in: TestClient, db: Session
) -> None:
    text = PASSAGE.format(answer="C")
    response = logged_in.post(URL, data={"text": text})

    assert response.status_code == 400
    assert "Строка 8" in response.text
    assert "passages[0].questions[0].answer" in response.text
    assert "الإعلام" in response.text  # the text box is refilled
    assert stored(db) == []


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("﻿" + PASSAGE.format(answer="B"), None),  # saved with a BOM
        (PASSAGE.format(answer="B"), None),
        ("title: نص".encode("cp1256"), "Файл не в кодировке UTF-8"),
        (b"#" * (MAX_BYTES + 1), "Файл больше 1 MB"),
    ],
    ids=["bom", "plain", "windows-1256", "too-large"],
)
def test_an_uploaded_file(
    logged_in: TestClient, db: Session, raw: str | bytes, message: str | None
) -> None:
    content = raw.encode() if isinstance(raw, str) else raw
    response = logged_in.post(
        URL, data={"text": "ignored"}, files={"file": ("p.yaml", content)}
    )

    if message is None:
        assert response.status_code == 200 and len(stored(db)) == 1
    else:
        assert response.status_code == 400 and message in response.text


def test_the_page_shows_a_prompt_whose_example_is_valid(logged_in: TestClient) -> None:
    assert parse(EXAMPLE).passages[0].slug == "a2-market"
    page = logged_in.get(URL).text
    assert "Convert the material I give you" in page
    assert "2 to 6 different options" in page
