"""Level 3: /manage/passages (users: peter 1, sarah 2, admin 3)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.passages.models import Passage
from tests.factories import make_passage

URL = "/manage/passages"


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
