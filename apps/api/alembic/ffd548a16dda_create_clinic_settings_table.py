"""create clinic_settings table

Revision ID: ffd548a16dda
Revises: 978c196a0f9f
Create Date: 2026-10-13 21:37:34.897133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ffd548a16dda'
down_revision: Union[str, Sequence[str], None] = '978c196a0f9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('clinic_settings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('clinic_id', sa.UUID(), nullable=False),
    sa.Column('currency', sa.String(length=3), server_default='PKR', nullable=False),
    sa.Column('timezone', sa.String(length=50), server_default='Asia/Karachi', nullable=False),
    sa.Column('working_hours', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('default_slot_min', sa.Integer(), server_default='30', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('clinic_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('clinic_settings')