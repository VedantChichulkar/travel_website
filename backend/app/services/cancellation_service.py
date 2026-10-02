"""Cancellation and refund decisions based solely on the booking-time policy snapshot."""

import re
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.booking import Booking, BookingStatus, BookingStatusHistory, Cancellation, CancellationStatus, CancellationType, Payment, PaymentStatus, Refund, RefundStatus, SettlementImpactStatus
from app.models.user import User, UserRole
from app.services import inventory_service, refund_execution_service
from app.services import notification_service
from app.models.communication import NotificationEventType
from app.services import audit_service


MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _policy_decision(booking: Booking, now: datetime) -> tuple[Decimal, bool, str]:
    """Return (refund, manual_review, explanation) without reading HotelPolicy."""
    policy = str(booking.policy_snapshot.get("cancellation_policy") or "").strip()
    if not policy:
        return Decimal("0.00"), True, "No cancellation terms were captured with this booking"
    normalized = " ".join(policy.lower().split())
    if "non-refundable" in normalized or "non refundable" in normalized:
        return Decimal("0.00"), False, "Captured policy marks this booking as non-refundable"
    cutoff = re.search(r"free cancellation (?:until|up to) (\d+) hours? before", normalized)
    if not cutoff:
        return Decimal("0.00"), True, "Captured cancellation terms require manual review"
    hours = int(cutoff.group(1))
    arrival = datetime.combine(booking.check_in, time.min, tzinfo=timezone.utc)
    if now <= arrival - timedelta(hours=hours):
        return booking.total_amount, False, f"Free cancellation before the captured {hours}-hour cutoff"
    if re.search(r"charged? (?:one|1) night", normalized):
        nightly = booking.price_snapshot.get("nightly_prices") or []
        first_night = Decimal(str(nightly[0].get("amount", "0"))) if nightly else Decimal("0.00")
        return max(Decimal("0.00"), _money(booking.total_amount - first_night)), False, "Captured policy charges one night after the free-cancellation cutoff"
    return Decimal("0.00"), True, "Captured policy does not define the post-cutoff refund"


def _customer_booking(db: Session, booking_id: int, user: User) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.room_type), selectinload(Booking.payments), selectinload(Booking.cancellation)))
    if booking is None or booking.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def _paid_payment(booking: Booking) -> Payment:
    payment = next((item for item in reversed(booking.payments) if item.status == PaymentStatus.PAID), None)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No verified payment is available to refund")
    return payment


def _create_refund(db: Session, cancellation: Cancellation, payment: Payment, amount: Decimal, *, manual: bool = False) -> Refund | None:
    if manual:
        # No financial instruction is sent until an administrator resolves the
        # ambiguous captured terms. A zero amount is not a refund record.
        cancellation.status = CancellationStatus.MANUAL_REVIEW
        return None
    if amount <= 0:
        cancellation.status = CancellationStatus.COMPLETED
        cancellation.refunded_amount = Decimal("0.00")
        return None
    return refund_execution_service.create_instruction(db, cancellation, payment, amount)


def record_no_show_implication(
    db: Session,
    booking: Booking,
    *,
    decided_by_user_id: int | None,
    system_generated: bool,
) -> Cancellation:
    """Record the financial review outcome without duplicating refund execution.

    The decision reads only the immutable booking policy snapshot. Ambiguous terms
    enter the existing manual-refund workflow; no provider refund is created here.
    """
    existing = db.scalar(select(Cancellation).where(Cancellation.booking_id == booking.id).with_for_update())
    if existing is not None:
        return existing

    policy = str(booking.policy_snapshot.get("cancellation_policy") or "").strip()
    normalized = " ".join(policy.lower().split())
    has_no_show_term = "no-show" in normalized or "no show" in normalized
    clearly_non_refundable = has_no_show_term and any(
        marker in normalized
        for marker in ("non-refundable", "non refundable", "no refund", "charged in full", "full booking amount")
    )
    if clearly_non_refundable:
        decision = "Booking-time policy explicitly makes no-shows non-refundable"
        cancellation_status = CancellationStatus.COMPLETED
        manual_review = False
    else:
        decision = "Booking-time policy requires manual review for no-show financial implications"
        cancellation_status = CancellationStatus.MANUAL_REVIEW
        manual_review = True

    cancellation = Cancellation(
        booking=booking,
        cancellation_type=CancellationType.NO_SHOW,
        status=cancellation_status,
        reason="Automatic no-show fallback" if system_generated else "Hotel-reported no-show",
        policy_snapshot={**booking.policy_snapshot, "refund_decision": decision},
        refundable_amount=Decimal("0.00"),
        refunded_amount=Decimal("0.00"),
        requires_manual_review=manual_review,
        decided_by_user_id=decided_by_user_id,
    )
    db.add(cancellation)
    return cancellation


def request_customer_cancellation(db: Session, user: User, booking_id: int, reason: str) -> Cancellation:
    if user.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customers can request cancellations")
    booking = _customer_booking(db, booking_id, user)
    locked = db.scalar(select(Booking).where(Booking.id == booking.id).with_for_update())
    if locked is None or locked.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only confirmed bookings can be cancelled")
    if db.scalar(select(Cancellation).where(Cancellation.booking_id == locked.id).with_for_update()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A cancellation already exists for this booking")
    payment = _paid_payment(booking)
    refundable, manual, decision = _policy_decision(locked, datetime.now(timezone.utc))
    cancellation = Cancellation(booking_id=locked.id, cancellation_type=CancellationType.CUSTOMER, reason=reason, policy_snapshot={**locked.policy_snapshot, "refund_decision": decision}, refundable_amount=refundable, requires_manual_review=manual, decided_by_user_id=None)
    db.add(cancellation); db.flush()
    inventory_service.release_confirmed_inventory(db, room=locked.room_type or db.get(inventory_service.RoomType, locked.room_type_id), check_in=locked.check_in, check_out=locked.check_out, rooms=locked.rooms)
    old_status = locked.status
    locked.status = BookingStatus.CANCELLED if refundable == 0 and not manual else BookingStatus.REFUND_PENDING
    locked.payment_status = PaymentStatus.REFUND_PENDING if refundable > 0 else PaymentStatus.PAID
    locked.status_history.append(BookingStatusHistory(old_status=old_status, new_status=locked.status, changed_by_user_id=user.id, note=f"Customer cancellation requested: {decision}"))
    refund = _create_refund(db, cancellation, payment, refundable, manual=manual)
    notification_service.for_booking(db, locked, event_type=NotificationEventType.CANCELLATION, event_key=str(cancellation.id), title="Cancellation recorded", body=f"Cancellation for booking {locked.booking_reference} was recorded.")
    if refundable > 0 and not manual:
        notification_service.for_booking(db, locked, event_type=NotificationEventType.REFUND_INITIATED, event_key=str(cancellation.id), title="Refund initiated", body=f"A refund for booking {locked.booking_reference} is pending.")
    db.commit(); db.refresh(cancellation)
    if refund is not None:
        refund_execution_service.submit_refund(db, refund.id)
    return get_cancellation(db, locked.id, user)


def create_hotel_caused_cancellation(db: Session, admin: User, booking_id: int, reason: str) -> Cancellation:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Maharashtra Tourist Places administrators can create hotel-caused cancellations")
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.room_type), selectinload(Booking.payments)).with_for_update())
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.status != BookingStatus.CONFIRMED or db.scalar(select(Cancellation).where(Cancellation.booking_id == booking.id).with_for_update()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking cannot be cancelled")
    payment = _paid_payment(booking)
    cancellation = Cancellation(booking_id=booking.id, cancellation_type=CancellationType.HOTEL_CAUSED, reason=reason, policy_snapshot={**booking.policy_snapshot, "refund_decision": "Hotel-caused exception: full refund"}, refundable_amount=booking.total_amount, requires_manual_review=False, decided_by_user_id=admin.id)
    db.add(cancellation); db.flush()
    inventory_service.release_confirmed_inventory(db, room=booking.room_type or db.get(inventory_service.RoomType, booking.room_type_id), check_in=booking.check_in, check_out=booking.check_out, rooms=booking.rooms)
    booking.status = BookingStatus.REFUND_PENDING; booking.payment_status = PaymentStatus.REFUND_PENDING
    booking.status_history.append(BookingStatusHistory(old_status=BookingStatus.CONFIRMED, new_status=BookingStatus.REFUND_PENDING, changed_by_user_id=admin.id, note="Hotel-caused cancellation; full refund initiated"))
    refund = _create_refund(db, cancellation, payment, booking.total_amount)
    notification_service.for_booking(db, booking, event_type=NotificationEventType.CANCELLATION, event_key=str(cancellation.id), title="Booking cancelled", body=f"Booking {booking.booking_reference} was cancelled due to a hotel exception.")
    notification_service.for_booking(db, booking, event_type=NotificationEventType.REFUND_INITIATED, event_key=str(cancellation.id), title="Refund initiated", body=f"A full refund for booking {booking.booking_reference} is pending.")
    audit_service.record(db, actor=admin, action="HOTEL_CAUSED_CANCELLATION", target_type="BOOKING", target_id=booking.id, reason=reason, previous_value={"status": BookingStatus.CONFIRMED.value}, new_value={"status": booking.status.value, "refund_amount": str(booking.total_amount)})
    db.commit(); db.refresh(cancellation)
    refund_execution_service.submit_refund(db, refund.id, admin=admin, reason=reason)
    return get_cancellation(db, booking.id, admin)


def get_cancellation(db: Session, booking_id: int, user: User) -> Cancellation | None:
    booking = _customer_booking(db, booking_id, user) if user.role != UserRole.ADMIN else db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return db.scalar(select(Cancellation).where(Cancellation.booking_id == booking.id).options(selectinload(Cancellation.refunds)))


def settle_refund(db: Session, admin: User, refund_id: int, outcome: RefundStatus, processed_amount: Decimal | None = None, failure_reason: str | None = None, reason: str | None = None) -> Refund:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Maharashtra Tourist Places administrators can settle refunds")
    if outcome in (RefundStatus.SUCCEEDED, RefundStatus.PARTIAL):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Refund completion can only come from verified provider evidence",
        )
    if outcome != RefundStatus.MANUAL_REVIEW:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Admin may only place a refund into manual review; provider evidence controls execution state")
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).options(selectinload(Refund.cancellation).selectinload(Cancellation.booking)).with_for_update())
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    if refund.status not in (RefundStatus.PENDING, RefundStatus.PROCESSING, RefundStatus.RETRY_REQUIRED, RefundStatus.RECONCILIATION_REQUIRED, RefundStatus.FAILED, RefundStatus.MANUAL_REVIEW):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refund has already been settled")
    amount = processed_amount if processed_amount is not None else refund.amount
    if amount < 0 or amount > refund.amount:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Processed amount is outside the approved refund")
    old_status = refund.status
    refund.status = outcome; refund.executed_by_user_id = admin.id; refund.failure_reason = failure_reason[:255] if failure_reason else None
    refund.settlement_impact_status = SettlementImpactStatus.PENDING
    cancellation = refund.cancellation
    cancellation.status = CancellationStatus.MANUAL_REVIEW; cancellation.requires_manual_review = True; cancellation.booking.status = BookingStatus.REFUND_PENDING
    cancellation.booking.status_history.append(BookingStatusHistory(old_status=BookingStatus.REFUND_PENDING, new_status=cancellation.booking.status, changed_by_user_id=admin.id, note=f"Refund {outcome.value.lower()}"))
    notification_service.for_booking(db, cancellation.booking, event_type=NotificationEventType.REFUND_REQUIRES_REVIEW, event_key=f"{refund.id}:{outcome.value}", title="Refund requires review", body=f"Refund for booking {cancellation.booking.booking_reference} requires support review.", include_hotel=False)
    audit_service.record(db, actor=admin, action="REFUND_SETTLED", target_type="REFUND", target_id=refund.id, reason=reason or failure_reason or "Refund outcome recorded", previous_value={"status": old_status.value}, new_value={"status": outcome.value, "processed_amount": str(amount)})
    db.commit(); db.refresh(refund)
    return refund


def approve_manual_refund(db: Session, admin: User, cancellation_id: int, approved_amount: Decimal, note: str) -> Cancellation:
    if admin.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Maharashtra Tourist Places administrators can decide manual refunds")
    cancellation = db.scalar(select(Cancellation).where(Cancellation.id == cancellation_id).options(selectinload(Cancellation.booking).selectinload(Booking.payments)).with_for_update())
    if cancellation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cancellation not found")
    if cancellation.status != CancellationStatus.MANUAL_REVIEW or cancellation.refunds:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Manual refund has already been decided")
    booking = cancellation.booking
    if approved_amount > booking.total_amount:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Approved amount exceeds the original booking total")
    cancellation.refundable_amount = approved_amount; cancellation.decided_by_user_id = admin.id; cancellation.policy_snapshot = {**cancellation.policy_snapshot, "manual_refund_decision": note}
    payment = _paid_payment(booking)
    refund = _create_refund(db, cancellation, payment, approved_amount)
    if approved_amount == 0:
        booking.status = BookingStatus.CANCELLED
    else:
        booking.status = BookingStatus.REFUND_PENDING; booking.payment_status = PaymentStatus.REFUND_PENDING
    booking.status_history.append(BookingStatusHistory(old_status=BookingStatus.REFUND_PENDING, new_status=booking.status, changed_by_user_id=admin.id, note="Manual refund decision recorded"))
    audit_service.record(db, actor=admin, action="MANUAL_REFUND_DECIDED", target_type="CANCELLATION", target_id=cancellation.id, reason=note, previous_value={"status": CancellationStatus.MANUAL_REVIEW.value}, new_value={"status": cancellation.status.value, "approved_amount": str(approved_amount)})
    db.commit(); db.refresh(cancellation)
    if refund is not None:
        refund_execution_service.submit_refund(db, refund.id, admin=admin, reason=note)
    return get_cancellation(db, booking.id, admin)
