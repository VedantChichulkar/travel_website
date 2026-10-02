"""Resolution workflow for verified funds whose booking confirmation failed."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, Payment, PaymentReconciliationStatus, PaymentStatus
from app.models.communication import NotificationEventType
from app.models.user import User
from app.services import audit_service, inventory_service, notification_service, payment_provider


logger = logging.getLogger(__name__)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _mark_failure(db: Session, payment_id: int, reason: str, *, permanent: bool, ambiguous: bool = False) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    now = datetime.now(timezone.utc)
    payment.reconciliation_attempts += 1
    payment.reconciliation_last_attempt_at = now
    payment.failure_reason = reason[:255]
    payment.reconciliation_reason = reason
    if ambiguous:
        payment.reconciliation_status = PaymentReconciliationStatus.MANUAL_REVIEW
        payment.reconciliation_next_retry_at = None
    elif permanent or payment.reconciliation_attempts >= settings.PAYMENT_RECONCILIATION_MAX_ATTEMPTS:
        payment.reconciliation_status = PaymentReconciliationStatus.REFUND_REQUIRED
        payment.reconciliation_next_retry_at = None
    else:
        delay = settings.PAYMENT_RECONCILIATION_BACKOFF_MINUTES * (2 ** (payment.reconciliation_attempts - 1))
        payment.reconciliation_status = PaymentReconciliationStatus.CONFIRMATION_REQUIRED
        payment.reconciliation_next_retry_at = now + timedelta(minutes=delay)
    booking = db.get(Booking, payment.booking_id)
    if booking:
        notification_service.for_booking(
            db, booking, event_type=NotificationEventType.PAYMENT_RECONCILIATION,
            event_key=f"{payment.id}:{payment.reconciliation_status.value}:{payment.reconciliation_attempts}",
            title="Payment reconciliation update",
            body=f"Payment for booking {booking.booking_reference} is {payment.reconciliation_status.value.lower().replace('_', ' ')}.",
            include_hotel=False,
        )
    db.commit(); db.refresh(payment)
    if payment.reconciliation_status == PaymentReconciliationStatus.REFUND_REQUIRED:
        from app.services import refund_execution_service
        try:
            refund_execution_service.ensure_payment_reconciliation_refund(db, payment.id)
        except HTTPException:
            db.rollback()
    logger.warning("Payment reconciliation unresolved", extra={"payment_id": payment.id, "booking_id": payment.booking_id, "reconciliation_status": payment.reconciliation_status.value, "attempt": payment.reconciliation_attempts})
    return payment


def attempt_confirmation(db: Session, payment_id: int, *, admin: User | None = None, reason: str = "Automatic paid-booking reconciliation") -> Payment:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.status != PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only verified paid payments can be reconciled")
    previous_reconciliation_status = payment.reconciliation_status
    booking = db.scalar(select(Booking).where(Booking.id == payment.booking_id).with_for_update())
    if booking is None:
        db.rollback()
        return _mark_failure(db, payment_id, "Paid payment has no booking record", permanent=False, ambiguous=True)
    if booking.status == BookingStatus.CONFIRMED:
        payment.reconciliation_status = PaymentReconciliationStatus.RESOLVED
        payment.reconciliation_next_retry_at = None
        payment.reconciliation_resolved_at = datetime.now(timezone.utc)
        payment.reconciliation_resolved_by = admin.id if admin else None
        payment.reconciliation_reason = reason
        notification_service.for_booking(db, booking, event_type=NotificationEventType.PAYMENT_RECONCILIATION, event_key=f"{payment.id}:resolved", title="Payment reconciliation completed", body=f"Payment reconciliation for booking {booking.booking_reference} is complete.", include_hotel=False)
        db.commit(); db.refresh(payment)
        return payment
    if booking.status != BookingStatus.PAYMENT_PENDING:
        db.rollback()
        return _mark_failure(db, payment_id, f"Paid booking is in ambiguous state {booking.status.value}", permanent=False, ambiguous=True)
    try:
        room = booking.room_type or db.get(inventory_service.RoomType, booking.room_type_id)
        if room is None:
            raise RuntimeError("Booking room type is missing")
        inventory_service.finalize_hold_as_confirmed(db, hold_token=booking.hold_token or "", user_id=booking.user_id, room=room, check_in=booking.check_in, check_out=booking.check_out, rooms=booking.rooms)
        booking.status = BookingStatus.CONFIRMED
        booking.payment_status = PaymentStatus.PAID
        booking.operation_qr_token = booking.operation_qr_token or secrets.token_urlsafe(24)
        booking.status_history.append(BookingStatusHistory(old_status=BookingStatus.PAYMENT_PENDING, new_status=BookingStatus.CONFIRMED, changed_by_user_id=admin.id if admin else None, note="Confirmed from verified payment reconciliation"))
        payment.reconciliation_status = PaymentReconciliationStatus.RESOLVED
        payment.reconciliation_attempts += 1
        payment.reconciliation_last_attempt_at = datetime.now(timezone.utc)
        payment.reconciliation_next_retry_at = None
        payment.reconciliation_resolved_at = datetime.now(timezone.utc)
        payment.reconciliation_resolved_by = admin.id if admin else None
        payment.reconciliation_reason = reason
        payment.failure_reason = None
        payment.receipt_status = "AVAILABLE"
        payment.receipt_requested_at = payment.receipt_requested_at or datetime.now(timezone.utc)
        notification_service.for_booking(db, booking, event_type=NotificationEventType.PAYMENT_RECONCILIATION, event_key=f"{payment.id}:resolved", title="Payment reconciliation completed", body=f"Payment reconciliation for booking {booking.booking_reference} is complete.", include_hotel=False)
        notification_service.for_booking(db, booking, event_type=NotificationEventType.BOOKING_CONFIRMATION, event_key=f"reconciliation:{payment.id}", title="Booking confirmed", body=f"Booking {booking.booking_reference} is confirmed.")
        if admin:
            audit_service.record(db, actor=admin, action="PAYMENT_RECONCILIATION_CONFIRMED", target_type="PAYMENT", target_id=payment.id, reason=reason, previous_value={"reconciliation_status": previous_reconciliation_status.value}, new_value={"reconciliation_status": PaymentReconciliationStatus.RESOLVED.value, "booking_status": BookingStatus.CONFIRMED.value})
        db.commit(); db.refresh(payment)
        logger.info("Payment reconciliation resolved", extra={"payment_id": payment.id, "booking_id": booking.id, "outcome": "CONFIRMED"})
        return payment
    except HTTPException as exc:
        detail = str(exc.detail)
        db.rollback()
        permanent = any(token in detail.lower() for token in ("expired", "no longer active", "not found"))
        return _mark_failure(db, payment_id, detail, permanent=permanent, ambiguous=not permanent and "safely" in detail.lower())
    except Exception:
        logger.exception("Payment reconciliation attempt failed", extra={"payment_id": payment_id})
        db.rollback()
        return _mark_failure(db, payment_id, "Unexpected confirmation failure; manual investigation may be required", permanent=False)


def set_outcome(db: Session, payment_id: int, admin: User, outcome: PaymentReconciliationStatus, reason: str) -> Payment:
    if outcome not in (PaymentReconciliationStatus.REFUND_REQUIRED, PaymentReconciliationStatus.MANUAL_REVIEW):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported reconciliation outcome")
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.status != PaymentStatus.PAID or payment.reconciliation_status == PaymentReconciliationStatus.RESOLVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment is not eligible for this reconciliation outcome")
    previous = payment.reconciliation_status
    payment.reconciliation_status = outcome
    payment.reconciliation_next_retry_at = None
    payment.reconciliation_reason = reason.strip()
    payment.reconciliation_resolved_by = admin.id
    booking = db.get(Booking, payment.booking_id)
    if booking:
        notification_service.for_booking(db, booking, event_type=NotificationEventType.PAYMENT_RECONCILIATION, event_key=f"{payment.id}:{outcome.value}", title="Payment reconciliation update", body=f"Payment for booking {booking.booking_reference} requires support review.", include_hotel=False)
    audit_service.record(db, actor=admin, action="PAYMENT_RECONCILIATION_CLASSIFIED", target_type="PAYMENT", target_id=payment.id, reason=reason, previous_value={"reconciliation_status": previous.value}, new_value={"reconciliation_status": outcome.value})
    db.commit(); db.refresh(payment)
    if outcome == PaymentReconciliationStatus.REFUND_REQUIRED:
        from app.services import refund_execution_service
        refund_execution_service.ensure_payment_reconciliation_refund(db, payment.id)
    logger.info("Payment reconciliation classified", extra={"payment_id": payment.id, "booking_id": payment.booking_id, "outcome": outcome.value})
    return payment


def run_due(db: Session, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    pending_ids: list[int] = []
    if settings.PAYMENT_PROVIDER == "RAZORPAY" and settings.PAYMENT_MODE in ("test", "live"):
        pending_ids = list(db.scalars(select(Payment.id).where(
            Payment.status == PaymentStatus.PENDING,
            Payment.provider == settings.PAYMENT_PROVIDER,
            Payment.created_at <= current - timedelta(minutes=2),
        ).order_by(Payment.created_at).limit(50)))
    for payment_id in pending_ids:
        payment = db.get(Payment, payment_id)
        if payment is None:
            continue
        try:
            evidence = payment_provider.configured_provider().fetch_captured_order_payment(payment.provider_order_id)
            if evidence and evidence.provider_order_id == payment.provider_order_id:
                from app.services import payment_service
                payment_service.process_webhook(db, payment.provider, f"reconcile:{evidence.provider_payment_id}", payment.provider_order_id, "succeeded", evidence.amount, evidence.currency, evidence.provider_payment_id)
        except HTTPException:
            db.rollback()
            logger.warning("Pending payment provider lookup unavailable", extra={"payment_id": payment_id, "provider": payment.provider})
    ids = list(db.scalars(select(Payment.id).where(
        Payment.status == PaymentStatus.PAID,
        Payment.reconciliation_status == PaymentReconciliationStatus.CONFIRMATION_REQUIRED,
        Payment.reconciliation_attempts < settings.PAYMENT_RECONCILIATION_MAX_ATTEMPTS,
        Payment.reconciliation_next_retry_at.is_not(None),
        Payment.reconciliation_next_retry_at <= current,
    ).order_by(Payment.reconciliation_next_retry_at).limit(50)))
    for payment_id in ids:
        attempt_confirmation(db, payment_id)
    return len(pending_ids) + len(ids)
