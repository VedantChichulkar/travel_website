"""add verification fee payment and refund links

Revision ID: c4f1a8b7d2e6
Revises: b8d2f4a6c9e1
"""

from alembic import op
import sqlalchemy as sa


revision = "c4f1a8b7d2e6"
down_revision = "b8d2f4a6c9e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("verification_hotel_id", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("purpose", sa.Enum("BOOKING", "VERIFICATION_FEE", name="payment_purpose", native_enum=False), nullable=False, server_default="BOOKING"))
    op.alter_column("payments", "booking_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key("fk_payments_verification_hotel_id", "payments", "hotels", ["verification_hotel_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_payments_verification_hotel_id", "payments", ["verification_hotel_id"])
    op.create_index("ix_payments_purpose", "payments", ["purpose"])
    op.create_index("ix_payments_verification_hotel_created", "payments", ["verification_hotel_id", "created_at"])
    op.create_check_constraint("ck_payments_single_subject", "payments", "(booking_id IS NOT NULL AND verification_hotel_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NOT NULL)")

    op.add_column("refunds", sa.Column("verification_id", sa.Integer(), nullable=True))
    op.alter_column("refunds", "cancellation_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key("fk_refunds_verification_id", "refunds", "hotel_verifications", ["verification_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_refunds_verification_id", "refunds", ["verification_id"])
    op.create_index("ix_refunds_verification_status", "refunds", ["verification_id", "status"])
    op.create_check_constraint("ck_refunds_single_reason", "refunds", "(cancellation_id IS NOT NULL AND verification_id IS NULL) OR (cancellation_id IS NULL AND verification_id IS NOT NULL)")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    refund_checks = {item["name"] for item in inspector.get_check_constraints("refunds")}
    refund_indexes = {item["name"] for item in inspector.get_indexes("refunds")}
    refund_fks = {item["name"] for item in inspector.get_foreign_keys("refunds")}
    if "ck_refunds_single_reason" in refund_checks:
        op.drop_constraint("ck_refunds_single_reason", "refunds", type_="check")
    if "ix_refunds_verification_status" in refund_indexes:
        op.drop_index("ix_refunds_verification_status", table_name="refunds")
    if "fk_refunds_verification_id" in refund_fks:
        op.drop_constraint("fk_refunds_verification_id", "refunds", type_="foreignkey")
    if "ix_refunds_verification_id" in refund_indexes:
        op.drop_index("ix_refunds_verification_id", table_name="refunds")
    op.drop_column("refunds", "verification_id")
    op.alter_column("refunds", "cancellation_id", existing_type=sa.Integer(), nullable=False)

    inspector = sa.inspect(bind)
    payment_checks = {item["name"] for item in inspector.get_check_constraints("payments")}
    payment_indexes = {item["name"] for item in inspector.get_indexes("payments")}
    payment_fks = {item["name"] for item in inspector.get_foreign_keys("payments")}
    if "ck_payments_single_subject" in payment_checks:
        op.drop_constraint("ck_payments_single_subject", "payments", type_="check")
    if "ix_payments_verification_hotel_created" in payment_indexes:
        op.drop_index("ix_payments_verification_hotel_created", table_name="payments")
    if "ix_payments_purpose" in payment_indexes:
        op.drop_index("ix_payments_purpose", table_name="payments")
    if "fk_payments_verification_hotel_id" in payment_fks:
        op.drop_constraint("fk_payments_verification_hotel_id", "payments", type_="foreignkey")
    if "ix_payments_verification_hotel_id" in payment_indexes:
        op.drop_index("ix_payments_verification_hotel_id", table_name="payments")
    op.drop_column("payments", "purpose")
    op.drop_column("payments", "verification_hotel_id")
    op.alter_column("payments", "booking_id", existing_type=sa.Integer(), nullable=False)
