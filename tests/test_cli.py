"""
The tests call `run()` with the test session; `main()` would open the real database.
"""

from pathlib import Path

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.cli import parse, run
from app.grammar.models import GrammarQuestion
from app.passages.models import Passage


def cli(db: Session, *argv: str) -> int:
    return run(db, parse(argv))


def admins(engine: Engine) -> list[str]:
    """Read from a new session, so only committed changes count."""
    with Session(engine) as fresh:
        return list(fresh.scalars(select(User.username).where(User.is_admin)).all())


@pytest.mark.usefixtures("user", "other_user")
def test_make_admin(
    db: Session, engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli(db, "make-admin", " Peter ") == 0

    assert admins(engine) == ["peter"]
    assert capsys.readouterr().out == "peter is now an admin.\n"


@pytest.mark.usefixtures("user")
def test_make_admin_of_an_unknown_user(
    db: Session, engine: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli(db, "make-admin", "nobody") == 1

    assert admins(engine) == []
    output = capsys.readouterr()
    assert (output.out, output.err) == ("", "No user named 'nobody'.\n")


PASSAGE = """\
passages:
  - slug: b1-media
    text: الفقرة.
    questions:
      - prompt: سؤال؟
        options: [أ, ب]
        answer: {answer}
"""


@pytest.mark.usefixtures("user")
def test_import_adds_then_updates(
    db: Session, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "passages.yaml"
    file.write_text(PASSAGE.format(answer="B"))

    assert cli(db, "import", str(file), "--owner", "peter") == 0
    assert cli(db, "import", str(file), "--owner", "peter") == 0

    assert capsys.readouterr().out == (
        "added 1: b1-media\nupdated 0: -\nadded 0: -\nupdated 1: b1-media\n"
    )
    assert db.scalars(select(Passage.owner_id)).all() == [1]


def test_import_for_an_unknown_owner(
    db: Session, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "passages.yaml"
    file.write_text(PASSAGE.format(answer="B"))

    assert cli(db, "import", str(file), "--owner", "nobody") == 1

    assert capsys.readouterr().err == "No user named 'nobody'.\n"
    assert db.scalars(select(Passage)).all() == []


def test_check(db: Session, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good, bad = tmp_path / "good.yaml", tmp_path / "bad.yaml"
    good.write_text(PASSAGE.format(answer="B"))
    bad.write_text(PASSAGE.format(answer="C"))

    assert cli(db, "check", str(good)) == 0
    assert cli(db, "check", str(bad)) == 1
    assert cli(db, "check", str(tmp_path / "missing.yaml")) == 1

    output = capsys.readouterr()
    assert output.out == f"{good}: 1 passage, no errors\n"
    errors = output.err.splitlines()
    assert errors[0] == (
        f"{bad}:7: passages[0].questions[0].answer: "
        "Answer C is out of range: this question has 2 options."
    )
    assert errors[1].startswith(f"{tmp_path / 'missing.yaml'}: [Errno 2]")


GRAMMAR = """\
grammar:
  - slug: case-01
    prompt: جملة ___.
    options: [أ, ب]
    answer: A
"""


@pytest.mark.usefixtures("user")
def test_a_grammar_file(
    db: Session, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = tmp_path / "grammar.yaml"
    file.write_text(GRAMMAR)

    assert cli(db, "check", str(file)) == 0
    assert cli(db, "import", str(file), "--owner", "peter") == 0

    assert capsys.readouterr().out == (
        f"{file}: 1 grammar question, no errors\nadded 1: case-01\nupdated 0: -\n"
    )
    assert db.scalars(select(GrammarQuestion.owner_id)).all() == [1]
