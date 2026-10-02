"""enrich destination and place discovery content

Revision ID: c3d8e1f5a7b2
Revises: b1e7c9a4d2f6
"""
from alembic import op
import sqlalchemy as sa


revision = "c3d8e1f5a7b2"
down_revision = "b1e7c9a4d2f6"
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def upgrade() -> None:
    op.add_column("destinations", sa.Column("short_summary", sa.String(500)))
    for name, column in (
        ("address", sa.String(500)),
        ("opening_hours", sa.Text()),
        ("entry_fee_info", sa.Text()),
        ("recommended_visit_duration", sa.String(120)),
        ("best_time_to_visit", sa.String(300)),
        ("getting_there", sa.Text()),
        ("nearest_railway_station", sa.String(300)),
        ("nearest_airport", sa.String(300)),
        ("visitor_info_source", sa.String(500)),
        ("visitor_info_source_url", sa.String(2048)),
        ("visitor_info_verified_at", sa.Date()),
    ):
        op.add_column("places", sa.Column(name, column))

    op.create_table(
        "destination_faqs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.CheckConstraint("display_order >= 0", name="ck_destination_faqs_display_order"),
    )
    op.create_index("ix_destination_faqs_public", "destination_faqs", ["destination_id", "is_active", "display_order"])
    op.create_table(
        "place_faqs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.CheckConstraint("display_order >= 0", name="ck_place_faqs_display_order"),
    )
    op.create_index("ix_place_faqs_public", "place_faqs", ["place_id", "is_active", "display_order"])

    for table, owner, owner_table in (
        ("destination_media", "destination_id", "destinations"),
        ("place_media", "place_id", "places"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(owner, sa.Integer(), nullable=False),
            sa.Column("media_asset_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(16), nullable=False, server_default="GALLERY"),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint([owner], [f"{owner_table}.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["media_asset_id"], ["public_media_assets.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("media_asset_id", name=f"uq_{table}_asset"),
            sa.CheckConstraint("role IN ('HERO','GALLERY')", name=f"ck_{table}_role"),
            sa.CheckConstraint("display_order >= 0", name=f"ck_{table}_display_order"),
        )
        op.create_index(f"ix_{table}_order", table, [owner, "role", "display_order"])

    connection = op.get_bind()
    connection.execute(sa.text(
        "INSERT INTO destination_media (destination_id, media_asset_id, role, display_order) "
        "SELECT id, media_asset_id, 'HERO', 0 FROM destinations WHERE media_asset_id IS NOT NULL"
    ))
    connection.execute(sa.text(
        "INSERT INTO place_media (place_id, media_asset_id, role, display_order) "
        "SELECT id, media_asset_id, 'HERO', 0 FROM places WHERE media_asset_id IS NOT NULL"
    ))


def downgrade() -> None:
    op.drop_table("place_media")
    op.drop_table("destination_media")
    op.drop_table("place_faqs")
    op.drop_table("destination_faqs")
    for name in (
        "visitor_info_verified_at", "visitor_info_source_url", "visitor_info_source", "nearest_airport",
        "nearest_railway_station", "getting_there", "best_time_to_visit", "recommended_visit_duration",
        "entry_fee_info", "opening_hours", "address",
    ):
        op.drop_column("places", name)
    op.drop_column("destinations", "short_summary")
