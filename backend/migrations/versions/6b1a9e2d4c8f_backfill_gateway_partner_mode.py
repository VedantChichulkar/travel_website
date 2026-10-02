"""preserve existing hotel gateway modes during partner-mode rollout

Revision ID: 6b1a9e2d4c8f
Revises: 4e3a1c9f2b7d
"""

from alembic import op


revision = "6b1a9e2d4c8f"
down_revision = "4e3a1c9f2b7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 4e3 introduced the partner preference with PAUSED as a safe default.
    # Existing hotels already had an explicit gateway setting, so preserve it.
    op.execute("UPDATE hotels SET partner_booking_gateway_status = booking_gateway_status")


def downgrade() -> None:
    pass
