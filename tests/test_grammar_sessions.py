"""
Grammar sessions (users: peter 1, sarah 2, admin 3). Questions:
    1, 2  peter's, private
    3     peter's, published
    4     common, author deleted
    5     sarah's, private
"""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.grammar.service import EmptyPool, pool_counts, start_session
from app.grammar.views import PoolCounts
from app.practice.models import Attempt
from tests.factories import T0, make_grammar_question


@pytest.fixture(autouse=True)
def questions(db: Session, user: User, other_user: User) -> None:
    db.add_all(
        [
            make_grammar_question(1, owner=user),
            make_grammar_question(2, owner=user),
            make_grammar_question(3, owner=user, is_common=True),
            make_grammar_question(4, owner=None),
            make_grammar_question(5, owner=other_user),
        ]
    )
    db.commit()


def copied_ids(attempt: Attempt) -> set[int]:
    return {q["id"] for q in attempt.content["questions"]}


def main(page: str) -> str:
    """The page without the header, whose nav links to every section."""
    return page.split("<main", 1)[1]


def test_pool_counts(db: Session, user: User) -> None:
    assert pool_counts(db, user) == PoolCounts(all=4, mine=3)


def test_a_session_takes_at_most_the_whole_pool(db: Session, user: User) -> None:
    attempt = start_session(db, user, "all", 50, T0)

    assert copied_ids(attempt) == {1, 2, 3, 4}
    assert len(attempt.content["questions"]) == 4
    assert (attempt.kind, attempt.passage_id, attempt.content["text"]) == (
        "grammar",
        None,
        "",
    )


def test_only_mine_leaves_out_common_questions(db: Session, user: User) -> None:
    assert copied_ids(start_session(db, user, "mine", 10, T0)) == {1, 2, 3}


def test_an_open_session_is_returned_instead_of_a_new_one(
    db: Session, user: User
) -> None:
    first = start_session(db, user, "all", 2, T0)
    again = start_session(db, user, "mine", 3, T0)

    assert again.id == first.id
    assert db.scalar(select(func.count()).select_from(Attempt)) == 1


def test_an_empty_pool(db: Session, admin: User) -> None:
    with pytest.raises(EmptyPool):
        start_session(db, admin, "mine", 10, T0)


def test_a_session_from_start_to_result(
    logged_in: TestClient, db: Session, user: User
) -> None:
    response = logged_in.post("/grammar/sessions", data={"pool": "mine", "size": "2"})
    assert response.status_code == 303
    url = response.headers["location"]
    attempt_id = url.rsplit("/", 1)[1]

    page = main(logged_in.get(url).text)
    assert "<article" not in page and "Грамматика" in page
    assert 'data-back="/grammar"' in page  # where attempt.js goes once it is discarded
    [first, _second] = [int(i) for i in re.findall(r'data-question-id="(\d+)"', page)]

    saved = logged_in.put(
        f"/api/attempts/{attempt_id}/answers/{first}",
        json={"option_id": first * 10 + 1},  # option 1 is the correct one
    )
    assert saved.status_code == 204
    logged_in.post(f"/attempts/{attempt_id}/submit")

    result = main(logged_in.get(url).text)
    assert "1<span" in result  # the score, 1/2
    assert "Новая сессия" in result and 'action="/passages/' not in result
    assert "Грамматика" in main(logged_in.get("/profile").text)
    db.refresh(user)
    assert user.current_streak == 1


def test_the_start_page_and_an_empty_pool(
    client: TestClient, db: Session, admin: User
) -> None:
    client.cookies.set(SESSION_COOKIE, create_session(db, admin))
    assert "Только мои" in client.get("/grammar").text

    response = client.post("/grammar/sessions", data={"pool": "mine", "size": "5"})

    assert response.status_code == 400
    assert "В этом наборе пока нет вопросов." in response.text
