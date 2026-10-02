"""enhance hotels entity with district and booking gateway status

Revision ID: c8230da46721
Revises: e7192f1b4520
Create Date: 2026-08-28 00:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8230da46721'
down_revision: Union[str, Sequence[str], None] = 'e7192f1b4520'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add district and booking gateway status to hotels."""
    op.add_column(
        'hotels',
        sa.Column('district', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'hotels',
        sa.Column('booking_gateway_status', sa.String(length=20), server_default='ACTIVE', nullable=False),
    )
    op.create_index(op.f('ix_hotels_district'), 'hotels', ['district'], unique=False)
    op.create_index(
        'ix_hotels_booking_gateway',
        'hotels',
        ['status', 'booking_gateway_status'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_hotels_booking_gateway', table_name='hotels')
    op.drop_index(op.f('ix_hotels_district'), table_name='hotels')
    op.drop_column('hotels', 'booking_gateway_status')
    op.drop_column('hotels', 'district')
