"""Verified-stay reviews, hotel responses, challenges, and moderation."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.booking import Booking, BookingStatus
from app.models.review import Review, ReviewChallenge, ReviewChallengeStatus, ReviewModerationEvent, ReviewModerationStatus, ReviewResponse, ReviewRiskLevel
from app.models.user import User, UserRole
from app.repositories import hotel_repository
from app.schemas.review import ModerationAction, ReviewChallengeCreate, ReviewCreate
from app.services import notification_service
from app.models.communication import NotificationEventType
from app.models.hotel import Hotel
from app.services import audit_service


def _options():
    return (
        selectinload(Review.hotel),
        selectinload(Review.booking),
        selectinload(Review.hotel_response),
        selectinload(Review.challenge),
        selectinload(Review.moderation_events),
    )


def _risk_reasons(text: str) -> list[str]:
    normalized = " ".join(text.lower().split())
    reasons: list[str] = []
    if re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", normalized) or re.search(r"(?:\+?\d[\s().-]*){10,}", normalized):
        reasons.append("PERSONAL_INFORMATION")
    if any(phrase in normalized for phrase in ("refund me or i will", "pay me or i will", "money or i will remove", "compensate me or")):
        reasons.append("EXTORTION")
    if len(re.findall(r"https?://|www\.", normalized)) >= 2:
        reasons.append("SPAM")
    if any(phrase in normalized for phrase in ("i will kill", "i will hurt", "death threat")):
        reasons.append("ABUSIVE_THREAT")
    return reasons


def create_review(db: Session, customer: User, booking_id: int, data: ReviewCreate) -> Review:
    if customer.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required")
    booking = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == customer.id).with_for_update())
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eligible completed booking not found")
    if booking.status != BookingStatus.CHECKED_OUT or booking.checked_out_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a completed Maharashtra Tourist Places stay can be reviewed")
    if db.scalar(select(Review.id).where(Review.booking_id == booking.id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This stay already has a review")
    reasons = _risk_reasons(data.review_text)
    moderation = ReviewModerationStatus.PENDING_REVIEW if reasons else ReviewModerationStatus.PUBLISHED
    review = Review(booking_id=booking.id, hotel_id=booking.hotel_id, customer_id=customer.id, **data.model_dump(), verified_stay=True, risk_level=ReviewRiskLevel.HIGH if reasons else ReviewRiskLevel.NORMAL, risk_reasons=reasons, moderation_status=moderation)
    review.moderation_events.append(ReviewModerationEvent(old_status=None, new_status=moderation, note="High-risk content routed to moderation" if reasons else "Verified stay review published", actor_user_id=customer.id))
    db.add(review)
    db.flush()
    hotel = db.get(Hotel, booking.hotel_id)
    if hotel and hotel.partner_id:
        notification_service.create(db, recipient_user_id=hotel.partner_id, event_type=NotificationEventType.REVIEW_RECEIVED, dedupe_key=f"REVIEW_RECEIVED:{review.id}", title="New guest review", body=f"A verified guest reviewed booking {booking.booking_reference}.", data={"review_id": review.id, "booking_id": booking.id, "hotel_id": booking.hotel_id})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This stay already has a review") from exc
    return get_customer_review(db, customer, booking.id)


def get_customer_review(db: Session, customer: User, booking_id: int) -> Review:
    review = db.scalar(select(Review).where(Review.booking_id == booking_id, Review.customer_id == customer.id).options(*_options()))
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review


def list_public(db: Session, hotel_id: int) -> list[Review]:
    return list(db.scalars(select(Review).where(Review.hotel_id == hotel_id, Review.moderation_status == ReviewModerationStatus.PUBLISHED).options(*_options()).order_by(Review.created_at.desc())))


def _partner_hotel_id(db: Session, partner: User) -> int:
    if partner.role != UserRole.HOTEL_PARTNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hotel partner access required")
    hotel = hotel_repository.get_hotel_by_partner_id(db, partner.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return hotel.id


def list_partner(db: Session, partner: User) -> list[Review]:
    hotel_id = _partner_hotel_id(db, partner)
    return list(db.scalars(select(Review).outerjoin(ReviewChallenge).where(Review.hotel_id == hotel_id, or_(Review.moderation_status == ReviewModerationStatus.PUBLISHED, ReviewChallenge.id.is_not(None))).options(*_options()).order_by(Review.created_at.desc())))


def _partner_review(db: Session, partner: User, review_id: int, *, lock: bool = False) -> Review:
    hotel_id = _partner_hotel_id(db, partner)
    query = select(Review).where(Review.id == review_id, Review.hotel_id == hotel_id).options(*_options())
    review = db.scalar(query.with_for_update() if lock else query)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review


def respond(db: Session, partner: User, review_id: int, response_text: str) -> Review:
    review = _partner_review(db, partner, review_id, lock=True)
    if review.moderation_status != ReviewModerationStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a published review can receive a public response")
    if review.hotel_response is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This review already has a hotel response")
    review.hotel_response = ReviewResponse(response_text=response_text.strip(), responded_by_user_id=partner.id)
    db.commit()
    return _partner_review(db, partner, review_id)


def challenge(db: Session, partner: User, review_id: int, data: ReviewChallengeCreate) -> Review:
    review = _partner_review(db, partner, review_id, lock=True)
    if review.moderation_status != ReviewModerationStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a published review can be challenged")
    if review.challenge is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This review already has a challenge")
    review.challenge = ReviewChallenge(reason=data.reason, details=data.details.strip(), status=ReviewChallengeStatus.OPEN, challenged_by_user_id=partner.id)
    review.moderation_events.append(ReviewModerationEvent(old_status=review.moderation_status, new_status=review.moderation_status, note=f"Hotel challenge opened: {data.reason.value}", actor_user_id=partner.id))
    notification_service.create(db, recipient_user_id=review.customer_id, event_type=NotificationEventType.REVIEW_CHALLENGED, dedupe_key=f"REVIEW_CHALLENGED:{review.id}", title="Review challenged", body="The hotel challenged your review. Maharashtra Tourist Places will review the evidence.", data={"review_id": review.id, "booking_id": review.booking_id, "hotel_id": review.hotel_id})
    db.commit()
    return _partner_review(db, partner, review_id)


def list_admin_queue(db: Session) -> list[Review]:
    return list(db.scalars(select(Review).outerjoin(ReviewChallenge).where(or_(Review.moderation_status == ReviewModerationStatus.PENDING_REVIEW, ReviewChallenge.status == ReviewChallengeStatus.OPEN)).options(*_options()).order_by(Review.created_at.asc())))


def moderate(db: Session, admin: User, review_id: int, action: ModerationAction, note: str) -> Review:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    review = db.scalar(select(Review).where(Review.id == review_id).options(*_options()).with_for_update())
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    has_open_challenge = review.challenge is not None and review.challenge.status == ReviewChallengeStatus.OPEN
    if review.moderation_status != ReviewModerationStatus.PENDING_REVIEW and not has_open_challenge:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review is not awaiting moderation")
    old = review.moderation_status
    review.moderation_status = ReviewModerationStatus.PUBLISHED if action == ModerationAction.PUBLISH else ReviewModerationStatus.REJECTED
    review.moderated_by_user_id = admin.id
    review.moderated_at = datetime.now(timezone.utc)
    review.moderation_events.append(ReviewModerationEvent(old_status=old, new_status=review.moderation_status, note=note.strip(), actor_user_id=admin.id))
    if has_open_challenge:
        review.challenge.status = ReviewChallengeStatus.DISMISSED if action == ModerationAction.PUBLISH else ReviewChallengeStatus.UPHELD
        review.challenge.resolved_by_user_id = admin.id
        review.challenge.resolution_note = note.strip()
        review.challenge.resolved_at = review.moderated_at
    audit_service.record(db, actor=admin, action="REVIEW_MODERATED", target_type="REVIEW", target_id=review.id, reason=note, previous_value={"moderation_status": old.value, "challenge_status": ReviewChallengeStatus.OPEN.value if has_open_challenge else None}, new_value={"moderation_status": review.moderation_status.value, "challenge_status": review.challenge.status.value if has_open_challenge else None})
    db.commit()
    return db.scalar(select(Review).where(Review.id == review.id).options(*_options()))
