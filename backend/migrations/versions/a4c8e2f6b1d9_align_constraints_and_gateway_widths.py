"""align constraints, indexes, and gateway value widths

Revision ID: a4c8e2f6b1d9
Revises: f0a7c4d9e2b5
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a4c8e2f6b1d9"
down_revision: str | None = "f0a7c4d9e2b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_cancellations_booking_id", table_name="cancellations")
    op.alter_column("hotels", "booking_gateway_status", existing_type=sa.String(20), type_=sa.String(18), existing_nullable=False, existing_server_default="ACTIVE")
    op.alter_column("hotels", "partner_booking_gateway_status", existing_type=sa.String(32), type_=sa.String(18), existing_nullable=False, existing_server_default="PAUSED")
    op.alter_column("hotels", "gateway_override_status", existing_type=sa.String(32), type_=sa.String(18), existing_nullable=True)
    op.alter_column("inventory_holds", "status", existing_type=sa.String(16), type_=sa.String(9), existing_nullable=False, existing_server_default="ACTIVE")


def downgrade() -> None:
    op.alter_column("inventory_holds", "status", existing_type=sa.String(9), type_=sa.String(16), existing_nullable=False, existing_server_default="ACTIVE")
    op.alter_column("hotels", "gateway_override_status", existing_type=sa.String(18), type_=sa.String(32), existing_nullable=True)
    op.alter_column("hotels", "partner_booking_gateway_status", existing_type=sa.String(18), type_=sa.String(32), existing_nullable=False, existing_server_default="PAUSED")
    op.alter_column("hotels", "booking_gateway_status", existing_type=sa.String(18), type_=sa.String(20), existing_nullable=False, existing_server_default="ACTIVE")
    op.create_index("ix_cancellations_booking_id", "cancellations", ["booking_id"], unique=False)
