"""add Maharashtra districts and destinations

Revision ID: b8d2f4a6c9e1
Revises: a5c9e3f7b2d1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from app.data.maharashtra import MAHARASHTRA_DISTRICTS_V1


revision: str = "b8d2f4a6c9e1"
down_revision: str | None = "a5c9e3f7b2d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "districts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("division", sa.String(length=80), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("hero_image_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_districts_name"),
        sa.UniqueConstraint("slug", name="uq_districts_slug"),
    )
    op.create_index("ix_districts_division", "districts", ["division"], unique=False)
    op.create_index("ix_districts_public", "districts", ["is_active", "name"], unique=False)

    district_table = sa.table(
        "districts",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("division", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        district_table,
        [
            {"name": name, "slug": slug, "division": division, "is_active": True}
            for name, slug, division in MAHARASHTRA_DISTRICTS_V1
        ],
    )

    op.create_table(
        "destinations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "name", name="uq_destinations_district_name"),
        sa.UniqueConstraint("district_id", "slug", name="uq_destinations_district_slug"),
    )
    op.create_index("ix_destinations_district_id", "destinations", ["district_id"], unique=False)
    op.create_index("ix_destinations_public", "destinations", ["district_id", "is_active", "name"], unique=False)

    op.add_column("hotels", sa.Column("district_id", sa.Integer(), nullable=True))
    op.add_column("hotels", sa.Column("destination_id", sa.Integer(), nullable=True))
    op.create_index("ix_hotels_district_id", "hotels", ["district_id"], unique=False)
    op.create_index("ix_hotels_destination_id", "hotels", ["destination_id"], unique=False)
    op.create_foreign_key(
        "fk_hotels_district_id_districts", "hotels", "districts", ["district_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_hotels_destination_id_destinations", "hotels", "destinations", ["destination_id"], ["id"], ondelete="SET NULL"
    )

    # Keep historical free-text locations intact; link exact Maharashtra district
    # identities, including official rename aliases, wherever it is safe to do so.
    connection = op.get_bind()
    dialect = connection.dialect.name
    source = "LOWER(TRIM(COALESCE(NULLIF(h.district, ''), h.city)))"
    canonical = (
        f"CASE {source} "
        "WHEN 'ahmednagar' THEN 'ahilyanagar' "
        "WHEN 'aurangabad' THEN 'chhatrapati sambhajinagar' "
        "WHEN 'osmanabad' THEN 'dharashiv' "
        "WHEN 'buldana' THEN 'buldhana' "
        "WHEN 'gondiya' THEN 'gondia' "
        f"ELSE {source} END"
    )
    if dialect == "mysql":
        connection.execute(sa.text(
            "UPDATE hotels h JOIN districts d ON LOWER(d.name) = " + canonical
            + " SET h.district_id = d.id WHERE LOWER(TRIM(h.state)) = 'maharashtra' AND h.district_id IS NULL"
        ))
    else:
        connection.execute(sa.text(
            "UPDATE hotels AS h SET district_id = (SELECT d.id FROM districts AS d WHERE LOWER(d.name) = "
            + canonical
            + ") WHERE LOWER(TRIM(h.state)) = 'maharashtra' AND h.district_id IS NULL"
        ))


def downgrade() -> None:
    op.drop_constraint("fk_hotels_destination_id_destinations", "hotels", type_="foreignkey")
    op.drop_constraint("fk_hotels_district_id_districts", "hotels", type_="foreignkey")
    op.drop_index("ix_hotels_destination_id", table_name="hotels")
    op.drop_index("ix_hotels_district_id", table_name="hotels")
    op.drop_column("hotels", "destination_id")
    op.drop_column("hotels", "district_id")
    op.drop_index("ix_destinations_public", table_name="destinations")
    op.drop_index("ix_destinations_district_id", table_name="destinations")
    op.drop_table("destinations")
    op.drop_index("ix_districts_public", table_name="districts")
    op.drop_index("ix_districts_division", table_name="districts")
    op.drop_table("districts")
