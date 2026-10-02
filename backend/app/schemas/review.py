from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.review import ReviewChallengeReason, ReviewChallengeStatus, ReviewModerationStatus, ReviewRiskLevel


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    overall_rating: int = Field(ge=1, le=5)
    cleanliness_rating: int = Field(ge=1, le=5)
    service_rating: int = Field(ge=1, le=5)
    location_rating: int = Field(ge=1, le=5)
    room_quality_rating: int = Field(ge=1, le=5)
    value_rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=10, max_length=5000)


class HotelReviewResponseCreate(BaseModel):
    response_text: str = Field(min_length=3, max_length=3000)


class ReviewChallengeCreate(BaseModel):
    reason: ReviewChallengeReason
    details: str = Field(min_length=10, max_length=3000)


class ModerationAction(str, Enum):
    PUBLISH = "PUBLISH"
    REJECT = "REJECT"


class ReviewModerationRequest(BaseModel):
    action: ModerationAction
    note: str = Field(min_length=3, max_length=3000)


class HotelSummary(OrmModel):
    id: int
    name: str


class BookingSummary(OrmModel):
    id: int
    booking_reference: str
    checked_out_at: datetime | None


class HotelReviewResponse(OrmModel):
    id: int
    response_text: str
    created_at: datetime


class ReviewChallengeResponse(OrmModel):
    id: int
    reason: ReviewChallengeReason
    details: str
    status: ReviewChallengeStatus
    resolution_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class ReviewRead(OrmModel):
    id: int
    booking_id: int
    hotel_id: int
    overall_rating: int
    cleanliness_rating: int
    service_rating: int
    location_rating: int
    room_quality_rating: int
    value_rating: int
    review_text: str
    verified_stay: bool
    moderation_status: ReviewModerationStatus
    created_at: datetime
    hotel: HotelSummary
    booking: BookingSummary
    hotel_response: HotelReviewResponse | None
    challenge: ReviewChallengeResponse | None


class PublicReview(OrmModel):
    id: int
    overall_rating: int
    cleanliness_rating: int
    service_rating: int
    location_rating: int
    room_quality_rating: int
    value_rating: int
    review_text: str
    verified_stay: bool
    created_at: datetime
    hotel_response: HotelReviewResponse | None
    reviewer_label: str = "Verified Maharashtra Tourist Places guest"


class PublicReviewList(BaseModel):
    items: list[PublicReview]
    total: int
    average_overall_rating: float | None


class AdminModerationEvent(OrmModel):
    id: int
    old_status: ReviewModerationStatus | None
    new_status: ReviewModerationStatus
    note: str
    actor_user_id: int | None
    created_at: datetime


class AdminReview(ReviewRead):
    risk_level: ReviewRiskLevel
    risk_reasons: list[str]
    moderation_events: list[AdminModerationEvent]
