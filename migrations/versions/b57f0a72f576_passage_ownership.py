"""passage ownership

Revision ID: b57f0a72f576
Revises: 6ad753184ecc
Create Date: 2026-10-12 17:18:46.374165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b57f0a72f576'
down_revision: Union[str, Sequence[str], None] = '6ad753184ecc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default=sa.false(), nullable=False))

    # Existing passages have no owner, so they become common: the column is added with
    # default true (Postgres fills existing rows without rewriting the table), then new
    # rows default to false.
    op.add_column('passages', sa.Column('is_common', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.alter_column('passages', 'is_common', server_default=sa.false())

    op.add_column('passages', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(op.f('fk_passages_owner_id_users'), 'passages', 'users', ['owner_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_passages_owner_id'), 'passages', ['owner_id'], unique=False)
    # Autogenerate doesn't detect CHECK constraints.
    op.create_check_constraint(op.f('ck_passages_common_or_owned'), 'passages', 'is_common OR owner_id IS NOT NULL')

    op.alter_column('passages', 'title', existing_type=sa.VARCHAR(length=200), nullable=True)
    op.alter_column('passages', 'slug', existing_type=sa.VARCHAR(length=80), nullable=True)
    op.drop_index(op.f('ix_passages_slug'), table_name='passages')
    op.create_index('uq_passages_slug_common', 'passages', ['slug'], unique=True, postgresql_where=sa.text('is_common'))


def downgrade() -> None:
    """Downgrade schema.

    Fails while a passage has no title or slug, or two private passages share a slug.
    That data only exists after this revision, and dropping it silently would be worse.
    """
    op.drop_index('uq_passages_slug_common', table_name='passages', postgresql_where=sa.text('is_common'))
    op.create_index(op.f('ix_passages_slug'), 'passages', ['slug'], unique=True)
    op.alter_column('passages', 'slug', existing_type=sa.VARCHAR(length=80), nullable=False)
    op.alter_column('passages', 'title', existing_type=sa.VARCHAR(length=200), nullable=False)

    op.drop_constraint(op.f('ck_passages_common_or_owned'), 'passages', type_='check')
    op.drop_index(op.f('ix_passages_owner_id'), table_name='passages')
    op.drop_constraint(op.f('fk_passages_owner_id_users'), 'passages', type_='foreignkey')
    op.drop_column('passages', 'owner_id')
    op.drop_column('passages', 'is_common')

    op.drop_column('users', 'is_admin')
