"""Level 3: /manage/passages (users: peter 1, sarah 2, admin 3)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.passages.models import Passage
from tests.factories import make_passage, make_question

URL = "/manage/passages"


def editor_form(*answers: str | None, prompt: str = "سؤال؟") -> dict[str, str]:
    """The editor's fields as a browser posts them, radios included."""
    passage = {
        "title": "",
        "level": "A2",
        "text": "الفقرة.",
        "translation_ru": "",
        "questions": [
            {
                "prompt": prompt,
                "options": ["أ", "ب", "ج"],
                "answer": a,
                "explanation": "",
            }
            for a in answers
        ],
    }
    return {"passage": json.dumps(passage, ensure_ascii=False), "k1": "k3"}


@pytest.fixture
def owned(db: Session, user: User, other_user: User) -> None:
    db.add_all(
        [
            make_passage(10, [], owner=user),
            make_passage(11, [], owner=other_user),
            make_passage(13, [], owner=None),
        ]
    )
    db.commit()


def test_logged_out_goes_to_login(client: TestClient) -> None:
    assert client.get(URL).headers["location"] == "/login?next=/manage/passages"


@pytest.mark.usefixtures("owned")
def test_the_list_shows_what_i_may_edit(
    client: TestClient, db: Session, user: User, admin: User
) -> None:
    def listed(who: User) -> list[int]:
        client.cookies.set(SESSION_COOKIE, create_session(db, who))
        page = client.get(URL).text
        return [pid for pid in (10, 11, 13) if f"نص {pid}" in page]

    assert listed(user) == [10]
    assert listed(admin) == [13]


@pytest.mark.usefixtures("owned")
def test_deleting_my_passage(logged_in: TestClient, db: Session) -> None:
    response = logged_in.post(f"{URL}/10/delete")

    assert (response.status_code, response.headers["location"]) == (303, URL)
    assert db.get(Passage, 10) is None


@pytest.mark.parametrize(
    ("passage_id", "viewer"),
    [
        pytest.param(11, "peter", id="sarah's private / peter"),
        pytest.param(13, "peter", id="common / peter"),
        pytest.param(10, "admin", id="peter's private / admin"),
    ],
)
@pytest.mark.usefixtures("owned")
def test_deleting_what_i_may_not_edit_is_a_404(
    client: TestClient,
    db: Session,
    user: User,
    admin: User,
    passage_id: int,
    viewer: str,
) -> None:
    who = {"peter": user, "admin": admin}[viewer]
    client.cookies.set(SESSION_COOKIE, create_session(db, who))

    assert client.post(f"{URL}/{passage_id}/delete").status_code == 404
    assert db.get(Passage, passage_id) is not None


def test_a_new_passage_is_saved_and_can_be_practised(
    logged_in: TestClient, db: Session, user: User
) -> None:
    response = logged_in.post(f"{URL}/new", data=editor_form("B", "C"))

    assert (response.status_code, response.headers["location"]) == (303, URL)
    passage = db.scalars(select(Passage)).one()
    assert (passage.owner_id, passage.is_common, passage.title) == (
        user.id,
        False,
        None,
    )
    assert logged_in.post(f"/passages/{passage.id}/attempts").status_code == 303


def test_errors_show_under_their_fields_and_keep_the_input(
    logged_in: TestClient, db: Session
) -> None:
    form = editor_form(None, prompt="سؤال فريد؟")
    form["passage"] = form["passage"].replace('"ب"', '" "')
    response = logged_in.post(f"{URL}/new", data=form)

    assert response.status_code == 400
    assert '"questions[0].answer": "Выберите правильный вариант."' in response.text
    assert (
        '"questions[0].options[1]": "Значение не может быть пустым."' in response.text
    )
    assert "سؤال فريد؟" in response.text  # the editor is refilled
    assert db.scalars(select(Passage)).all() == []


def test_a_payload_that_is_not_json_is_refused(logged_in: TestClient) -> None:
    response = logged_in.post(f"{URL}/new", data={"passage": "{not json"})
    assert response.status_code == 400 and '"data": null' in response.text


def test_editing_replaces_the_questions(
    logged_in: TestClient, db: Session, user: User
) -> None:
    db.add(
        make_passage(
            10, [make_question(1, correct=1), make_question(2, correct=2)], owner=user
        )
    )
    db.commit()

    page = logged_in.get(f"{URL}/10/edit").text
    assert 'action="/manage/passages/10/edit"' in page and "سؤال 2؟" in page

    response = logged_in.post(f"{URL}/10/edit", data=editor_form("C"))

    assert response.status_code == 303
    db.expire_all()
    [question] = db.get_one(Passage, 10).questions
    assert [o.is_correct for o in question.options] == [False, False, True]


@pytest.mark.usefixtures("owned")
def test_editing_what_i_may_not_edit_is_a_404(logged_in: TestClient) -> None:
    for pid in (11, 13):  # sarah's private, common
        assert logged_in.get(f"{URL}/{pid}/edit").status_code == 404
        response = logged_in.post(f"{URL}/{pid}/edit", data=editor_form("A"))
        assert response.status_code == 404


def test_publishing_into_a_taken_slug_shows_the_error(
    client: TestClient, db: Session, admin: User
) -> None:
    common = make_passage(5, [])
    mine = make_passage(6, [make_question(1, correct=1)], owner=admin, is_common=False)
    common.slug = mine.slug = "b1-media"
    db.add_all([common, mine])
    db.commit()
    client.cookies.set(SESSION_COOKIE, create_session(db, admin))

    form = editor_form("A") | {"common": "on"}
    response = client.post(f"{URL}/6/edit", data=form)

    assert response.status_code == 400
    assert "Слаг b1-media уже занят другим текстом." in response.text
    db.expire_all()
    assert not db.get_one(Passage, 6).is_common
