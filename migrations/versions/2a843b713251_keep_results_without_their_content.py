"""keep results without their content

Attempts read only their copy now. Deleting a passage sets passage_id to NULL, and
answers have no foreign keys to questions or options.

Revision ID: 2a843b713251
Revises: 6d1acc8cc6ab
Create Date: 2026-10-20 19:19:16.707711

"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2a843b713251"
down_revision: Union[str, Sequence[str], None] = "6d1acc8cc6ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

attempts = sa.table(
    "attempts",
    sa.column("id", sa.Integer),
    sa.column("option_order", sa.JSON),
    sa.column("content", sa.JSON),
)


def upgrade() -> None:
    op.drop_index(op.f("ix_attempt_answers_option_id"), table_name="attempt_answers")
    op.drop_index(op.f("ix_attempt_answers_question_id"), table_name="attempt_answers")
    op.drop_constraint(
        op.f("fk_attempt_answers_option_id_options"),
        "attempt_answers",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_attempt_answers_question_id_questions"),
        "attempt_answers",
        type_="foreignkey",
    )
    op.alter_column("attempts", "passage_id", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "attempts",
        "content",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
    )
    op.drop_constraint(
        op.f("fk_attempts_passage_id_passages"), "attempts", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_attempts_passage_id_passages"),
        "attempts",
        "passages",
        ["passage_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("attempts", "option_order")


def downgrade() -> None:
    # Loses data the old schema can't hold: attempts whose passage is gone, and answers
    # whose question or option is gone.
    op.execute("DELETE FROM attempts WHERE passage_id IS NULL")
    op.execute(
        "DELETE FROM attempt_answers a WHERE NOT EXISTS ("
        "SELECT 1 FROM options o WHERE o.id = a.option_id "
        "AND o.question_id = a.question_id)"
    )

    op.add_column(
        "attempts",
        sa.Column("option_order", postgresql.JSON(astext_type=sa.Text())),
    )
    conn = op.get_bind()
    for attempt_id, content in conn.execute(
        sa.select(attempts.c.id, attempts.c.content)
    ).all():
        conn.execute(
            attempts.update()
            .where(attempts.c.id == attempt_id)
            .values(option_order=option_order(content))
        )
    op.alter_column("attempts", "option_order", nullable=False)

    op.drop_constraint(
        op.f("fk_attempts_passage_id_passages"), "attempts", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_attempts_passage_id_passages"),
        "attempts",
        "passages",
        ["passage_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "attempts",
        "content",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )
    op.alter_column(
        "attempts", "passage_id", existing_type=sa.INTEGER(), nullable=False
    )
    op.create_foreign_key(
        op.f("fk_attempt_answers_question_id_questions"),
        "attempt_answers",
        "questions",
        ["question_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_attempt_answers_option_id_options"),
        "attempt_answers",
        "options",
        ["option_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_attempt_answers_question_id"),
        "attempt_answers",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attempt_answers_option_id"),
        "attempt_answers",
        ["option_id"],
        unique=False,
    )


def option_order(content: dict[str, Any]) -> dict[str, list[int]]:
    """The order the copy shows each question's options in, as 1.0 stored it."""
    return {str(q["id"]): [o["id"] for o in q["options"]] for q in content["questions"]}
