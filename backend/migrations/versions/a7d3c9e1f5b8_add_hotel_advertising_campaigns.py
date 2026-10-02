"""add hotel advertising campaigns

Revision ID: a7d3c9e1f5b8
Revises: c4f1a8b7d2e6
"""
from alembic import op
import sqlalchemy as sa

revision = "a7d3c9e1f5b8"
down_revision = "c4f1a8b7d2e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("payments", "purpose", existing_type=sa.String(16), type_=sa.Enum("BOOKING", "VERIFICATION_FEE", "ADVERTISING_CAMPAIGN", name="payment_purpose", native_enum=False, length=32), existing_nullable=False, existing_server_default="BOOKING")
    op.create_table("advertising_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("hotel_id", sa.Integer(), nullable=False),
        sa.Column("placement", sa.Enum("HOMEPAGE_BANNER", "DESTINATION_PROMOTION", name="advertising_placement", native_enum=False), nullable=False),
        sa.Column("plan_code", sa.String(80), nullable=False), sa.Column("district_id", sa.Integer()), sa.Column("destination_id", sa.Integer()),
        sa.Column("creative_url", sa.String(2048)), sa.Column("creative_storage_key", sa.String(512)), sa.Column("creative_content_type", sa.String(100)), sa.Column("creative_size", sa.Integer()), sa.Column("alt_text", sa.String(255)),
        sa.Column("status", sa.Enum("DRAFT", "PAYMENT_PENDING", "PENDING_REVIEW", "NEEDS_CHANGES", "SCHEDULED", "ACTIVE", "EXPIRED", "REJECTED", "PAUSED", "CANCELLED", name="advertising_campaign_status", native_enum=False), nullable=False, server_default="DRAFT"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False), sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("review_reason", sa.Text()), sa.Column("reviewed_by", sa.Integer()), sa.Column("submitted_at", sa.DateTime(timezone=True)), sa.Column("reviewed_at", sa.DateTime(timezone=True)), sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["district_id"], ["districts.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("end_at > start_at", name="ck_ad_campaign_dates"), sa.CheckConstraint("price_amount >= 0", name="ck_ad_campaign_price"))
    op.create_index("ix_ad_campaign_public", "advertising_campaigns", ["placement", "status", "start_at", "end_at"])
    op.create_index("ix_ad_campaign_hotel_created", "advertising_campaigns", ["hotel_id", "created_at"])
    for column in ("hotel_id", "district_id", "destination_id", "status", "end_at", "reviewed_by"):
        op.create_index(f"ix_advertising_campaigns_{column}", "advertising_campaigns", [column])
    op.drop_constraint("ck_payments_single_subject", "payments", type_="check")
    op.add_column("payments", sa.Column("advertising_campaign_id", sa.Integer()))
    op.create_foreign_key("fk_payments_advertising_campaign_id", "payments", "advertising_campaigns", ["advertising_campaign_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_payments_advertising_campaign_id", "payments", ["advertising_campaign_id"])
    op.create_index("ix_payments_ad_campaign_created", "payments", ["advertising_campaign_id", "created_at"])
    op.create_check_constraint("ck_payments_single_subject", "payments", "(booking_id IS NOT NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NOT NULL AND advertising_campaign_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NOT NULL)")
    op.create_table("advertising_events",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Enum("IMPRESSION", "CLICK", name="advertising_event_type", native_enum=False), nullable=False),
        sa.Column("dedupe_hash", sa.String(64), nullable=False), sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["advertising_campaigns.id"], ondelete="CASCADE"), sa.UniqueConstraint("campaign_id", "event_type", "dedupe_hash", "bucket_start", name="uq_ad_event_dedupe_bucket"))
    op.create_index("ix_ad_events_campaign_type", "advertising_events", ["campaign_id", "event_type"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "advertising_events" in inspector.get_table_names():
        op.drop_table("advertising_events")
    inspector = sa.inspect(bind)
    checks = {item["name"] for item in inspector.get_check_constraints("payments")}
    indexes = {item["name"] for item in inspector.get_indexes("payments")}
    foreign_keys = {item["name"] for item in inspector.get_foreign_keys("payments")}
    columns = {item["name"] for item in inspector.get_columns("payments")}
    if "ck_payments_single_subject" in checks:
        op.drop_constraint("ck_payments_single_subject", "payments", type_="check")
    if "ix_payments_ad_campaign_created" in indexes:
        op.drop_index("ix_payments_ad_campaign_created", table_name="payments")
    if "fk_payments_advertising_campaign_id" in foreign_keys:
        op.drop_constraint("fk_payments_advertising_campaign_id", "payments", type_="foreignkey")
    if "ix_payments_advertising_campaign_id" in indexes:
        op.drop_index("ix_payments_advertising_campaign_id", table_name="payments")
    if "advertising_campaign_id" in columns:
        op.drop_column("payments", "advertising_campaign_id")
    op.create_check_constraint("ck_payments_single_subject", "payments", "(booking_id IS NOT NULL AND verification_hotel_id IS NULL) OR (booking_id IS NULL AND verification_hotel_id IS NOT NULL)")
    if "advertising_campaigns" in inspector.get_table_names():
        op.drop_table("advertising_campaigns")
    op.alter_column("payments", "purpose", existing_type=sa.String(32), type_=sa.Enum("BOOKING", "VERIFICATION_FEE", name="payment_purpose", native_enum=False, length=16), existing_nullable=False, existing_server_default="BOOKING")
