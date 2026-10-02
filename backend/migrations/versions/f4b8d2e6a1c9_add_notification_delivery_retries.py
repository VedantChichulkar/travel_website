"""add transactional notification delivery retries

Revision ID: f4b8d2e6a1c9
Revises: e3a7c9d1f5b2
"""

from alembic import op
import sqlalchemy as sa


revision = "f4b8d2e6a1c9"
down_revision = "e3a7c9d1f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_jobs", sa.Column("provider_message_id", sa.String(length=160), nullable=True))
    op.add_column("notification_jobs", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.add_column("notification_jobs", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notification_jobs", sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notification_jobs", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE notification_jobs SET idempotency_key = CONCAT('legacy-notification-job-', id) WHERE idempotency_key IS NULL")
    op.alter_column("notification_jobs", "idempotency_key", existing_type=sa.String(length=120), nullable=False)
    op.create_unique_constraint("uq_notification_jobs_idempotency", "notification_jobs", ["idempotency_key"])
    op.create_index("ix_notification_jobs_next_retry_at", "notification_jobs", ["next_retry_at"])
    op.create_index("ix_notification_jobs_status_retry", "notification_jobs", ["status", "next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_jobs_status_retry", table_name="notification_jobs")
    op.drop_index("ix_notification_jobs_next_retry_at", table_name="notification_jobs")
    op.drop_constraint("uq_notification_jobs_idempotency", "notification_jobs", type_="unique")
    for column in ("sent_at", "last_attempt_at", "next_retry_at", "idempotency_key", "provider_message_id"):
        op.drop_column("notification_jobs", column)
