"""drop passage glossary

Revision ID: 6d5095db3a6d
Revises: d9a273a744e5
Create Date: 2026-10-25 20:02:33.641720

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d5095db3a6d"
down_revision: str | Sequence[str] | None = "d9a273a744e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("passages", "glossary")


def downgrade() -> None:
    op.add_column(
        "passages",
        sa.Column(
            "glossary", sa.JSON(), server_default=sa.text("'{}'"), nullable=False
        ),
    )
    op.alter_column("passages", "glossary", server_default=None)
