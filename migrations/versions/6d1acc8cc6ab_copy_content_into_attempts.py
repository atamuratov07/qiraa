"""copy content into attempts

Gives every existing attempt a copy of its passage, with each question's options in the
order the attempt showed them.

Revision ID: 6d1acc8cc6ab
Revises: 5c3b0f29a687
Create Date: 2026-10-20 01:58:01.704442

"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d1acc8cc6ab"
down_revision: Union[str, Sequence[str], None] = "5c3b0f29a687"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The tables as they are at this revision. The app's models describe the newest schema,
# so a migration never imports them.
attempts = sa.table(
    "attempts",
    sa.column("id", sa.Integer),
    sa.column("passage_id", sa.Integer),
    sa.column("option_order", sa.JSON),
    sa.column("content", sa.JSON),
)
passages = sa.table(
    "passages",
    sa.column("id", sa.Integer),
    sa.column("title", sa.String),
    sa.column("level", sa.String),
    sa.column("text", sa.Text),
    sa.column("translation_ru", sa.Text),
)
questions = sa.table(
    "questions",
    sa.column("id", sa.Integer),
    sa.column("passage_id", sa.Integer),
    sa.column("position", sa.Integer),
    sa.column("prompt", sa.Text),
    sa.column("explanation", sa.Text),
)
options = sa.table(
    "options",
    sa.column("id", sa.Integer),
    sa.column("question_id", sa.Integer),
    sa.column("position", sa.Integer),
    sa.column("text", sa.Text),
    sa.column("is_correct", sa.Boolean),
)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(attempts.c.id, attempts.c.passage_id, attempts.c.option_order).where(
            attempts.c.content.is_(None)
        )
    ).all()

    loaded: dict[int, dict[str, Any]] = {}
    for attempt_id, passage_id, option_order in rows:
        if passage_id not in loaded:
            loaded[passage_id] = load_passage(conn, passage_id)
        conn.execute(
            attempts.update()
            .where(attempts.c.id == attempt_id)
            .values(content=in_saved_order(loaded[passage_id], option_order))
        )


def downgrade() -> None:
    # sa.null() is SQL NULL; None would store the JSON value null.
    op.execute(attempts.update().values(content=sa.null()))


def load_passage(conn: sa.Connection, passage_id: int) -> dict[str, Any]:
    """The passage as a copy, with every question's options by position."""
    passage = conn.execute(sa.select(passages).where(passages.c.id == passage_id)).one()
    question_rows = conn.execute(
        sa.select(questions)
        .where(questions.c.passage_id == passage_id)
        .order_by(questions.c.position)
    ).all()
    option_rows = conn.execute(
        sa.select(options)
        .where(options.c.question_id.in_([q.id for q in question_rows]))
        .order_by(options.c.position)
    ).all()

    return {
        "title": passage.title,
        "level": passage.level,
        "text": passage.text,
        "translation_ru": passage.translation_ru,
        "questions": [
            {
                "id": q.id,
                "prompt": q.prompt,
                "explanation": q.explanation,
                "options": [
                    {"id": o.id, "text": o.text, "is_correct": o.is_correct}
                    for o in option_rows
                    if o.question_id == q.id
                ],
            }
            for q in question_rows
        ],
    }


def in_saved_order(
    passage: dict[str, Any], option_order: dict[str, list[int]]
) -> dict[str, Any]:
    """Options in the order the attempt showed them; ones added since then go last."""
    copied: list[dict[str, Any]] = []
    for q in passage["questions"]:
        saved = option_order.get(str(q["id"]), [])
        rank = {option_id: i for i, option_id in enumerate(saved)}
        ordered = sorted(q["options"], key=lambda o: rank.get(o["id"], len(saved)))
        copied.append({**q, "options": ordered})

    return {**passage, "questions": copied}
