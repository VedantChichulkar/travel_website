"""complete settlement commission and payout lifecycle

Revision ID: e3a7c9d1f5b2
Revises: d2f6a8c1e4b9
"""

from alembic import op
import sqlalchemy as sa


revision = "e3a7c9d1f5b2"
down_revision = "d2f6a8c1e4b9"
branch_labels = None
depends_on = None


payout_status = sa.Enum(
    "PENDING", "PROCESSING", "SUCCESS", "FAILED", "RECONCILIATION_REQUIRED",
    name="payout_status", native_enum=False,
)


def upgrade() -> None:
    op.add_column("settlements", sa.Column("commission_rate", sa.Numeric(7, 6), nullable=True))
    op.add_column("settlements", sa.Column("commission_rule", sa.String(length=120), nullable=True))
    op.add_column("settlement_adjustments", sa.Column("applied_to_settlement_id", sa.Integer(), nullable=True))
    op.add_column("settlement_adjustments", sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_settlement_adjustments_applied_to", "settlement_adjustments", "settlements",
        ["applied_to_settlement_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_settlement_adjustments_applied_to_settlement_id", "settlement_adjustments", ["applied_to_settlement_id"])

    op.create_table(
        "payouts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("beneficiary_reference", sa.String(length=120), nullable=False),
        sa.Column("provider_payout_id", sa.String(length=120), nullable=True),
        sa.Column("provider_status", sa.String(length=40), nullable=True),
        sa.Column("status", payout_status, server_default="PENDING", nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("reconciliation_reason", sa.Text(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_payouts_amount"),
        sa.ForeignKeyConstraint(["settlement_id"], ["settlements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settlement_id", name="uq_payouts_settlement"),
        sa.UniqueConstraint("idempotency_key", name="uq_payouts_idempotency"),
        sa.UniqueConstraint("provider_payout_id", name="uq_payouts_provider_reference"),
    )
    op.create_index("ix_payouts_settlement_id", "payouts", ["settlement_id"], unique=True)
    op.create_index("ix_payouts_status", "payouts", ["status"])
    op.create_index("ix_payouts_next_retry_at", "payouts", ["next_retry_at"])
    op.create_index("ix_payouts_status_retry", "payouts", ["status", "next_retry_at"])

    op.create_table(
        "payout_webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_event_id", sa.String(length=120), nullable=False),
        sa.Column("payout_id", sa.Integer(), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payout_id"], ["payouts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_payout_webhook_provider_event"),
    )
    op.create_index("ix_payout_webhook_events_payout_id", "payout_webhook_events", ["payout_id"])


def downgrade() -> None:
    op.drop_table("payout_webhook_events")
    op.drop_table("payouts")
    op.drop_index("ix_settlement_adjustments_applied_to_settlement_id", table_name="settlement_adjustments")
    op.drop_constraint("fk_settlement_adjustments_applied_to", "settlement_adjustments", type_="foreignkey")
    op.drop_column("settlement_adjustments", "applied_at")
    op.drop_column("settlement_adjustments", "applied_to_settlement_id")
    op.drop_column("settlements", "commission_rule")
    op.drop_column("settlements", "commission_rate")
