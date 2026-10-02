"""add cancellation and refund financial records

Revision ID: d4e8f1a2c6b9
Revises: b3f9c2e7a1d4
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e8f1a2c6b9"
down_revision = "b3f9c2e7a1d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cancellations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("cancellation_type", sa.Enum("CUSTOMER", "HOTEL_CAUSED", name="cancellation_type", native_enum=False), nullable=False),
        sa.Column("status", sa.Enum("REQUESTED", "REFUND_PENDING", "MANUAL_REVIEW", "COMPLETED", "REJECTED", name="cancellation_status", native_enum=False), nullable=False, server_default="REQUESTED"),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("refundable_amount", sa.Numeric(12, 2), nullable=False), sa.Column("refunded_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("decided_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cancellations_booking_id", "cancellations", ["booking_id"])
    op.create_index("ix_cancellations_status", "cancellations", ["status"])
    op.create_index("ix_cancellations_decided_by_user_id", "cancellations", ["decided_by_user_id"])
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cancellation_id", sa.Integer(), sa.ForeignKey("cancellations.id", ondelete="CASCADE"), nullable=False), sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "SUCCEEDED", "FAILED", "PARTIAL", "MANUAL_REVIEW", name="refund_status", native_enum=False), nullable=False, server_default="PENDING"),
        sa.Column("provider_refund_id", sa.String(length=100), nullable=True, unique=True), sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("settlement_impact_status", sa.Enum("PENDING", "RECORDED", "NOT_APPLICABLE", name="settlement_impact_status", native_enum=False), nullable=False, server_default="PENDING"),
        sa.Column("executed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount >= 0", name="ck_refunds_amount"),
    )
    op.create_index("ix_refunds_cancellation_id", "refunds", ["cancellation_id"]); op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"]); op.create_index("ix_refunds_status", "refunds", ["status"]); op.create_index("ix_refunds_executed_by_user_id", "refunds", ["executed_by_user_id"]); op.create_index("ix_refunds_cancellation_status", "refunds", ["cancellation_id", "status"])


def downgrade() -> None:
    op.drop_table("refunds")
    op.drop_table("cancellations")
