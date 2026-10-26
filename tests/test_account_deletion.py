"""
Peter (1) deletes his account. Passage 5 is his private one, passage 6 he wrote and was
published; Sarah (2) has an attempt on passage 6. Grammar questions 7 and 8 are his,
private and published.
"""

import pytest
from psycopg.errors import CheckViolation
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import hash_password
from app.auth.service import delete_account
from app.grammar.models import GrammarOption, GrammarQuestion
from app.passages.models import Passage, PassageOption, PassageQuestion
from app.passages.service import start_attempt
from app.practice import service
from app.practice.models import Attempt, AttemptAnswer
from tests.factories import T0, make_grammar_question, make_passage, make_question

PASSWORD = "correct-horse"


@pytest.fixture
def content(db: Session, user: User, other_user: User) -> None:
    user.password_hash = hash_password(PASSWORD)
    private = make_passage(5, [make_question(1, correct=1)], owner=user)
    published = make_passage(
        6, [make_question(2, correct=2)], owner=user, is_common=True
    )
    db.add_all(
        [
            private,
            published,
            make_grammar_question(7, owner=user),
            make_grammar_question(8, owner=user, is_common=True),
        ]
    )
    db.commit()

    mine = start_attempt(db, user, private, T0)
    service.save_answer(db, mine, question_id=1, option_id=11)
    theirs = start_attempt(db, other_user, published, T0)
    service.save_answer(db, theirs, question_id=2, option_id=22)


def count(db: Session, model: type, *where: ColumnElement[bool]) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


@pytest.mark.usefixtures("content")
def test_deleting_an_account_removes_private_content_and_keeps_common(
    db: Session, user: User
) -> None:
    delete_account(db, user, PASSWORD)

    assert count(db, User, User.id == 1) == 0
    assert count(db, Passage, Passage.id == 5) == 0
    assert count(db, PassageQuestion, PassageQuestion.id == 1) == 0
    assert count(db, PassageOption, PassageOption.question_id == 1) == 0
    assert count(db, Attempt, Attempt.user_id == 1) == 0
    assert count(db, AttemptAnswer, AttemptAnswer.question_id == 1) == 0
    assert count(db, GrammarQuestion, GrammarQuestion.id == 7) == 0
    assert count(db, GrammarOption, GrammarOption.question_id == 7) == 0

    published = db.scalars(select(Passage).where(Passage.id == 6)).one()
    assert (published.owner_id, published.is_common) == (None, True)
    assert count(db, Attempt, Attempt.user_id == 2, Attempt.passage_id == 6) == 1
    assert count(db, AttemptAnswer, AttemptAnswer.question_id == 2) == 1
    assert db.execute(
        select(GrammarQuestion.owner_id, GrammarQuestion.is_common).where(
            GrammarQuestion.id == 8
        )
    ).one() == (None, True)


@pytest.mark.usefixtures("content")
def test_deleting_the_user_alone_is_refused_by_the_check(
    db: Session, user: User
) -> None:
    db.delete(user)
    with pytest.raises(IntegrityError) as error:
        db.commit()
    db.rollback()

    assert isinstance(error.value.orig, CheckViolation)
    assert error.value.orig.diag.constraint_name in {  # Postgres stops at the first
        "ck_passages_common_or_owned",
        "ck_grammar_questions_common_or_owned",
    }
    assert count(db, User, User.id == 1) == 1
    assert count(db, Passage, Passage.owner_id == 1) == 2
