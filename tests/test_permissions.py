"""
Passages used here (users: peter 1, sarah 2, admin 3):
    10  peter's, private
    11  sarah's, private
    12  peter's, published
    13  admin's, common
    14  common, author deleted
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.core.permissions import load_editable, load_visible, visible
from app.passages.models import Passage
from tests.factories import make_passage, make_question


@pytest.fixture
def owned(db: Session, user: User, other_user: User, admin: User) -> None:
    db.add_all(
        [
            make_passage(10, [], owner=user),
            make_passage(11, [], owner=other_user),
            make_passage(12, [], owner=user, is_common=True),
            make_passage(13, [], owner=admin, is_common=True),
            make_passage(14, [], owner=None),
        ]
    )
    db.commit()


@pytest.mark.parametrize(
    ("passage_id", "viewer", "can_view", "can_edit"),
    [
        pytest.param(10, "peter", True, True, id="my private / peter"),
        pytest.param(11, "peter", False, False, id="other's private / peter"),
        pytest.param(12, "peter", True, False, id="my published / peter"),
        pytest.param(13, "peter", True, False, id="common / peter"),
        pytest.param(14, "peter", True, False, id="orphaned common / peter"),
        pytest.param(10, "admin", False, False, id="other's private / admin"),
        pytest.param(11, "admin", False, False, id="other's private 2 / admin"),
        pytest.param(12, "admin", True, True, id="published by a user / admin"),
        pytest.param(13, "admin", True, True, id="my common / admin"),
        pytest.param(14, "admin", True, True, id="orphaned common / admin"),
    ],
)
@pytest.mark.usefixtures("owned")
def test_who_can_view_and_edit(
    db: Session,
    user: User,
    admin: User,
    passage_id: int,
    viewer: str,
    can_view: bool,
    can_edit: bool,
) -> None:
    who = {"peter": user, "admin": admin}[viewer]
    listed = db.scalars(select(Passage.id).where(visible(Passage, who))).all()

    assert (load_visible(db, who, Passage, passage_id) is not None) is can_view
    assert (passage_id in listed) is can_view
    assert (load_editable(db, who, Passage, passage_id) is not None) is can_edit


@pytest.mark.parametrize("viewer", ["peter", "admin"])
def test_someone_elses_private_passage_looks_like_a_missing_one(
    client: TestClient,
    db: Session,
    user: User,
    other_user: User,
    admin: User,
    viewer: str,
) -> None:
    db.add(make_passage(5, [make_question(1, correct=1)], owner=other_user))
    db.commit()
    who = {"peter": user, "admin": admin}[viewer]
    client.cookies.set(SESSION_COOKIE, create_session(db, who))

    for method, path in [("GET", "/passages/{}"), ("POST", "/passages/{}/attempts")]:
        missing = client.request(method, path.format(999))
        private = client.request(method, path.format(5))
        assert missing.status_code == 404
        assert (private.status_code, private.text) == (
            missing.status_code,
            missing.text,
        )

    assert "نص 5" not in client.get("/passages").text


def test_my_private_passage_is_listed_and_can_be_started(
    logged_in: TestClient, db: Session, user: User
) -> None:
    db.add(make_passage(5, [make_question(1, correct=1)], owner=user))
    db.commit()

    assert "نص 5" in logged_in.get("/passages").text
    response = logged_in.post("/passages/5/attempts")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/attempts/")
