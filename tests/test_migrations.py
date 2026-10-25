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
from sqlalchemy.exc import IntegrityError

from app.core.config import BASE_DIR, get_settings
from app.models import Base

INITIAL = "6ad753184ecc"


def alembic_config() -> Config:
    config = Config()  # without alembic.ini, env.py leaves pytest's logging alone
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    return config


def upgrade(revision: str) -> None:
    command.upgrade(alembic_config(), revision)


def downgrade(revision: str) -> None:
    command.downgrade(alembic_config(), revision)


@pytest.fixture
def empty_db(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    # env.py migrates whatever the settings point at.
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "")
    get_settings.cache_clear()

    engine = create_engine(database_url)
    reset_schema(engine)
    yield engine
    # A test can end at an old revision, whose table names drop_all() doesn't know.
    reset_schema(engine)
    engine.dispose()


def reset_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


def test_existing_passages_become_common(empty_db: Engine) -> None:
    upgrade(INITIAL)
    # Raw SQL: the models describe the newest schema, not this revision's.
    with empty_db.begin() as conn:
        conn.execute(
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
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, created_at) "
                "VALUES (1, 'peter', 'x', now())"
            )
        )
        conn.execute(
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


def test_existing_attempts_become_passage_attempts(empty_db: Engine) -> None:
    upgrade("2ad70ffd8c9c")
    insert_attempt = text(
        "INSERT INTO attempts (user_id, passage_id, content, started_at, "
        "last_seen_at, elapsed_seconds) VALUES (1, NULL, '{}', now(), now(), 0)"
    )
    with empty_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, created_at) "
                "VALUES (1, 'peter', 'x', now())"
            )
        )
        conn.execute(insert_attempt)

    upgrade("head")

    with empty_db.begin() as conn:
        assert conn.scalar(text("SELECT kind FROM attempts")) == "passage"
    with pytest.raises(IntegrityError), empty_db.begin() as conn:
        conn.execute(
            insert_attempt
        )  # no default any more: a new attempt names its kind


def test_existing_attempts_get_a_copy_of_their_passage(empty_db: Engine) -> None:
    upgrade("350b8310a972")
    with empty_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, created_at) "
                "VALUES (1, 'peter', 'x', now());"
                "INSERT INTO passages (id, title, level, text, glossary, is_common) "
                "VALUES (1, 'نص', 'A2', 'الفقرة.', '{}', true);"
                "INSERT INTO questions (id, passage_id, position, prompt, explanation) "
                "VALUES (1, 1, 1, 'سؤال؟', 'Because.');"
                "INSERT INTO options (id, question_id, position, text, is_correct) "
                "VALUES (11, 1, 1, 'أ', false), (12, 1, 2, 'ب', true), "
                "(13, 1, 3, 'ج', false);"
                "INSERT INTO attempts (id, user_id, passage_id, option_order, "
                "started_at, last_seen_at, elapsed_seconds) "
                """VALUES (1, 1, 1, '{"1": [13, 11]}', now(), now(), 0);"""
                "INSERT INTO attempt_answers (attempt_id, question_id, option_id) "
                "VALUES (1, 1, 13)"
            )
        )

    upgrade("head")

    with empty_db.begin() as conn:
        content = conn.scalar(text("SELECT content FROM attempts"))
        answer = conn.execute(
            text("SELECT question_id, option_id FROM attempt_answers")
        ).one()
    assert content == {
        "title": "نص",
        "level": "A2",
        "text": "الفقرة.",
        "translation_ru": None,
        "questions": [
            {
                "id": 1,
                "prompt": "سؤال؟",
                "explanation": "Because.",
                "options": [  # the saved order, then 12, added after the attempt began
                    {"id": 13, "text": "ج", "is_correct": False},
                    {"id": 11, "text": "أ", "is_correct": False},
                    {"id": 12, "text": "ب", "is_correct": True},
                ],
            }
        ],
    }
    assert tuple(answer) == (1, 13)


def test_downgrading_drops_what_the_old_schema_cannot_hold(empty_db: Engine) -> None:
    upgrade("head")
    copy = (
        '{"title": "نص", "level": "A2", "text": "الفقرة.", "translation_ru": null, '
        '"questions": [{"id": 1, "prompt": "سؤال؟", "explanation": null, "options": '
        '[{"id": 12, "text": "ب", "is_correct": true}, '
        '{"id": 11, "text": "أ", "is_correct": false}]}]}'
    )
    with empty_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, created_at) "
                "VALUES (1, 'peter', 'x', now());"
                "INSERT INTO passages (id, title, level, text, glossary, is_common) "
                "VALUES (1, 'نص', 'A2', 'الفقرة.', '{}', true);"
                "INSERT INTO passage_questions (id, passage_id, position, prompt) "
                "VALUES (1, 1, 1, 'سؤال؟');"
                "INSERT INTO passage_options (id, question_id, position, text, "
                "is_correct) VALUES (11, 1, 1, 'أ', false), (12, 1, 2, 'ب', true)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO attempts (id, user_id, passage_id, kind, content, "
                "started_at, last_seen_at, elapsed_seconds) "
                "VALUES (1, 1, 1, 'passage', :copy, now(), now(), 0), "
                "(2, 1, NULL, 'passage', :copy, now(), now(), 0)"  # passage deleted
            ),
            {"copy": copy},
        )
        conn.execute(
            text(
                "INSERT INTO attempt_answers (attempt_id, question_id, option_id) "
                "VALUES (1, 1, 12), (1, 2, 21), (2, 1, 11)"  # question 2 was deleted
            )
        )

    downgrade("6d1acc8cc6ab")

    with empty_db.begin() as conn:
        kept = conn.execute(text("SELECT id, option_order FROM attempts")).all()
        answers = conn.execute(
            text("SELECT attempt_id, question_id, option_id FROM attempt_answers")
        ).all()
    assert [tuple(row) for row in kept] == [(1, {"1": [12, 11]})]
    assert [tuple(row) for row in answers] == [(1, 1, 12)]
