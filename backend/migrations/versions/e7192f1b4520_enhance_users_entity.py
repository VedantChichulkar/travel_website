"""enhance users entity with status verification flags and last login

Revision ID: e7192f1b4520
Revises: 13b4e7871d27
Create Date: 2026-08-28 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7192f1b4520'
down_revision: Union[str, Sequence[str], None] = '13b4e7871d27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add platform user fields."""
    op.add_column(
        'users',
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('is_email_verified', sa.Boolean(), server_default='0', nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('is_phone_verified', sa.Boolean(), server_default='0', nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'is_phone_verified')
    op.drop_column('users', 'is_email_verified')
    op.drop_column('users', 'status')
