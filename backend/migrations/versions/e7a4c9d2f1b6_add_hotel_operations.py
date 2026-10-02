"""add hotel operations booking states

Revision ID: e7a4c9d2f1b6
Revises: d4e8f1a2c6b9
"""

from alembic import op
import sqlalchemy as sa

revision = "e7a4c9d2f1b6"
down_revision = "d4e8f1a2c6b9"
branch_labels = None
depends_on = None

_old = sa.Enum("PENDING", "PAYMENT_PENDING", "CONFIRMED", "FAILED", "CANCELLATION_REQUESTED", "CANCELLED", "REFUND_PENDING", "REFUNDED", name="booking_status")
_new = sa.Enum("PENDING", "PAYMENT_PENDING", "CONFIRMED", "FAILED", "CANCELLATION_REQUESTED", "CANCELLED", "REFUND_PENDING", "REFUNDED", "CHECK_IN_ISSUE", "CHECKED_IN", "CHECKED_OUT", "NO_SHOW", name="booking_status")


def upgrade() -> None:
    op.alter_column("bookings", "status", existing_type=_old, type_=_new, existing_nullable=False)
    op.alter_column("booking_status_history", "old_status", existing_type=_old, type_=_new, existing_nullable=True)
    op.alter_column("booking_status_history", "new_status", existing_type=_old, type_=_new, existing_nullable=False)
    op.add_column("bookings", sa.Column("operation_qr_token", sa.String(length=64), nullable=True))
    op.add_column("bookings", sa.Column("assigned_room", sa.String(length=80), nullable=True))
    op.add_column("bookings", sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_bookings_operation_qr_token", "bookings", ["operation_qr_token"], unique=True)
    op.create_index("ix_bookings_checked_in_at", "bookings", ["checked_in_at"])
    op.create_index("ix_bookings_checked_out_at", "bookings", ["checked_out_at"])


def downgrade() -> None:
    op.drop_index("ix_bookings_checked_out_at", table_name="bookings"); op.drop_index("ix_bookings_checked_in_at", table_name="bookings"); op.drop_index("ix_bookings_operation_qr_token", table_name="bookings")
    op.drop_column("bookings", "checked_out_at"); op.drop_column("bookings", "checked_in_at"); op.drop_column("bookings", "assigned_room"); op.drop_column("bookings", "operation_qr_token")
    op.alter_column("booking_status_history", "new_status", existing_type=_new, type_=_old, existing_nullable=False)
    op.alter_column("booking_status_history", "old_status", existing_type=_new, type_=_old, existing_nullable=True)
    op.alter_column("bookings", "status", existing_type=_new, type_=_old, existing_nullable=False)
