"""Level 3: /manage/grammar (users: peter 1, sarah 2, admin 3)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.grammar.models import GrammarQuestion
from app.grammar.service import pool_counts
from tests.factories import make_grammar_question

URL = "/manage/grammar"


def editor_form(
    answer: str | None, *options: str, prompt: str = "جملة ___."
) -> dict[str, str]:
    """The editor's fields as a browser posts them, a radio included."""
    question = {
        "prompt": prompt,
        "options": list(options or ("أ", "ب", "ج")),
        "answer": answer,
        "explanation": "",
    }
    return {"question": json.dumps(question, ensure_ascii=False), "k1": "k3"}


@pytest.fixture
def owned(db: Session, user: User, other_user: User) -> None:
    db.add_all(
        [
            make_grammar_question(10, owner=user),
            make_grammar_question(11, owner=other_user),
            make_grammar_question(13, owner=None),
        ]
    )
    db.commit()


@pytest.mark.usefixtures("owned")
def test_the_list_shows_what_i_may_edit(
    client: TestClient, db: Session, user: User, admin: User
) -> None:
    def listed(who: User) -> list[int]:
        client.cookies.set(SESSION_COOKIE, create_session(db, who))
        page = client.get(URL).text
        return [qid for qid in (10, 11, 13) if f"{URL}/{qid}/edit" in page]

    assert listed(user) == [10]
    assert listed(admin) == [13]


def test_a_new_question_is_saved_and_joins_my_pool(
    logged_in: TestClient, db: Session, user: User
) -> None:
    response = logged_in.post(f"{URL}/new", data=editor_form("B"))

    assert (response.status_code, response.headers["location"]) == (303, URL)
    question = db.scalars(select(GrammarQuestion)).one()
    assert (question.owner_id, question.is_common, question.slug) == (
        user.id,
        False,
        None,
    )
    assert [o.is_correct for o in question.options] == [False, True, False]
    assert pool_counts(db, user).mine == 1


def test_errors_show_under_their_fields_and_keep_the_input(
    logged_in: TestClient, db: Session
) -> None:
    form = editor_form(None, "أ", " ", prompt="جملة فريدة ___.")
    response = logged_in.post(f"{URL}/new", data=form)

    assert response.status_code == 400
    assert '"answer": "Выберите правильный вариант."' in response.text
    assert '"options[1]": "Значение не может быть пустым."' in response.text
    assert "جملة فريدة ___." in response.text  # the editor is refilled
    assert db.scalars(select(GrammarQuestion)).all() == []


def test_editing_replaces_the_options(
    logged_in: TestClient, db: Session, user: User
) -> None:
    db.add(make_grammar_question(10, owner=user, correct=1))
    db.commit()

    page = logged_in.get(f"{URL}/10/edit").text
    assert f'action="{URL}/10/edit"' in page and "كلمة 3" in page

    form = editor_form("A", "د", "ه") | {"common": "on"}  # ignored from a non-admin
    response = logged_in.post(f"{URL}/10/edit", data=form)

    assert response.status_code == 303
    db.expire_all()
    question = db.get_one(GrammarQuestion, 10)
    assert [(o.text, o.is_correct) for o in question.options] == [
        ("د", True),
        ("ه", False),
    ]
    assert not question.is_common


@pytest.mark.usefixtures("owned")
def test_what_i_may_not_edit_is_a_404(logged_in: TestClient, db: Session) -> None:
    for qid in (11, 13):  # sarah's private, common
        assert logged_in.get(f"{URL}/{qid}/edit").status_code == 404
        assert (
            logged_in.post(f"{URL}/{qid}/edit", data=editor_form("A")).status_code
            == 404
        )
        assert logged_in.post(f"{URL}/{qid}/delete").status_code == 404
    assert db.get(GrammarQuestion, 11) is not None


@pytest.mark.usefixtures("owned")
def test_deleting_my_question(logged_in: TestClient, db: Session) -> None:
    response = logged_in.post(f"{URL}/10/delete")

    assert (response.status_code, response.headers["location"]) == (303, URL)
    assert db.get(GrammarQuestion, 10) is None


def test_publishing_into_a_taken_slug_shows_the_error(
    client: TestClient, db: Session, admin: User
) -> None:
    common = make_grammar_question(5)
    mine = make_grammar_question(6, owner=admin, is_common=False)
    common.slug = mine.slug = "case-01"
    db.add_all([common, mine])
    db.commit()
    client.cookies.set(SESSION_COOKIE, create_session(db, admin))

    response = client.post(f"{URL}/6/edit", data=editor_form("A") | {"common": "on"})

    assert response.status_code == 400
    assert "Слаг case-01 уже занят другим вопросом." in response.text
    db.expire_all()
    assert not db.get_one(GrammarQuestion, 6).is_common
