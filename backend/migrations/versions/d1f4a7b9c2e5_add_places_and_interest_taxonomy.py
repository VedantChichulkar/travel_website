"""add places and interest taxonomy

Revision ID: d1f4a7b9c2e5
Revises: c8e4a1f6d2b9
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.data.interests import MAHARASHTRA_INTERESTS_V1


revision: str = "d1f4a7b9c2e5"
down_revision: str | None = "c8e4a1f6d2b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("display_order >= 0", name="ck_interests_display_order"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_interests_name"),
        sa.UniqueConstraint("slug", name="uq_interests_slug"),
    )
    op.create_index("ix_interests_public", "interests", ["is_active", "display_order"], unique=False)

    interest_table = sa.table(
        "interests",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("display_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        interest_table,
        [
            {
                "name": name,
                "slug": slug,
                "display_order": display_order,
                "is_active": True,
            }
            for name, slug, display_order in MAHARASHTRA_INTERESTS_V1
        ],
    )

    op.create_table(
        "places",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("short_description", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("spiritual_tradition", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("display_order >= 0", name="ck_places_display_order"),
        sa.CheckConstraint(
            "spiritual_tradition IS NULL OR spiritual_tradition IN "
            "('HINDU','BUDDHIST','JAIN','SIKH','ISLAMIC','CHRISTIAN','OTHER','MULTI_TRADITION')",
            name="ck_places_spiritual_tradition",
        ),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "name", name="uq_places_district_name"),
        sa.UniqueConstraint("district_id", "slug", name="uq_places_district_slug"),
    )
    op.create_index("ix_places_district_id", "places", ["district_id"], unique=False)
    op.create_index("ix_places_destination_id", "places", ["destination_id"], unique=False)
    op.create_index(
        "ix_places_public",
        "places",
        ["district_id", "is_active", "is_featured", "display_order"],
        unique=False,
    )
    op.create_index(
        "ix_places_destination_public",
        "places",
        ["destination_id", "is_active", "display_order"],
        unique=False,
    )

    op.create_table(
        "place_interests",
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("interest_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["interest_id"], ["interests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("place_id", "interest_id"),
    )
    op.create_index("ix_place_interests_interest_id", "place_interests", ["interest_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_place_interests_interest_id", table_name="place_interests")
    op.drop_table("place_interests")
    op.drop_index("ix_places_destination_public", table_name="places")
    op.drop_index("ix_places_public", table_name="places")
    op.drop_index("ix_places_destination_id", table_name="places")
    op.drop_index("ix_places_district_id", table_name="places")
    op.drop_table("places")
    op.drop_index("ix_interests_public", table_name="interests")
    op.drop_table("interests")

