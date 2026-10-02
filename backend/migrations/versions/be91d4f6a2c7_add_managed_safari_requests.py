"""add managed safari requests

Revision ID: be91d4f6a2c7
Revises: a7d3c9e1f5b8
"""
from alembic import op
import sqlalchemy as sa

revision = "be91d4f6a2c7"
down_revision = "a7d3c9e1f5b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("safaris",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("district_id", sa.Integer()), sa.Column("destination_id", sa.Integer()), sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("shifts", sa.JSON(), nullable=False), sa.Column("zones", sa.JSON(), nullable=False), sa.Column("gates", sa.JSON(), nullable=False), sa.Column("traveller_requirements", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"), sa.Column("is_public", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="RESTRICT"))
    op.create_index("ix_safaris_slug", "safaris", ["slug"], unique=True)
    for column in ("district_id", "destination_id", "is_active", "is_public"): op.create_index(f"ix_safaris_{column}", "safaris", [column])
    op.create_table("safari_requests",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("request_reference", sa.String(32), nullable=False),
        sa.Column("safari_id", sa.Integer(), nullable=False), sa.Column("customer_id", sa.Integer(), nullable=False), sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("preferred_shift", sa.String(100)), sa.Column("visitor_count", sa.Integer(), nullable=False), sa.Column("alternate_preference", sa.String(500)),
        sa.Column("status", sa.Enum("AVAILABILITY_REQUESTED", "CHECKING_AVAILABILITY", "AWAITING_TRAVELLER_DETAILS", "DETAILS_SUBMITTED", "PAYMENT_PENDING", "BOOKING_IN_PROGRESS", "CONFIRMED", "NOT_AVAILABLE", "EXPIRED", "CANCELLED", "BOOKING_FAILED", name="safari_request_status", native_enum=False, length=40), nullable=False, server_default="AVAILABILITY_REQUESTED"),
        sa.Column("availability_result", sa.String(30)), sa.Column("selected_alternative_id", sa.Integer()), sa.Column("target_response_at", sa.DateTime(timezone=True), nullable=False), sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("payable_amount", sa.Numeric(12, 2)), sa.Column("currency", sa.String(3)), sa.Column("price_breakdown", sa.JSON()), sa.Column("internal_notes", sa.Text()),
        sa.Column("external_booking_reference", sa.String(160)), sa.Column("confirmed_date", sa.Date()), sa.Column("confirmed_shift", sa.String(100)), sa.Column("confirmed_zone", sa.String(160)), sa.Column("confirmed_gate", sa.String(160)),
        sa.Column("reporting_instructions", sa.Text()), sa.Column("final_amount", sa.Numeric(12, 2)), sa.Column("failure_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["safari_id"], ["safaris.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("visitor_count > 0", name="ck_safari_request_visitors"), sa.CheckConstraint("payable_amount IS NULL OR payable_amount >= 0", name="ck_safari_request_amount"))
    op.create_index("ix_safari_requests_request_reference", "safari_requests", ["request_reference"], unique=True)
    for column in ("safari_id", "customer_id", "status", "selected_alternative_id", "target_response_at"): op.create_index(f"ix_safari_requests_{column}", "safari_requests", [column])
    op.create_index("ix_safari_request_queue", "safari_requests", ["status", "target_response_at", "created_at"]); op.create_index("ix_safari_request_customer_created", "safari_requests", ["customer_id", "created_at"])
    op.create_table("safari_alternatives", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("request_id", sa.Integer(), nullable=False), sa.Column("safari_date", sa.Date(), nullable=False), sa.Column("shift", sa.String(100)), sa.Column("zone", sa.String(160)), sa.Column("gate", sa.String(160)), sa.Column("note", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["request_id"], ["safari_requests.id"], ondelete="CASCADE"))
    op.create_index("ix_safari_alternatives_request_id", "safari_alternatives", ["request_id"])
    op.create_foreign_key("fk_safari_requests_selected_alternative", "safari_requests", "safari_alternatives", ["selected_alternative_id"], ["id"], ondelete="SET NULL")
    op.create_table("safari_travellers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("request_id", sa.Integer(), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("details_encrypted", sa.String(12000), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["request_id"], ["safari_requests.id"], ondelete="CASCADE"), sa.UniqueConstraint("request_id", "position", name="uq_safari_traveller_position"))
    op.create_index("ix_safari_travellers_request_id", "safari_travellers", ["request_id"])
    op.create_table("safari_documents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("request_id", sa.Integer(), nullable=False), sa.Column("traveller_id", sa.Integer()), sa.Column("kind", sa.Enum("TRAVELLER", "CONFIRMATION", name="safari_document_kind", native_enum=False), nullable=False), sa.Column("document_type", sa.String(100), nullable=False), sa.Column("storage_key", sa.String(512), nullable=False, unique=True), sa.Column("original_name", sa.String(255), nullable=False), sa.Column("content_type", sa.String(100), nullable=False), sa.Column("size", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["request_id"], ["safari_requests.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["traveller_id"], ["safari_travellers.id"], ondelete="CASCADE"))
    op.create_index("ix_safari_documents_request_id", "safari_documents", ["request_id"]); op.create_index("ix_safari_documents_traveller_id", "safari_documents", ["traveller_id"])
    op.drop_constraint("ck_payments_single_subject", "payments", type_="check")
    op.add_column("payments", sa.Column("safari_request_id", sa.Integer()))
    op.create_foreign_key("fk_payments_safari_request_id", "payments", "safari_requests", ["safari_request_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_payments_safari_request_id", "payments", ["safari_request_id"]); op.create_index("ix_payments_safari_request_created", "payments", ["safari_request_id", "created_at"])
    op.create_check_constraint("ck_payments_single_subject", "payments", "(booking_id IS NOT NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NOT NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NOT NULL AND safari_request_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NOT NULL)")
    op.drop_constraint("ck_refunds_single_reason", "refunds", type_="check")
    op.add_column("refunds", sa.Column("safari_request_id", sa.Integer()))
    op.create_foreign_key("fk_refunds_safari_request_id", "refunds", "safari_requests", ["safari_request_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_refunds_safari_request_id", "refunds", ["safari_request_id"]); op.create_index("ix_refunds_safari_status", "refunds", ["safari_request_id", "status"])
    op.create_check_constraint("ck_refunds_single_reason", "refunds", "(cancellation_id IS NOT NULL AND verification_id IS NULL AND safari_request_id IS NULL) OR (cancellation_id IS NULL AND verification_id IS NOT NULL AND safari_request_id IS NULL) OR (cancellation_id IS NULL AND verification_id IS NULL AND safari_request_id IS NOT NULL)")


def downgrade() -> None:
    op.drop_constraint("ck_refunds_single_reason", "refunds", type_="check"); op.drop_index("ix_refunds_safari_status", table_name="refunds"); op.drop_constraint("fk_refunds_safari_request_id", "refunds", type_="foreignkey"); op.drop_index("ix_refunds_safari_request_id", table_name="refunds"); op.drop_column("refunds", "safari_request_id")
    op.create_check_constraint("ck_refunds_single_reason", "refunds", "(cancellation_id IS NOT NULL AND verification_id IS NULL) OR (cancellation_id IS NULL AND verification_id IS NOT NULL)")
    op.drop_constraint("ck_payments_single_subject", "payments", type_="check"); op.drop_index("ix_payments_safari_request_created", table_name="payments"); op.drop_constraint("fk_payments_safari_request_id", "payments", type_="foreignkey"); op.drop_index("ix_payments_safari_request_id", table_name="payments"); op.drop_column("payments", "safari_request_id")
    op.create_check_constraint("ck_payments_single_subject", "payments", "(booking_id IS NOT NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NOT NULL AND advertising_campaign_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NOT NULL)")
    op.drop_table("safari_documents"); op.drop_table("safari_travellers"); op.drop_constraint("fk_safari_requests_selected_alternative", "safari_requests", type_="foreignkey"); op.drop_table("safari_alternatives"); op.drop_table("safari_requests"); op.drop_table("safaris")
