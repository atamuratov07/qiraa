"""Level 2: the services behind the passage editor (users: peter 1, admin 3)."""

import pytest
from sqlalchemy.orm import Session

from app.auth.models import User
from app.passages.schemas import PassageIn
from app.passages.service import (
    SlugTaken,
    create_passage,
    managed_passages,
    passage_in,
    update_passage,
)
from tests.factories import make_passage, make_question


def data(*answers: str) -> PassageIn:
    return PassageIn.model_validate(
        {
            "text": "الفقرة.",
            "translation_ru": "Абзац.",
            "glossary": {"فقرة": "абзац"},
            "questions": [
                {"prompt": f"سؤال {i}؟", "options": ["أ", "ب", "ج"], "answer": a}
                for i, a in enumerate(answers, start=1)
            ],
        }
    )


def test_a_created_passage_reads_back_as_it_was_written(
    db: Session, user: User
) -> None:
    written = data("B", "C")
    passage = create_passage(db, user, written, common=True)  # ignored: not an admin

    db.expire_all()
    assert (passage.owner_id, passage.is_common, passage.slug) == (user.id, False, None)
    assert passage_in(passage) == written


@pytest.mark.parametrize(
    ("owner", "is_common", "common", "expected"),
    [
        pytest.param("admin", False, True, ("admin", True), id="publish my own"),
        pytest.param(None, True, False, ("admin", False), id="unpublish authorless"),
        pytest.param("peter", True, False, ("peter", False), id="unpublish peter's"),
    ],
)
def test_an_admin_publishes_and_unpublishes(
    db: Session,
    user: User,
    admin: User,
    owner: str | None,
    is_common: bool,
    common: bool,
    expected: tuple[str, bool],
) -> None:
    users = {"peter": user, "admin": admin}
    passage = make_passage(
        5,
        [make_question(1, correct=1)],
        owner=users[owner] if owner else None,
        is_common=is_common,
    )
    db.add(passage)
    db.commit()

    update_passage(db, admin, passage, data("A"), common=common)

    db.expire_all()
    expected_owner, expected_common = expected
    assert (passage.owner_id, passage.is_common) == (
        users[expected_owner].id,
        expected_common,
    )


def test_publishing_into_a_taken_slug_changes_nothing(db: Session, admin: User) -> None:
    common = make_passage(5, [make_question(1, correct=1)])
    mine = make_passage(6, [make_question(2, correct=1)], owner=admin, is_common=False)
    common.slug = mine.slug = "b1-media"
    db.add_all([common, mine])
    db.commit()

    with pytest.raises(SlugTaken) as excinfo:
        update_passage(db, admin, mine, data("A", "B"), common=True)

    assert excinfo.value.slug == "b1-media"
    db.expire_all()
    assert not mine.is_common and [q.id for q in mine.questions] == [2]


def test_managed_passages_are_the_editable_ones(
    db: Session, user: User, other_user: User, admin: User
) -> None:
    db.add_all(
        [
            make_passage(10, [make_question(1, correct=1)], owner=user),
            make_passage(11, [], owner=other_user),
            make_passage(12, [], owner=user, is_common=True),
            make_passage(13, [], owner=admin, is_common=True),
            make_passage(14, [], owner=None),
            make_passage(15, [], owner=admin),
        ]
    )
    db.commit()

    mine = managed_passages(db, user)
    assert [(p.id, p.question_count) for p in mine] == [(10, 1)]
    # private first
    assert [p.id for p in managed_passages(db, admin)] == [15, 12, 13, 14]
