"""add paid booking reconciliation workflow

Revision ID: c1a7e9d4f2b8
Revises: b6e1d3f8a2c4
"""

from alembic import op
import sqlalchemy as sa


revision = "c1a7e9d4f2b8"
down_revision = "b6e1d3f8a2c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("reconciliation_attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("payments", sa.Column("reconciliation_next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("reconciliation_last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("reconciliation_resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("reconciliation_resolved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("payments", sa.Column("reconciliation_reason", sa.Text(), nullable=True))
    op.create_index("ix_payments_reconciliation_next_retry_at", "payments", ["reconciliation_next_retry_at"])
    op.create_index("ix_payments_reconciliation_resolved_by", "payments", ["reconciliation_resolved_by"])
    op.alter_column("notifications", "event_type", existing_type=sa.String(length=23), type_=sa.String(length=32), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("notifications", "event_type", existing_type=sa.String(length=32), type_=sa.String(length=23), existing_nullable=False)
    op.drop_index("ix_payments_reconciliation_resolved_by", table_name="payments")
    op.drop_index("ix_payments_reconciliation_next_retry_at", table_name="payments")
    op.drop_column("payments", "reconciliation_reason")
    op.drop_column("payments", "reconciliation_resolved_by")
    op.drop_column("payments", "reconciliation_resolved_at")
    op.drop_column("payments", "reconciliation_last_attempt_at")
    op.drop_column("payments", "reconciliation_next_retry_at")
    op.drop_column("payments", "reconciliation_attempts")
