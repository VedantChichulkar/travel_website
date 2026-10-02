"""complete booking-on-request lifecycle

Revision ID: b6e1d3f8a2c4
Revises: a4c8e2f6b1d9
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b6e1d3f8a2c4"
down_revision: str | None = "a4c8e2f6b1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_BOOKING_STATUS = sa.Enum(
    "PENDING", "PAYMENT_PENDING", "CONFIRMED", "FAILED", "CANCELLATION_REQUESTED",
    "CANCELLED", "REFUND_PENDING", "REFUNDED", "CHECK_IN_ISSUE", "CHECKED_IN",
    "CHECKED_OUT", "NO_SHOW", name="booking_status",
)
NEW_BOOKING_STATUS = sa.Enum(
    "PENDING", "PAYMENT_PENDING", "CONFIRMED", "FAILED", "CANCELLATION_REQUESTED",
    "CANCELLED", "REFUND_PENDING", "REFUNDED", "CHECK_IN_ISSUE", "CHECKED_IN",
    "CHECKED_OUT", "NO_SHOW", "REQUEST_REJECTED", "REQUEST_EXPIRED", name="booking_status",
)


def upgrade() -> None:
    op.add_column("bookings", sa.Column("booking_mode", sa.String(length=18), server_default="ACTIVE", nullable=False))
    op.add_column("bookings", sa.Column("request_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("request_decided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("request_decision_reason", sa.Text(), nullable=True))
    op.add_column("bookings", sa.Column("payment_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE bookings SET booking_mode = 'BOOKING_ON_REQUEST' WHERE status = 'PENDING'")
    op.create_index("ix_bookings_request_expires_at", "bookings", ["request_expires_at"])
    op.create_index("ix_bookings_payment_expires_at", "bookings", ["payment_expires_at"])
    op.create_index("ix_bookings_request_queue", "bookings", ["booking_mode", "status", "request_expires_at"])
    op.alter_column("bookings", "status", existing_type=OLD_BOOKING_STATUS, type_=NEW_BOOKING_STATUS, existing_nullable=False, existing_server_default="PAYMENT_PENDING")
    op.alter_column("booking_status_history", "old_status", existing_type=OLD_BOOKING_STATUS, type_=NEW_BOOKING_STATUS, existing_nullable=True)
    op.alter_column("booking_status_history", "new_status", existing_type=OLD_BOOKING_STATUS, type_=NEW_BOOKING_STATUS, existing_nullable=False)


def downgrade() -> None:
    op.execute("UPDATE booking_status_history SET old_status = 'FAILED' WHERE old_status = 'REQUEST_EXPIRED'")
    op.execute("UPDATE booking_status_history SET new_status = 'FAILED' WHERE new_status = 'REQUEST_EXPIRED'")
    op.execute("UPDATE booking_status_history SET old_status = 'CANCELLED' WHERE old_status = 'REQUEST_REJECTED'")
    op.execute("UPDATE booking_status_history SET new_status = 'CANCELLED' WHERE new_status = 'REQUEST_REJECTED'")
    op.execute("UPDATE bookings SET status = 'FAILED' WHERE status = 'REQUEST_EXPIRED'")
    op.execute("UPDATE bookings SET status = 'CANCELLED' WHERE status = 'REQUEST_REJECTED'")
    op.alter_column("booking_status_history", "new_status", existing_type=NEW_BOOKING_STATUS, type_=OLD_BOOKING_STATUS, existing_nullable=False)
    op.alter_column("booking_status_history", "old_status", existing_type=NEW_BOOKING_STATUS, type_=OLD_BOOKING_STATUS, existing_nullable=True)
    op.alter_column("bookings", "status", existing_type=NEW_BOOKING_STATUS, type_=OLD_BOOKING_STATUS, existing_nullable=False, existing_server_default="PAYMENT_PENDING")
    op.drop_index("ix_bookings_request_queue", table_name="bookings")
    op.drop_index("ix_bookings_payment_expires_at", table_name="bookings")
    op.drop_index("ix_bookings_request_expires_at", table_name="bookings")
    op.drop_column("bookings", "payment_expires_at")
    op.drop_column("bookings", "request_decision_reason")
    op.drop_column("bookings", "request_decided_at")
    op.drop_column("bookings", "request_expires_at")
    op.drop_column("bookings", "booking_mode")
