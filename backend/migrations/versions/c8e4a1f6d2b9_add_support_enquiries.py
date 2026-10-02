"""add support enquiries

Revision ID: c8e4a1f6d2b9
Revises: f1c3a7d9e2b4
"""
from alembic import op
import sqlalchemy as sa


revision = "c8e4a1f6d2b9"
down_revision = "f1c3a7d9e2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_enquiries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("reference", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(80), nullable=False),
        sa.Column("user_id", sa.Integer()),
        sa.Column("enquiry_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("email", sa.String(768), nullable=False),
        sa.Column("mobile", sa.String(256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("customer_reference", sa.String(512)),
        sa.Column("property_name", sa.String(512)),
        sa.Column("location", sa.String(512)),
        sa.Column("booking_id", sa.Integer()),
        sa.Column("safari_request_id", sa.Integer()),
        sa.Column("status", sa.String(24), nullable=False, server_default="RECEIVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["safari_request_id"], ["safari_requests.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("idempotency_key", name="uq_support_enquiries_idempotency_key"),
    )
    op.create_index("ix_support_enquiries_reference", "support_enquiries", ["reference"], unique=True)
    op.create_index("ix_support_enquiries_user_id", "support_enquiries", ["user_id"])
    op.create_index("ix_support_enquiries_enquiry_type", "support_enquiries", ["enquiry_type"])
    op.create_index("ix_support_enquiries_booking_id", "support_enquiries", ["booking_id"])
    op.create_index("ix_support_enquiries_safari_request_id", "support_enquiries", ["safari_request_id"])
    op.create_index("ix_support_enquiries_status", "support_enquiries", ["status"])
    op.create_index("ix_support_enquiries_queue", "support_enquiries", ["status", "created_at"])
    op.create_index("ix_support_enquiries_user_created", "support_enquiries", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("support_enquiries")
