"""add refund execution and reconciliation

Revision ID: d2f6a8c1e4b9
Revises: c1a7e9d4f2b8
"""

from alembic import op
import sqlalchemy as sa


revision = "d2f6a8c1e4b9"
down_revision = "c1a7e9d4f2b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("cancellations", "cancellation_type", existing_type=sa.String(length=12), type_=sa.String(length=22), existing_nullable=False)
    op.alter_column("refunds", "status", existing_type=sa.String(length=13), type_=sa.String(length=23), existing_nullable=False)
    op.add_column("refunds", sa.Column("provider", sa.String(length=40), server_default="VAYORA_GATEWAY", nullable=False))
    op.add_column("refunds", sa.Column("idempotency_key", sa.String(length=100), nullable=True))
    op.add_column("refunds", sa.Column("provider_status", sa.String(length=40), nullable=True))
    op.add_column("refunds", sa.Column("reconciliation_reason", sa.Text(), nullable=True))
    op.add_column("refunds", sa.Column("execution_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("refunds", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refunds", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refunds", sa.Column("provider_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refunds", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE refunds SET idempotency_key = CONCAT('legacy-refund-', id) WHERE idempotency_key IS NULL")
    op.alter_column("refunds", "idempotency_key", existing_type=sa.String(length=100), nullable=False)
    op.create_unique_constraint("uq_refunds_provider_idempotency", "refunds", ["provider", "idempotency_key"])
    op.create_index("ix_refunds_next_retry_at", "refunds", ["next_retry_at"])
    op.add_column("payment_webhook_events", sa.Column("refund_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_payment_webhook_events_refund_id", "payment_webhook_events", "refunds", ["refund_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_payment_webhook_events_refund_id", "payment_webhook_events", ["refund_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_webhook_events_refund_id", table_name="payment_webhook_events")
    op.drop_constraint("fk_payment_webhook_events_refund_id", "payment_webhook_events", type_="foreignkey")
    op.drop_column("payment_webhook_events", "refund_id")
    op.drop_index("ix_refunds_next_retry_at", table_name="refunds")
    op.drop_constraint("uq_refunds_provider_idempotency", "refunds", type_="unique")
    for column in ("completed_at", "provider_accepted_at", "last_checked_at", "next_retry_at", "execution_attempts", "reconciliation_reason", "provider_status", "idempotency_key", "provider"):
        op.drop_column("refunds", column)
    op.alter_column("refunds", "status", existing_type=sa.String(length=23), type_=sa.String(length=13), existing_nullable=False)
    op.alter_column("cancellations", "cancellation_type", existing_type=sa.String(length=22), type_=sa.String(length=12), existing_nullable=False)
