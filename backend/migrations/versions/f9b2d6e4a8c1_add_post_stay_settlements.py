"""add post-stay settlement ledger

Revision ID: f9b2d6e4a8c1
Revises: e7a4c9d2f1b6
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f9b2d6e4a8c1"
down_revision: str | None = "e7a4c9d2f1b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


settlement_status = sa.Enum("ON_HOLD", "ELIGIBLE", "PROCESSING", "SETTLED", name="settlement_status", native_enum=False)
adjustment_kind = sa.Enum("ADJUSTMENT", "REVERSAL", name="settlement_adjustment_kind", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "settlements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hotel_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("vayora_fee", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("refund_deductions", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("adjustment_total", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("net_payable", sa.Numeric(12, 2), nullable=False),
        sa.Column("eligibility_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", settlement_status, nullable=False),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("held_by_user_id", sa.Integer(), nullable=True),
        sa.Column("held_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_provider", sa.String(length=40), nullable=True),
        sa.Column("payout_provider_reference", sa.String(length=120), nullable=True),
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("gross_amount >= 0", name="ck_settlements_gross"),
        sa.CheckConstraint("vayora_fee >= 0", name="ck_settlements_fee"),
        sa.CheckConstraint("refund_deductions >= 0", name="ck_settlements_refunds"),
        sa.CheckConstraint("net_payable >= 0", name="ck_settlements_net"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["held_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", name="uq_settlements_booking"),
        sa.UniqueConstraint("payout_provider_reference"),
    )
    op.create_index("ix_settlements_booking_id", "settlements", ["booking_id"], unique=True)
    op.create_index("ix_settlements_hotel_id", "settlements", ["hotel_id"])
    op.create_index("ix_settlements_status", "settlements", ["status"])
    op.create_index("ix_settlements_eligibility_date", "settlements", ["eligibility_date"])
    op.create_index("ix_settlements_held_by_user_id", "settlements", ["held_by_user_id"])
    op.create_index("ix_settlements_hotel_status", "settlements", ["hotel_id", "status"])
    op.create_index("ix_settlements_status_eligibility", "settlements", ["status", "eligibility_date"])

    op.create_table(
        "settlement_adjustments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("kind", adjustment_kind, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("applies_to_current_settlement", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount <> 0", name="ck_settlement_adjustments_nonzero"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["settlement_id"], ["settlements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settlement_adjustments_settlement_id", "settlement_adjustments", ["settlement_id"])
    op.create_index("ix_settlement_adjustments_created_by_user_id", "settlement_adjustments", ["created_by_user_id"])

    op.create_table(
        "settlement_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("old_status", settlement_status, nullable=True),
        sa.Column("new_status", settlement_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_id"], ["settlements.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settlement_events_settlement_id", "settlement_events", ["settlement_id"])
    op.create_index("ix_settlement_events_actor_user_id", "settlement_events", ["actor_user_id"])
    op.create_index("ix_settlement_events_settlement_created", "settlement_events", ["settlement_id", "created_at"])


def downgrade() -> None:
    op.drop_table("settlement_events")
    op.drop_table("settlement_adjustments")
    op.drop_table("settlements")
