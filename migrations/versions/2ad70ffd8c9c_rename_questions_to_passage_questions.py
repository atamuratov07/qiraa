"""rename questions to passage questions

Written by hand: autogenerate reads a renamed table as drop + create. A renamed table
keeps the names of its constraints, indexes and sequences, so they are renamed to what
the naming convention gives for the new table names.

Revision ID: 2ad70ffd8c9c
Revises: 2e18692e8f3e
Create Date: 2026-10-23 08:17:24.235251

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ad70ffd8c9c"
down_revision: Union[str, Sequence[str], None] = "2e18692e8f3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [("questions", "passage_questions"), ("options", "passage_options")]

# (new table name, old name, new name)
CONSTRAINTS = [
    ("passage_questions", "pk_questions", "pk_passage_questions"),
    (
        "passage_questions",
        "uq_questions_passage_id_position",
        "uq_passage_questions_passage_id_position",
    ),
    (
        "passage_questions",
        "fk_questions_passage_id_passages",
        "fk_passage_questions_passage_id_passages",
    ),
    ("passage_options", "pk_options", "pk_passage_options"),
    (
        "passage_options",
        "uq_options_question_id_position",
        "uq_passage_options_question_id_position",
    ),
    (
        "passage_options",
        "fk_options_question_id_questions",
        "fk_passage_options_question_id_passage_questions",
    ),
]

INDEXES = [("uq_options_one_correct", "uq_passage_options_one_correct")]

SEQUENCES = [
    ("questions_id_seq", "passage_questions_id_seq"),
    ("options_id_seq", "passage_options_id_seq"),
]


def upgrade() -> None:
    for old, new in TABLES:
        op.rename_table(old, new)
    for table, old, new in CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}")
    for old, new in INDEXES:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")
    for old, new in SEQUENCES:
        op.execute(f"ALTER SEQUENCE {old} RENAME TO {new}")


def downgrade() -> None:
    for old, new in SEQUENCES:
        op.execute(f"ALTER SEQUENCE {new} RENAME TO {old}")
    for old, new in INDEXES:
        op.execute(f"ALTER INDEX {new} RENAME TO {old}")
    for table, old, new in CONSTRAINTS:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {new} TO {old}")
    for old, new in TABLES:
        op.rename_table(new, old)
