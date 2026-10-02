"""align safaris with official workflow

Revision ID: f1c3a7d9e2b4
Revises: d2e6f8a1b4c9
"""
from alembic import op
import sqlalchemy as sa

revision = "f1c3a7d9e2b4"
down_revision = "d2e6f8a1b4c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("safaris", sa.Column("booking_categories", sa.JSON(), nullable=True))
    op.add_column("safaris", sa.Column("vehicle_options", sa.JSON(), nullable=True))
    op.execute("UPDATE safaris SET booking_categories = JSON_ARRAY() WHERE booking_categories IS NULL")
    op.execute("UPDATE safaris SET vehicle_options = JSON_ARRAY() WHERE vehicle_options IS NULL")
    op.alter_column("safaris", "booking_categories", existing_type=sa.JSON(), nullable=False)
    op.alter_column("safaris", "vehicle_options", existing_type=sa.JSON(), nullable=False)
    op.add_column("safaris", sa.Column("official_reference_required", sa.Boolean(), nullable=False, server_default="1"))
    op.add_column("safaris", sa.Column("official_contact_required", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("safaris", sa.Column("official_document_required", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("safaris", sa.Column("source_url", sa.String(2048)))
    op.add_column("safaris", sa.Column("last_verified_at", sa.DateTime(timezone=True)))

    op.add_column("safari_requests", sa.Column("preferred_booking_category", sa.String(100)))
    op.add_column("safari_requests", sa.Column("preferred_vehicle_option", sa.String(100)))
    op.add_column("safari_requests", sa.Column("confirmed_booking_category", sa.String(100)))
    op.add_column("safari_requests", sa.Column("confirmed_vehicle_option", sa.String(100)))
    op.add_column("safari_requests", sa.Column("official_booking_contact", sa.String(512)))
    op.add_column("safari_requests", sa.Column("operator_confirmed_at", sa.DateTime(timezone=True)))
    op.add_column("safari_alternatives", sa.Column("booking_category", sa.String(100)))
    op.add_column("safari_alternatives", sa.Column("vehicle_option", sa.String(100)))

    op.create_table(
        "safari_operational_notices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("safari_id", sa.Integer()),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["safari_id"], ["safaris.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_safari_operational_notices_safari_id", "safari_operational_notices", ["safari_id"])
    op.create_index("ix_safari_notice_public_window", "safari_operational_notices", ["is_active", "effective_from", "effective_until"])


def downgrade() -> None:
    op.drop_index("ix_safari_notice_public_window", table_name="safari_operational_notices")
    op.drop_index("ix_safari_operational_notices_safari_id", table_name="safari_operational_notices")
    op.drop_table("safari_operational_notices")
    op.drop_column("safari_alternatives", "vehicle_option")
    op.drop_column("safari_alternatives", "booking_category")
    for column in ("operator_confirmed_at", "official_booking_contact", "confirmed_vehicle_option", "confirmed_booking_category", "preferred_vehicle_option", "preferred_booking_category"):
        op.drop_column("safari_requests", column)
    for column in ("last_verified_at", "source_url", "official_document_required", "official_contact_required", "official_reference_required", "vehicle_options", "booking_categories"):
        op.drop_column("safaris", column)
