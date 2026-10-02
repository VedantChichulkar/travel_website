"""link bookings to consumed holds and preserve booking snapshots

Revision ID: 8a2d5f1c7e9b
Revises: 6b1a9e2d4c8f
"""

from alembic import op
import sqlalchemy as sa

revision = "8a2d5f1c7e9b"
down_revision = "6b1a9e2d4c8f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("hold_token", sa.String(length=64), nullable=True))
    op.add_column("bookings", sa.Column("room_snapshot", sa.JSON(), nullable=False, server_default=sa.text("(JSON_OBJECT())")))
    op.add_column("bookings", sa.Column("price_snapshot", sa.JSON(), nullable=False, server_default=sa.text("(JSON_OBJECT())")))
    op.add_column("bookings", sa.Column("policy_snapshot", sa.JSON(), nullable=False, server_default=sa.text("(JSON_OBJECT())")))
    op.create_index("ix_bookings_hold_token", "bookings", ["hold_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_bookings_hold_token", table_name="bookings")
    op.drop_column("bookings", "policy_snapshot")
    op.drop_column("bookings", "price_snapshot")
    op.drop_column("bookings", "room_snapshot")
    op.drop_column("bookings", "hold_token")
