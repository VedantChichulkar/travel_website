"""productionize private documents

Revision ID: f2c8a4d6e1b9
Revises: e6a2c8f4b1d7
"""

from alembic import op
import sqlalchemy as sa


revision = "f2c8a4d6e1b9"
down_revision = "e6a2c8f4b1d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hotel_verifications", sa.Column("document_checksum_sha256", sa.String(64), nullable=True))
    op.add_column("hotel_verifications", sa.Column("document_uploaded_by", sa.Integer(), nullable=True))
    op.add_column("hotel_verifications", sa.Column("document_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_hotel_verifications_document_uploaded_by", "hotel_verifications", "users", ["document_uploaded_by"], ["id"], ondelete="SET NULL")
    op.add_column("safari_documents", sa.Column("checksum_sha256", sa.String(64), nullable=True))
    op.add_column("safari_documents", sa.Column("uploaded_by", sa.Integer(), nullable=True))
    op.create_index("ix_safari_documents_uploaded_by", "safari_documents", ["uploaded_by"])
    op.create_foreign_key("fk_safari_documents_uploaded_by", "safari_documents", "users", ["uploaded_by"], ["id"], ondelete="SET NULL")
    op.create_table(
        "private_document_deletion_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PROCESSING", "FAILED", "COMPLETED", name="private_document_deletion_status", native_enum=False), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_private_document_deletion_jobs_next_retry_at", "private_document_deletion_jobs", ["next_retry_at"])
    op.create_index("ix_private_document_deletion_due", "private_document_deletion_jobs", ["status", "next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_private_document_deletion_due", table_name="private_document_deletion_jobs")
    op.drop_index("ix_private_document_deletion_jobs_next_retry_at", table_name="private_document_deletion_jobs")
    op.drop_table("private_document_deletion_jobs")
    op.drop_constraint("fk_safari_documents_uploaded_by", "safari_documents", type_="foreignkey")
    op.drop_index("ix_safari_documents_uploaded_by", table_name="safari_documents")
    op.drop_column("safari_documents", "uploaded_by")
    op.drop_column("safari_documents", "checksum_sha256")
    op.drop_constraint("fk_hotel_verifications_document_uploaded_by", "hotel_verifications", type_="foreignkey")
    op.drop_column("hotel_verifications", "document_uploaded_at")
    op.drop_column("hotel_verifications", "document_uploaded_by")
    op.drop_column("hotel_verifications", "document_checksum_sha256")
