"""add last_login_at and make users.is_active not null

Revision ID: 978c196a0f9f
Revises: cffeb70aff2a
Create Date: 2026-10-09 23:54:53.756390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '978c196a0f9f'
down_revision: Union[str, Sequence[str], None] = 'cffeb70aff2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

    # is_active was created nullable. Treat any NULL as active (the model default), then forbid NULL.
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.alter_column('users', 'is_active',
                    existing_type=sa.BOOLEAN(),
                    nullable=False,
                    server_default=sa.true())


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'is_active',
                    existing_type=sa.BOOLEAN(),
                    nullable=True,
                    server_default=None)
    op.drop_column('users', 'last_login_at')