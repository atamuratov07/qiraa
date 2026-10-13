"""
Tests use the qiraa_test database of the Postgres in docker-compose.yml.
TEST_DATABASE_URL points them at another database. Every test drops all tables there.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.auth.models import User
from app.auth.service import SESSION_COOKIE, create_session
from app.core.config import get_settings
from app.core.db import get_db
from app.main import app
from app.models import Base
from app.passages.models import Passage
from tests.factories import make_passage, make_question, make_user

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def default_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Tashkent")
    monkeypatch.setenv("SECURE_COOKIES", "false")
    monkeypatch.setenv("ALLOW_SIGNUP", "true")
    monkeypatch.setenv("SIGNUP_CODE", "")
    monkeypatch.setenv("SESSION_DAYS", "30")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://qiraa:qiraa@localhost:5432/qiraa_test"


@pytest.fixture
def database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture
def engine(database_url: str) -> Iterator[Engine]:
    """A fresh, empty database for one test.

    Tables come from the models (create_all). Alembic is not involved here:
    these tests check the app's behaviour; test_migrations.py and CI check the migrations.
    """
    engine = create_engine(database_url)
    try:
        Base.metadata.drop_all(engine)
    except OperationalError:
        pytest.exit(
            "Test database not reachable. Start it: docker compose up -d --wait db"
        )
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
def admin(db: Session) -> User:
    u = make_user(3, "admin", is_admin=True)
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
    client.cookies.set(SESSION_COOKIE, create_session(db, user))
    return client
