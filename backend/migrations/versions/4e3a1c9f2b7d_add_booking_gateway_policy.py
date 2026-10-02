"""add booking gateway partner controls and platform override metadata

Revision ID: 4e3a1c9f2b7d
Revises: 7d8e4a0c1b9f
"""

from alembic import op
import sqlalchemy as sa


revision = "4e3a1c9f2b7d"
down_revision = "7d8e4a0c1b9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hotels", sa.Column("partner_booking_gateway_status", sa.String(length=32), server_default="PAUSED", nullable=False))
    op.add_column("hotels", sa.Column("gateway_override_status", sa.String(length=32), nullable=True))
    op.add_column("hotels", sa.Column("gateway_override_reason", sa.Text(), nullable=True))
    op.add_column("hotels", sa.Column("gateway_overridden_by", sa.Integer(), nullable=True))
    op.add_column("hotels", sa.Column("gateway_overridden_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_hotels_gateway_overridden_by", "hotels", "users", ["gateway_overridden_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_hotels_gateway_overridden_by", "hotels", ["gateway_overridden_by"])


def downgrade() -> None:
    op.drop_index("ix_hotels_gateway_overridden_by", table_name="hotels")
    op.drop_constraint("fk_hotels_gateway_overridden_by", "hotels", type_="foreignkey")
    op.drop_column("hotels", "gateway_overridden_at")
    op.drop_column("hotels", "gateway_overridden_by")
    op.drop_column("hotels", "gateway_override_reason")
    op.drop_column("hotels", "gateway_override_status")
    op.drop_column("hotels", "partner_booking_gateway_status")
