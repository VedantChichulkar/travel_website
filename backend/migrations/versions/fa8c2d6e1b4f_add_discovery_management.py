"""add production discovery management

Revision ID: fa8c2d6e1b4f
Revises: f7a3d9c2e5b1
"""

from alembic import op
import sqlalchemy as sa


revision = "fa8c2d6e1b4f"
down_revision = "f7a3d9c2e5b1"
branch_labels = None
depends_on = None


def _add_lifecycle(table: str) -> None:
    op.add_column(table, sa.Column("image_alt", sa.String(300), nullable=True))
    op.add_column(table, sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(table, sa.Column("content_source", sa.String(16), nullable=False, server_default="CURATED"))
    op.add_column(table, sa.Column("admin_overridden", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column(table, sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def upgrade() -> None:
    op.create_table(
        "public_media_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(24), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("public_url", sa.String(2048), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("alt_text", sa.String(300), nullable=False),
        sa.Column("specificity", sa.String(16), nullable=False),
        sa.Column("creator_owner", sa.String(200), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("usage_basis", sa.String(200), nullable=False),
        sa.Column("attribution_text", sa.String(500), nullable=True),
        sa.Column("rights_verified_at", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("replaced_by_asset_id", sa.Integer(), sa.ForeignKey("public_media_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_public_media_assets_status_created", "public_media_assets", ["status", "created_at"])
    op.create_index("ix_public_media_assets_entity", "public_media_assets", ["entity_type", "entity_id"])
    op.create_index("ix_public_media_assets_created_by_user_id", "public_media_assets", ["created_by_user_id"])
    for table in ("destinations", "places"):
        _add_lifecycle(table)
        op.add_column(table, sa.Column("media_asset_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table}_media_asset", table, "public_media_assets", ["media_asset_id"], ["id"], ondelete="SET NULL")
        op.create_index(f"ix_{table}_media_asset_id", table, ["media_asset_id"])
        op.execute(sa.text(f"UPDATE {table} SET published_at = created_at WHERE is_active = 1"))


def downgrade() -> None:
    for table in ("places", "destinations"):
        op.drop_index(f"ix_{table}_media_asset_id", table_name=table)
        op.drop_constraint(f"fk_{table}_media_asset", table, type_="foreignkey")
        op.drop_column(table, "media_asset_id")
        for column in ("version", "admin_overridden", "content_source", "published_at", "image_alt"):
            op.drop_column(table, column)
    op.drop_index("ix_public_media_assets_created_by_user_id", table_name="public_media_assets")
    op.drop_index("ix_public_media_assets_entity", table_name="public_media_assets")
    op.drop_index("ix_public_media_assets_status_created", table_name="public_media_assets")
    op.drop_table("public_media_assets")
