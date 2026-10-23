"""Level 2: importing parsed content files into the database."""

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.content.loader import parse
from app.content.service import NotAllowed
from app.grammar.models import GrammarQuestion
from app.grammar.schemas import GrammarEntry, GrammarFile
from app.grammar.service import import_grammar
from app.passages.models import Passage, PassageOption, PassageQuestion
from app.passages.schemas import PassageEntry, PassageFile
from app.passages.service import import_passages
from app.practice import service
from app.practice.models import Attempt
from tests.factories import T0

TWO_QUESTIONS = """\
passages:
  - slug: b1-media
    text: الفقرة.
    questions:
      - prompt: أول؟
        options: [أ, ب, ج]
        answer: B
      - prompt: ثان؟
        options: [د, ه]
        answer: A
"""

ONE_QUESTION = """\
passages:
  - slug: b1-media
    text: الفقرة.
    questions:
      - prompt: جديد؟
        options: [و, ز]
        answer: B
"""


def entries(text: str) -> list[PassageEntry]:
    return parse(text, PassageFile).passages


def count(db: Session, model: type[Passage | PassageQuestion | PassageOption]) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_reimporting_updates_the_passage_and_keeps_results(
    db: Session, user: User
) -> None:
    first = import_passages(db, entries(TWO_QUESTIONS), owner=None, common=True)
    passage = db.get_one(Passage, first.added[0].id)
    assert (passage.owner_id, passage.is_common) == (None, True)
    assert [[o.is_correct for o in q.options] for q in passage.questions] == [
        [False, True, False],
        [True, False],
    ]

    attempt = service.start(db, user, passage, T0)
    q1 = attempt.content["questions"][0]
    right = next(o["id"] for o in q1["options"] if o["is_correct"])
    service.submit(db, attempt, {q1["id"]: right}, T0)
    copy = attempt.content

    second = import_passages(db, entries(ONE_QUESTION), owner=None, common=True)

    assert (second.added, [p.id for p in second.updated]) == ([], [passage.id])
    assert (
        count(db, Passage),
        count(db, PassageQuestion),
        count(db, PassageOption),
    ) == (1, 1, 2)
    db.expire_all()
    assert [q.prompt for q in db.get_one(Passage, passage.id).questions] == ["جديد؟"]
    kept = db.get_one(Attempt, attempt.id)
    assert (kept.content, kept.score, kept.total) == (copy, 1, 2)


def test_one_slug_in_each_scope_is_a_separate_passage(
    db: Session, user: User, other_user: User, admin: User
) -> None:
    for owner in (user, other_user):
        import_passages(db, entries(TWO_QUESTIONS), owner=owner, common=False)
    import_passages(db, entries(TWO_QUESTIONS), owner=admin, common=True)

    again = import_passages(db, entries(ONE_QUESTION), owner=user, common=False)

    assert (len(again.added), len(again.updated)) == (0, 1)
    owners = db.execute(
        select(Passage.owner_id, Passage.is_common, func.count(PassageQuestion.id))
        .join(Passage.questions)
        .group_by(Passage.id)
        .order_by(Passage.id)
    ).all()
    assert [tuple(row) for row in owners] == [
        (user.id, False, 1),
        (other_user.id, False, 2),
        (admin.id, True, 2),
    ]


def test_an_update_keeps_the_author(db: Session, admin: User) -> None:
    import_passages(db, entries(TWO_QUESTIONS), owner=admin, common=True)
    again = import_passages(db, entries(ONE_QUESTION), owner=admin, common=True)
    from_cli = import_passages(db, entries(TWO_QUESTIONS), owner=None, common=True)

    assert (again.added, from_cli.added) == ([], [])
    assert db.scalars(select(Passage.owner_id)).all() == [admin.id]


def test_only_admins_import_common_content(
    db: Session, engine: Engine, user: User
) -> None:
    with pytest.raises(NotAllowed):
        import_passages(db, entries(TWO_QUESTIONS), owner=user, common=True)

    with Session(engine) as fresh:
        assert count(fresh, Passage) == 0


def test_reimporting_grammar_updates_by_slug_within_each_area(
    db: Session, user: User, other_user: User
) -> None:
    def grammar(answer: str, *options: str) -> list[GrammarEntry]:
        text = f"""\
grammar:
  - slug: case-01
    prompt: جملة ___.
    options: [{", ".join(options)}]
    answer: {answer}
"""
        return parse(text, GrammarFile).grammar

    first = import_grammar(db, grammar("A", "أ", "ب"), owner=user, common=False)
    theirs = import_grammar(db, grammar("A", "أ", "ب"), owner=other_user, common=False)
    again = import_grammar(db, grammar("C", "ج", "د", "ه"), owner=user, common=False)

    assert [i.id for i in again.updated] == [first.added[0].id]
    assert again.added == [] and theirs.added[0].id != first.added[0].id
    db.expire_all()
    mine = db.get_one(GrammarQuestion, first.added[0].id)
    assert [(o.text, o.is_correct) for o in mine.options] == [
        ("ج", False),
        ("د", False),
        ("ه", True),
    ]
