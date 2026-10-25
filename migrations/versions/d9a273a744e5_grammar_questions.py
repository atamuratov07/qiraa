"""grammar questions

Grammar questions get their own tables, and an attempt says whether it is a passage
attempt or a grammar session.

Revision ID: d9a273a744e5
Revises: 2ad70ffd8c9c
Create Date: 2026-10-23 09:09:36.030880

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9a273a744e5"
down_revision: Union[str, Sequence[str], None] = "2ad70ffd8c9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grammar_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("is_common", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.CheckConstraint(
            "is_common OR owner_id IS NOT NULL",
            name=op.f("ck_grammar_questions_common_or_owned"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_grammar_questions_owner_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_questions")),
    )
    op.create_index(
        op.f("ix_grammar_questions_owner_id"), "grammar_questions", ["owner_id"]
    )
    op.create_index(
        "uq_grammar_questions_owner_slug_private",
        "grammar_questions",
        ["owner_id", "slug"],
        unique=True,
        postgresql_where=sa.text("NOT is_common"),
    )
    op.create_index(
        "uq_grammar_questions_slug_common",
        "grammar_questions",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("is_common"),
    )

    op.create_table(
        "grammar_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["grammar_questions.id"],
            name=op.f("fk_grammar_options_question_id_grammar_questions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grammar_options")),
        sa.UniqueConstraint(
            "question_id",
            "position",
            name=op.f("uq_grammar_options_question_id_position"),
        ),
    )
    op.create_index(
        "uq_grammar_options_one_correct",
        "grammar_options",
        ["question_id"],
        unique=True,
        postgresql_where=sa.text("is_correct"),
    )

    # The default fills the existing attempts, which are all passage attempts. Dropping
    # it afterwards makes every new attempt name its kind.
    op.add_column(
        "attempts",
        sa.Column(
            "kind", sa.String(length=16), server_default="passage", nullable=False
        ),
    )
    op.alter_column("attempts", "kind", server_default=None)
    # Autogenerate doesn't detect CHECK constraints added to an existing table.
    op.create_check_constraint(
        op.f("ck_attempts_known_kind"), "attempts", "kind IN ('passage', 'grammar')"
    )
    op.create_check_constraint(
        op.f("ck_attempts_grammar_has_no_passage"),
        "attempts",
        "kind = 'passage' OR passage_id IS NULL",
    )
    op.create_index(
        "uq_attempts_one_open_grammar",
        "attempts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("submitted_at IS NULL AND kind = 'grammar'"),
    )


def downgrade() -> None:
    # Grammar sessions stay: the old schema already holds attempts without a passage,
    # and shows them as results on a deleted passage. Grammar questions are dropped.
    op.drop_index(
        "uq_attempts_one_open_grammar",
        table_name="attempts",
        postgresql_where=sa.text("submitted_at IS NULL AND kind = 'grammar'"),
    )
    op.drop_constraint(
        op.f("ck_attempts_grammar_has_no_passage"), "attempts", type_="check"
    )
    op.drop_constraint(op.f("ck_attempts_known_kind"), "attempts", type_="check")
    op.drop_column("attempts", "kind")

    op.drop_index(
        "uq_grammar_options_one_correct",
        table_name="grammar_options",
        postgresql_where=sa.text("is_correct"),
    )
    op.drop_table("grammar_options")
    op.drop_index(
        "uq_grammar_questions_slug_common",
        table_name="grammar_questions",
        postgresql_where=sa.text("is_common"),
    )
    op.drop_index(
        "uq_grammar_questions_owner_slug_private",
        table_name="grammar_questions",
        postgresql_where=sa.text("NOT is_common"),
    )
    op.drop_index(op.f("ix_grammar_questions_owner_id"), table_name="grammar_questions")
    op.drop_table("grammar_questions")
