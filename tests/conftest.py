"""
Set TEST_DATABASE_URL to run the same tests against Postgres, e.g.
    TEST_DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/qiraa_test uv run pytest
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db
from app.main import app
from app.models import Base, Passage, User
from app.services import auth
from tests.factories import make_passage, make_question, make_user

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    """A fresh, empty database for one test.

    `tmp_path` is a built-in pytest fixture: a new empty folder for each test.
    Tables come from the models (create_all). Alembic is not involved here: these tests
    check the app's behaviour, and migrations are checked when you run `alembic upgrade`.
    """
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _foreign_keys_on(
            dbapi_connection: sqlite3.Connection, _record: object
        ) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db: Session) -> User:
    u = make_user(1, "peter")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def other_user(db: Session) -> User:
    u = make_user(2, "sarah")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def passage(db: Session) -> Passage:
    p = make_passage(1, [make_question(1, correct=1), make_question(2, correct=2)])
    db.add(p)
    db.commit()
    return p


@pytest.fixture
def passage2(db: Session) -> Passage:
    p = make_passage(2, [make_question(3, correct=3)], level="B1")
    db.add(p)
    db.commit()
    return p


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    """Calls the app in-process, like a browser that never leaves your computer.

    `dependency_overrides` swaps get_db for one that uses the test database, so every
    route, and every dependency built on get_db (like CurrentUser), sees the test data.
    `follow_redirects=False` lets tests check a redirect's status and Location header.
    """
    test_sessions = sessionmaker(bind=engine)

    def get_test_db() -> Iterator[Session]:
        with test_sessions() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def logged_in(client: TestClient, db: Session, user: User) -> TestClient:
    client.cookies.set(auth.SESSION_COOKIE, auth.create_session(db, user))
    return client
