from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, event, func, inspect
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.hotel import Hotel
    from app.models.user import User


class ReviewModerationStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"


class ReviewRiskLevel(str, Enum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class ReviewChallengeReason(str, Enum):
    FAKE_OR_MISLEADING = "FAKE_OR_MISLEADING"
    WRONG_PROPERTY = "WRONG_PROPERTY"
    SPAM = "SPAM"
    ABUSIVE_CONTENT = "ABUSIVE_CONTENT"
    PERSONAL_INFORMATION = "PERSONAL_INFORMATION"
    EXTORTION = "EXTORTION"
    MANIPULATION = "MANIPULATION"
    OTHER_POLICY_VIOLATION = "OTHER_POLICY_VIOLATION"


class ReviewChallengeStatus(str, Enum):
    OPEN = "OPEN"
    UPHELD = "UPHELD"
    DISMISSED = "DISMISSED"


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_reviews_booking"),
        CheckConstraint("overall_rating BETWEEN 1 AND 5", name="ck_reviews_overall"),
        CheckConstraint("cleanliness_rating BETWEEN 1 AND 5", name="ck_reviews_cleanliness"),
        CheckConstraint("service_rating BETWEEN 1 AND 5", name="ck_reviews_service"),
        CheckConstraint("location_rating BETWEEN 1 AND 5", name="ck_reviews_location"),
        CheckConstraint("room_quality_rating BETWEEN 1 AND 5", name="ck_reviews_room_quality"),
        CheckConstraint("value_rating BETWEEN 1 AND 5", name="ck_reviews_value"),
        Index("ix_reviews_hotel_moderation", "hotel_id", "moderation_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    cleanliness_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    service_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    location_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    room_quality_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    value_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    verified_stay: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    moderation_status: Mapped[ReviewModerationStatus] = mapped_column(SqlEnum(ReviewModerationStatus, name="review_moderation_status", native_enum=False), nullable=False, index=True)
    risk_level: Mapped[ReviewRiskLevel] = mapped_column(SqlEnum(ReviewRiskLevel, name="review_risk_level", native_enum=False), nullable=False, default=ReviewRiskLevel.NORMAL, server_default=ReviewRiskLevel.NORMAL.value)
    risk_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    moderated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    booking: Mapped[Booking] = relationship("Booking", foreign_keys=[booking_id])
    hotel: Mapped[Hotel] = relationship("Hotel", foreign_keys=[hotel_id])
    customer: Mapped[User] = relationship("User", foreign_keys=[customer_id])
    moderated_by: Mapped[User | None] = relationship("User", foreign_keys=[moderated_by_user_id])
    hotel_response: Mapped[ReviewResponse | None] = relationship(back_populates="review", cascade="all, delete-orphan", uselist=False)
    challenge: Mapped[ReviewChallenge | None] = relationship(back_populates="review", cascade="all, delete-orphan", uselist=False)
    moderation_events: Mapped[list[ReviewModerationEvent]] = relationship(back_populates="review", cascade="all, delete-orphan", order_by="ReviewModerationEvent.id")


class ReviewResponse(Base):
    __tablename__ = "review_responses"
    __table_args__ = (UniqueConstraint("review_id", name="uq_review_responses_review"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    responded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    review: Mapped[Review] = relationship(back_populates="hotel_response")
    responded_by: Mapped[User] = relationship("User", foreign_keys=[responded_by_user_id])


class ReviewChallenge(Base):
    __tablename__ = "review_challenges"
    __table_args__ = (UniqueConstraint("review_id", name="uq_review_challenges_review"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    reason: Mapped[ReviewChallengeReason] = mapped_column(SqlEnum(ReviewChallengeReason, name="review_challenge_reason", native_enum=False), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReviewChallengeStatus] = mapped_column(SqlEnum(ReviewChallengeStatus, name="review_challenge_status", native_enum=False), nullable=False, default=ReviewChallengeStatus.OPEN, server_default=ReviewChallengeStatus.OPEN.value, index=True)
    challenged_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    review: Mapped[Review] = relationship(back_populates="challenge")
    challenged_by: Mapped[User] = relationship("User", foreign_keys=[challenged_by_user_id])
    resolved_by: Mapped[User | None] = relationship("User", foreign_keys=[resolved_by_user_id])


class ReviewModerationEvent(Base):
    __tablename__ = "review_moderation_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="RESTRICT"), nullable=False, index=True)
    old_status: Mapped[ReviewModerationStatus | None] = mapped_column(SqlEnum(ReviewModerationStatus, name="review_moderation_status", native_enum=False))
    new_status: Mapped[ReviewModerationStatus] = mapped_column(SqlEnum(ReviewModerationStatus, name="review_moderation_status", native_enum=False), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    review: Mapped[Review] = relationship(back_populates="moderation_events")
    actor: Mapped[User | None] = relationship("User", foreign_keys=[actor_user_id])


@event.listens_for(Review, "before_update")
def prevent_customer_content_rewrite(_mapper, _connection, target: Review) -> None:
    """Only moderation metadata may change after the review is created."""
    session = object_session(target)
    if session is None or not session.is_modified(target, include_collections=False):
        return
    state = inspect(target)
    protected = ("booking_id", "hotel_id", "customer_id", "overall_rating", "cleanliness_rating", "service_rating", "location_rating", "room_quality_rating", "value_rating", "review_text", "verified_stay", "created_at")
    if any(state.attrs[name].history.has_changes() for name in protected):
        raise ValueError("Customer review content and ratings are immutable")
