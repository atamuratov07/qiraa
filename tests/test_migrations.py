"""
Alembic runs here against the test database, starting from an empty schema. The other
tests build tables with create_all, so they can't notice a migration that forgot
something autogenerate doesn't detect, like a CHECK constraint.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import CheckConstraint, Engine, create_engine, inspect, text

from app.core.config import BASE_DIR, get_settings
from app.models import Base

INITIAL = "6ad753184ecc"


def upgrade(revision: str) -> None:
    config = Config()  # without alembic.ini, env.py leaves pytest's logging alone
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(config, revision)


@pytest.fixture
def empty_db(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    # env.py migrates whatever the settings point at.
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "")
    get_settings.cache_clear()

    engine = create_engine(database_url)
    with engine.begin() as conn:
        _ = conn.execute(text("DROP SCHEMA public CASCADE"))
        _ = conn.execute(text("CREATE SCHEMA public"))
    yield engine
    engine.dispose()


def test_existing_passages_become_common(empty_db: Engine) -> None:
    upgrade(INITIAL)
    # Raw SQL: the models describe the newest schema, not this revision's.
    with empty_db.begin() as conn:
        _ = conn.execute(
            text(
                "INSERT INTO passages (slug, title, level, text, glossary) "
                "VALUES ('old', 'نص', 'A2', 'الفقرة.', '{}')"
            )
        )

    upgrade("head")

    with empty_db.begin() as conn:
        assert conn.execute(text("SELECT owner_id, is_common FROM passages")).one() == (
            None,
            True,
        )
        _ = conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, created_at) "
                "VALUES (1, 'peter', 'x', now())"
            )
        )
        _ = conn.execute(
            text(
                "INSERT INTO passages (title, level, text, glossary, owner_id) "
                "VALUES ('new', 'A2', 'الفقرة.', '{}', 1)"
            )
        )
        new_is_common = conn.scalar(
            text("SELECT is_common FROM passages WHERE title = 'new'")
        )
    assert new_is_common is False


def test_migrations_create_every_check_and_partial_index(empty_db: Engine) -> None:
    upgrade("head")
    inspector = inspect(empty_db)

    expected: dict[str, set[str | None]] = {}
    actual: dict[str, set[str | None]] = {}
    for table in Base.metadata.sorted_tables:
        expected[table.name] = {
            c.name for c in table.constraints if isinstance(c, CheckConstraint)
        } | {
            i.name
            for i in table.indexes
            if i.dialect_options["postgresql"]["where"] is not None
        }
        actual[table.name] = {
            c["name"] for c in inspector.get_check_constraints(table.name)
        } | {
            i["name"]
            for i in inspector.get_indexes(table.name)
            if i.get("dialect_options", {}).get("postgresql_where")
        }

    assert actual == expected
