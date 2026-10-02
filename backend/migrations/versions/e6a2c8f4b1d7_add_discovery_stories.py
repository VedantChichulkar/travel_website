"""add discovery stories

Revision ID: e6a2c8f4b1d7
Revises: d1f4a7b9c2e5
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e6a2c8f4b1d7"
down_revision: str | None = "d1f4a7b9c2e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_stories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("short_description", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("display_order >= 0", name="ck_discovery_stories_display_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_discovery_stories_slug"),
        sa.UniqueConstraint("title", name="uq_discovery_stories_title"),
    )
    op.create_index("ix_discovery_stories_public", "discovery_stories", ["is_active", "is_featured", "display_order"])

    _association_table("discovery_story_interests", "interest_id", "interests", "ix_discovery_story_interests_interest_id")
    _association_table("discovery_story_districts", "district_id", "districts", "ix_discovery_story_districts_district_id")
    _association_table("discovery_story_destinations", "destination_id", "destinations", "ix_discovery_story_destinations_destination_id")
    _association_table("discovery_story_places", "place_id", "places", "ix_discovery_story_places_place_id")


def _association_table(name: str, related_column: str, related_table: str, index_name: str) -> None:
    op.create_table(
        name,
        sa.Column("story_id", sa.Integer(), nullable=False),
        sa.Column(related_column, sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["story_id"], ["discovery_stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint([related_column], [f"{related_table}.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("story_id", related_column),
    )
    op.create_index(index_name, name, [related_column])


def downgrade() -> None:
    for name in (
        "discovery_story_places",
        "discovery_story_destinations",
        "discovery_story_districts",
        "discovery_story_interests",
    ):
        op.drop_table(name)
    op.drop_index("ix_discovery_stories_public", table_name="discovery_stories")
    op.drop_table("discovery_stories")
