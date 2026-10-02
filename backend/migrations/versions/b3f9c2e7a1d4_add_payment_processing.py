"""add payment attempts and webhook deduplication

Revision ID: b3f9c2e7a1d4
Revises: 8a2d5f1c7e9b
"""

from alembic import op
import sqlalchemy as sa


revision = "b3f9c2e7a1d4"
down_revision = "8a2d5f1c7e9b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    reconciliation = sa.Enum("NOT_REQUIRED", "CONFIRMATION_REQUIRED", "RESOLVED", name="payment_reconciliation_status", native_enum=False)
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_order_id", sa.String(length=100), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum("NOT_STARTED", "PENDING", "PAID", "FAILED", "REFUND_PENDING", "REFUNDED", name="payment_status"), nullable=False, server_default="PENDING"),
        sa.Column("reconciliation_status", reconciliation, nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipt_status", sa.String(length=30), nullable=False, server_default="NOT_REQUESTED"),
        sa.Column("receipt_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount"),
        sa.UniqueConstraint("provider", "provider_order_id", name="uq_payments_provider_order"),
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_payments_provider_payment"),
    )
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_reconciliation_status", "payments", ["reconciliation_status"])
    op.create_index("ix_payments_booking_created", "payments", ["booking_id", "created_at"])
    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_event_id", sa.String(length=100), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_payment_webhook_provider_event"),
    )
    op.create_index("ix_payment_webhook_events_payment_id", "payment_webhook_events", ["payment_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_payment_id", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
    op.drop_index("ix_payments_booking_created", table_name="payments")
    op.drop_index("ix_payments_reconciliation_status", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_booking_id", table_name="payments")
    op.drop_table("payments")
