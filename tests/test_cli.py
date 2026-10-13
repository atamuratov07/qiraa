"""
The tests call `run()` with the test session; `main()` would open the real database.
"""

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.cli import parse, run


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
