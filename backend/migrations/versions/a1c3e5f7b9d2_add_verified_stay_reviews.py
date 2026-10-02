"""add verified stay reviews and moderation

Revision ID: a1c3e5f7b9d2
Revises: f9b2d6e4a8c1
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a1c3e5f7b9d2"
down_revision: str | None = "f9b2d6e4a8c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


moderation_status = sa.Enum("PUBLISHED", "PENDING_REVIEW", "REJECTED", name="review_moderation_status", native_enum=False)
risk_level = sa.Enum("NORMAL", "HIGH", name="review_risk_level", native_enum=False)
challenge_reason = sa.Enum("FAKE_OR_MISLEADING", "WRONG_PROPERTY", "SPAM", "ABUSIVE_CONTENT", "PERSONAL_INFORMATION", "EXTORTION", "MANIPULATION", "OTHER_POLICY_VIOLATION", name="review_challenge_reason", native_enum=False)
challenge_status = sa.Enum("OPEN", "UPHELD", "DISMISSED", name="review_challenge_status", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("hotel_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=False),
        sa.Column("cleanliness_rating", sa.Integer(), nullable=False),
        sa.Column("service_rating", sa.Integer(), nullable=False),
        sa.Column("location_rating", sa.Integer(), nullable=False),
        sa.Column("room_quality_rating", sa.Integer(), nullable=False),
        sa.Column("value_rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("verified_stay", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("moderation_status", moderation_status, nullable=False),
        sa.Column("risk_level", risk_level, nullable=False, server_default="NORMAL"),
        sa.Column("risk_reasons", sa.JSON(), nullable=False),
        sa.Column("moderated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_reviews_overall"),
        sa.CheckConstraint("cleanliness_rating BETWEEN 1 AND 5", name="ck_reviews_cleanliness"),
        sa.CheckConstraint("service_rating BETWEEN 1 AND 5", name="ck_reviews_service"),
        sa.CheckConstraint("location_rating BETWEEN 1 AND 5", name="ck_reviews_location"),
        sa.CheckConstraint("room_quality_rating BETWEEN 1 AND 5", name="ck_reviews_room_quality"),
        sa.CheckConstraint("value_rating BETWEEN 1 AND 5", name="ck_reviews_value"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["moderated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("booking_id", name="uq_reviews_booking"),
    )
    op.create_index("ix_reviews_booking_id", "reviews", ["booking_id"], unique=True)
    op.create_index("ix_reviews_hotel_id", "reviews", ["hotel_id"])
    op.create_index("ix_reviews_customer_id", "reviews", ["customer_id"])
    op.create_index("ix_reviews_moderation_status", "reviews", ["moderation_status"])
    op.create_index("ix_reviews_moderated_by_user_id", "reviews", ["moderated_by_user_id"])
    op.create_index("ix_reviews_hotel_moderation", "reviews", ["hotel_id", "moderation_status"])

    op.create_table(
        "review_responses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("responded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["responded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id", name="uq_review_responses_review"),
    )
    op.create_index("ix_review_responses_review_id", "review_responses", ["review_id"], unique=True)
    op.create_index("ix_review_responses_responded_by_user_id", "review_responses", ["responded_by_user_id"])

    op.create_table(
        "review_challenges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("reason", challenge_reason, nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("status", challenge_status, nullable=False, server_default="OPEN"),
        sa.Column("challenged_by_user_id", sa.Integer(), nullable=False),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["challenged_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id", name="uq_review_challenges_review"),
    )
    op.create_index("ix_review_challenges_review_id", "review_challenges", ["review_id"], unique=True)
    op.create_index("ix_review_challenges_status", "review_challenges", ["status"])
    op.create_index("ix_review_challenges_challenged_by_user_id", "review_challenges", ["challenged_by_user_id"])
    op.create_index("ix_review_challenges_resolved_by_user_id", "review_challenges", ["resolved_by_user_id"])

    op.create_table(
        "review_moderation_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("old_status", moderation_status, nullable=True),
        sa.Column("new_status", moderation_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_moderation_events_review_id", "review_moderation_events", ["review_id"])
    op.create_index("ix_review_moderation_events_actor_user_id", "review_moderation_events", ["actor_user_id"])


def downgrade() -> None:
    op.drop_table("review_moderation_events")
    op.drop_table("review_challenges")
    op.drop_table("review_responses")
    op.drop_table("reviews")
