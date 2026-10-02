"""add communication gateway and transactional notifications

Revision ID: c6d9a2e4f7b1
Revises: a1c3e5f7b9d2
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c6d9a2e4f7b1"
down_revision: str | None = "a1c3e5f7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


conversation_kind = sa.Enum("PRE_BOOKING", "BOOKING", "OPERATIONAL", "DISPUTE", name="conversation_kind", native_enum=False)
conversation_status = sa.Enum("OPEN", "CLOSED", name="conversation_status", native_enum=False)
notification_event_type = sa.Enum("BOOKING_CONFIRMATION", "PAYMENT_SUCCESS", "PAYMENT_FAILURE", "CANCELLATION", "REFUND_INITIATED", "REFUND_COMPLETED", "CHECK_IN_REMINDER", "CHECK_OUT_REMINDER", "NO_SHOW", "HOTEL_OPERATIONAL_ISSUE", "DISPUTE", "SETTLEMENT_UPDATE", "REVIEW_RECEIVED", "REVIEW_CHALLENGED", name="notification_event_type", native_enum=False)
notification_channel = sa.Enum("EMAIL", "SMS", "WHATSAPP", name="notification_channel", native_enum=False)
notification_job_status = sa.Enum("PENDING", "SENT", "FAILED", "PROVIDER_UNAVAILABLE", name="notification_job_status", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hotel_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("kind", conversation_kind, nullable=False),
        sa.Column("status", conversation_status, nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_customer_updated", "conversations", ["customer_id", "updated_at"])
    op.create_index("ix_conversations_hotel_updated", "conversations", ["hotel_id", "updated_at"])
    op.create_index("ix_conversations_booking_id", "conversations", ["booking_id"])
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_sender_user_id", "messages", ["sender_user_id"])
    op.create_table(
        "conversation_read_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_conversation_read_user"),
    )
    op.create_index("ix_conversation_read_states_conversation_id", "conversation_read_states", ["conversation_id"])
    op.create_index("ix_conversation_read_states_user_id", "conversation_read_states", ["user_id"])
    op.create_table(
        "conversation_admin_access",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversation_admin_access_conversation_id", "conversation_admin_access", ["conversation_id"])
    op.create_index("ix_conversation_admin_access_admin_user_id", "conversation_admin_access", ["admin_user_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", notification_event_type, nullable=False),
        sa.Column("dedupe_key", sa.String(180), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipient_user_id", "dedupe_key", name="uq_notifications_recipient_dedupe"),
    )
    op.create_index("ix_notifications_recipient_created", "notifications", ["recipient_user_id", "created_at"])
    op.create_index("ix_notifications_event_type", "notifications", ["event_type"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])
    op.create_table(
        "notification_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("status", notification_job_status, nullable=False, server_default="PROVIDER_UNAVAILABLE"),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id", "channel", name="uq_notification_jobs_channel"),
    )
    op.create_index("ix_notification_jobs_notification_id", "notification_jobs", ["notification_id"])


def downgrade() -> None:
    op.drop_table("notification_jobs")
    op.drop_table("notifications")
    op.drop_table("conversation_admin_access")
    op.drop_table("conversation_read_states")
    op.drop_table("messages")
    op.drop_table("conversations")
