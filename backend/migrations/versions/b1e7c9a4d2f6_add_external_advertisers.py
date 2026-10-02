"""add external advertisers to canonical advertising engine

Revision ID: b1e7c9a4d2f6
Revises: fa8c2d6e1b4f
"""
from alembic import op
import sqlalchemy as sa

revision = "b1e7c9a4d2f6"
down_revision = "fa8c2d6e1b4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advertiser_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("business_name", sa.String(160), nullable=False),
        sa.Column("contact_person", sa.String(100), nullable=False),
        sa.Column("business_email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(16), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("website", sa.String(2048)),
        sa.Column("status", sa.Enum("ACTIVE", "SUSPENDED", name="advertiser_status", native_enum=False), nullable=False, server_default="ACTIVE"),
        sa.Column("suspended_reason", sa.Text()), sa.Column("suspended_at", sa.DateTime(timezone=True)), sa.Column("suspended_by", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["suspended_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_advertiser_profiles_user_id"),
    )
    op.create_index("ix_advertiser_profiles_status", "advertiser_profiles", ["status"])

    op.add_column("advertising_campaigns", sa.Column("advertiser_type", sa.Enum("HOTEL", "EXTERNAL", name="advertiser_type", native_enum=False), nullable=False, server_default="HOTEL"))
    op.add_column("advertising_campaigns", sa.Column("advertiser_profile_id", sa.Integer()))
    op.add_column("advertising_campaigns", sa.Column("campaign_name", sa.String(160)))
    op.add_column("advertising_campaigns", sa.Column("headline", sa.String(120)))
    op.add_column("advertising_campaigns", sa.Column("short_copy", sa.String(280)))
    op.add_column("advertising_campaigns", sa.Column("target_url", sa.String(2048)))
    op.add_column("advertising_campaigns", sa.Column("approved_target_url", sa.String(2048)))
    op.add_column("advertising_campaigns", sa.Column("creative_width", sa.Integer()))
    op.add_column("advertising_campaigns", sa.Column("creative_height", sa.Integer()))
    op.add_column("advertising_campaigns", sa.Column("creative_rights_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("advertising_campaigns", sa.Column("creative_source", sa.String(255)))
    op.add_column("advertising_campaigns", sa.Column("refund_review_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("advertising_campaigns", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.alter_column("advertising_campaigns", "hotel_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key("fk_ad_campaign_advertiser_profile", "advertising_campaigns", "advertiser_profiles", ["advertiser_profile_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_advertising_campaigns_advertiser_type", "advertising_campaigns", ["advertiser_type"])
    op.create_index("ix_advertising_campaigns_advertiser_profile_id", "advertising_campaigns", ["advertiser_profile_id"])
    op.create_index("ix_ad_campaign_external_created", "advertising_campaigns", ["advertiser_profile_id", "created_at"])
    op.create_check_constraint("ck_ad_campaign_owner", "advertising_campaigns", "(advertiser_type = 'HOTEL' AND hotel_id IS NOT NULL AND advertiser_profile_id IS NULL) OR (advertiser_type = 'EXTERNAL' AND hotel_id IS NULL AND advertiser_profile_id IS NOT NULL)")


def downgrade() -> None:
    bind = op.get_bind(); inspector = sa.inspect(bind)
    checks = {item["name"] for item in inspector.get_check_constraints("advertising_campaigns")}
    indexes = {item["name"] for item in inspector.get_indexes("advertising_campaigns")}
    foreign_key_rows = inspector.get_foreign_keys("advertising_campaigns")
    foreign_keys = {item["name"] for item in foreign_key_rows}
    if "ck_ad_campaign_owner" in checks: op.drop_constraint("ck_ad_campaign_owner", "advertising_campaigns", type_="check")
    if "fk_ad_campaign_advertiser_profile" in foreign_keys: op.drop_constraint("fk_ad_campaign_advertiser_profile", "advertising_campaigns", type_="foreignkey")
    for index in ("ix_ad_campaign_external_created", "ix_advertising_campaigns_advertiser_profile_id", "ix_advertising_campaigns_advertiser_type"):
        if index in indexes: op.drop_index(index, table_name="advertising_campaigns")
    hotel_fk = next((item["name"] for item in foreign_key_rows if item.get("constrained_columns") == ["hotel_id"]), None)
    if hotel_fk: op.drop_constraint(hotel_fk, "advertising_campaigns", type_="foreignkey")
    op.alter_column("advertising_campaigns", "hotel_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("fk_advertising_campaigns_hotel_id", "advertising_campaigns", "hotels", ["hotel_id"], ["id"], ondelete="RESTRICT")
    for column in ("version", "refund_review_required", "creative_source", "creative_rights_confirmed", "creative_height", "creative_width", "approved_target_url", "target_url", "short_copy", "headline", "campaign_name", "advertiser_profile_id", "advertiser_type"):
        op.drop_column("advertising_campaigns", column)
    op.drop_table("advertiser_profiles")
