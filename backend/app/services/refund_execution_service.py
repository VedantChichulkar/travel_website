"""Provider-authoritative refund execution and reconciliation."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, Cancellation, CancellationStatus, CancellationType, Payment, PaymentReconciliationStatus, PaymentStatus, PaymentWebhookEvent, Refund, RefundStatus, SettlementImpactStatus
from app.models.communication import NotificationEventType
from app.models.user import User
from app.models.hotel import Hotel
from app.models.hotel_verification import HotelVerification
from app.models.safari import SafariRequest
from app.services import audit_service, notification_service, payment_provider, settlement_service
from app.schemas.booking import AdminRefundDetail, RefundResponse


logger = logging.getLogger(__name__)


def _notify_refund(db: Session, refund: Refund, *, event_type: NotificationEventType, key: str, title: str, body: str) -> None:
    if refund.cancellation is not None:
        notification_service.for_booking(db, refund.cancellation.booking, event_type=event_type, event_key=key, title=title, body=body, include_hotel=False)
        return
    if refund.verification_id is not None:
        verification = db.get(HotelVerification, refund.verification_id)
        hotel = db.get(Hotel, verification.hotel_id) if verification else None
        if hotel and hotel.partner_id:
            notification_service.create(
                db,
                recipient_user_id=hotel.partner_id,
                event_type=event_type,
                dedupe_key=f"{event_type.value}:{key}",
                title=title,
                body=body,
                data={"hotel_id": hotel.id, "verification_id": verification.id, "refund_id": refund.id},
            )
        return
    if refund.safari_request_id is not None:
        safari_request = db.get(SafariRequest, refund.safari_request_id)
        if safari_request:
            notification_service.create(
                db, recipient_user_id=safari_request.customer_id, event_type=event_type,
                dedupe_key=f"{event_type.value}:{key}", title=title, body=body,
                data={"safari_request_id": safari_request.id, "refund_id": refund.id},
            )


def create_instruction(db: Session, cancellation: Cancellation, payment: Payment, amount: Decimal, *, idempotency_key: str | None = None) -> Refund:
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Refund amount must be positive")
    existing = db.scalar(select(Refund).where(Refund.cancellation_id == cancellation.id, Refund.payment_id == payment.id).with_for_update())
    if existing is not None:
        if existing.amount != amount or existing.currency != payment.currency:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Existing refund instruction does not match the approved financials")
        return existing
    committed = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.payment_id == payment.id)) or Decimal("0")
    if amount + committed > payment.amount:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Refund amount exceeds the remaining captured payment")
    refund = Refund(
        cancellation_id=cancellation.id,
        payment_id=payment.id,
        amount=amount,
        currency=payment.currency,
        provider=payment.provider,
        idempotency_key=idempotency_key or f"refund-{uuid.uuid4().hex}",
        status=RefundStatus.PENDING,
        settlement_impact_status=SettlementImpactStatus.PENDING,
    )
    cancellation.status = CancellationStatus.REFUND_PENDING
    db.add(refund); db.flush()
    return refund


def create_verification_instruction(db: Session, verification: HotelVerification, payment: Payment) -> Refund:
    existing = db.scalar(select(Refund).where(Refund.verification_id == verification.id, Refund.payment_id == payment.id).with_for_update())
    if existing is not None:
        return existing
    committed = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.payment_id == payment.id)) or Decimal("0")
    if committed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A refund already exists for this verification payment")
    refund = Refund(
        cancellation_id=None,
        verification_id=verification.id,
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        provider=payment.provider,
        idempotency_key=f"verification-rejection-{verification.id}-{payment.id}",
        status=RefundStatus.PENDING,
        settlement_impact_status=SettlementImpactStatus.NOT_APPLICABLE,
    )
    payment.status = PaymentStatus.REFUND_PENDING
    db.add(refund)
    db.flush()
    _notify_refund(db, refund, event_type=NotificationEventType.REFUND_INITIATED, key=f"verification-refund:{refund.id}:initiated", title="Verification fee refund initiated", body="Your full verification processing fee refund has been initiated through the original payment path.")
    return refund


def create_safari_instruction(db: Session, safari_request: SafariRequest, payment: Payment) -> Refund:
    if payment.safari_request_id != safari_request.id or payment.status != PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Safari payment is not eligible for a refund")
    existing = db.scalar(select(Refund).where(Refund.safari_request_id == safari_request.id, Refund.payment_id == payment.id).with_for_update())
    if existing is not None:
        return existing
    committed = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.payment_id == payment.id)) or Decimal("0")
    if committed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A refund already exists for this safari payment")
    refund = Refund(cancellation_id=None, verification_id=None, safari_request_id=safari_request.id,
        payment_id=payment.id, amount=payment.amount, currency=payment.currency, provider=payment.provider,
        idempotency_key=f"safari-booking-failure-{safari_request.id}-{payment.id}", status=RefundStatus.PENDING,
        settlement_impact_status=SettlementImpactStatus.NOT_APPLICABLE)
    payment.status = PaymentStatus.REFUND_PENDING
    db.add(refund); db.flush()
    _notify_refund(db, refund, event_type=NotificationEventType.REFUND_INITIATED, key=f"safari-refund:{refund.id}:initiated", title="Safari payment refund initiated", body="A full refund was initiated after the external safari booking could not be completed.")
    return refund


def _schedule(refund: Refund, *, ambiguous: bool, reason: str) -> None:
    refund.execution_attempts += 1
    refund.last_checked_at = datetime.now(timezone.utc)
    refund.failure_reason = reason[:255]
    refund.reconciliation_reason = reason
    if ambiguous or refund.execution_attempts >= settings.REFUND_RECONCILIATION_MAX_ATTEMPTS:
        refund.status = RefundStatus.RECONCILIATION_REQUIRED
        refund.next_retry_at = None
    else:
        refund.status = RefundStatus.RETRY_REQUIRED
        delay = settings.REFUND_RECONCILIATION_BACKOFF_MINUTES * (2 ** max(0, refund.execution_attempts - 1))
        refund.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay)


def submit_refund(db: Session, refund_id: int, *, admin: User | None = None, reason: str = "Submit approved refund to provider") -> Refund:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).options(selectinload(Refund.payment), selectinload(Refund.cancellation).selectinload(Cancellation.booking)).with_for_update())
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    if refund.status in (RefundStatus.SUCCEEDED, RefundStatus.PARTIAL):
        return refund
    if refund.provider_refund_id:
        return reconcile_refund(db, refund.id, admin=admin, reason=reason)
    if not refund.payment.provider_payment_id:
        _schedule(refund, ambiguous=True, reason="Verified provider payment reference is missing")
        _notify_refund(db, refund, event_type=NotificationEventType.REFUND_REQUIRES_REVIEW, key=f"refund:{refund.id}:missing-payment-reference", title="Refund requires review", body="Your refund requires support review.")
        db.commit(); db.refresh(refund)
        return refund
    provider = payment_provider.configured_provider()
    try:
        instruction = provider.create_refund(provider_payment_id=refund.payment.provider_payment_id or "", amount=refund.amount, currency=refund.currency, idempotency_key=refund.idempotency_key)
        if instruction.amount != refund.amount or instruction.currency != refund.currency or instruction.status.lower() not in ("accepted", "pending", "processing"):
            _schedule(refund, ambiguous=True, reason="Provider refund acceptance did not match approved financials")
            _notify_refund(db, refund, event_type=NotificationEventType.REFUND_REQUIRES_REVIEW, key=f"refund:{refund.id}:acceptance-mismatch", title="Refund requires review", body="Your refund requires support review.")
        else:
            refund.provider_refund_id = instruction.provider_refund_id
            refund.provider_status = instruction.status
            refund.status = RefundStatus.PROCESSING
            refund.execution_attempts += 1
            refund.provider_accepted_at = datetime.now(timezone.utc)
            refund.last_checked_at = refund.provider_accepted_at
            refund.next_retry_at = refund.provider_accepted_at + timedelta(minutes=settings.REFUND_RECONCILIATION_BACKOFF_MINUTES)
            refund.failure_reason = None
            _notify_refund(db, refund, event_type=NotificationEventType.REFUND_PROCESSING, key=f"refund:{refund.id}:processing", title="Refund processing", body="Your refund was accepted for processing.")
        if admin:
            audit_service.record(db, actor=admin, action="REFUND_SUBMITTED", target_type="REFUND", target_id=refund.id, reason=reason, previous_value={"status": RefundStatus.PENDING.value}, new_value={"status": refund.status.value, "provider_reference_recorded": bool(refund.provider_refund_id)})
        db.commit(); db.refresh(refund)
        logger.info("Refund instruction submitted", extra={"refund_id": refund.id, "payment_id": refund.payment_id, "status": refund.status.value})
        return refund
    except HTTPException:
        db.rollback()
        refund = db.get(Refund, refund_id)
        _schedule(refund, ambiguous=False, reason="Refund provider unavailable")
        db.commit(); db.refresh(refund)
        return refund
    except Exception:
        logger.exception("Refund instruction outcome is uncertain", extra={"refund_id": refund_id})
        db.rollback()
        refund = db.get(Refund, refund_id)
        _schedule(refund, ambiguous=True, reason="Provider refund request outcome is unknown")
        db.commit(); db.refresh(refund)
        return refund


def _finalize(db: Session, refund: Refund) -> Refund:
    if refund.status == RefundStatus.SUCCEEDED:
        return refund
    now = datetime.now(timezone.utc)
    refund.status = RefundStatus.SUCCEEDED
    refund.provider_status = "completed"
    refund.completed_at = now
    refund.last_checked_at = now
    refund.next_retry_at = None
    refund.failure_reason = None
    cancellation = refund.cancellation
    if cancellation is None:
        refund.payment.status = PaymentStatus.REFUNDED
        refund.settlement_impact_status = SettlementImpactStatus.NOT_APPLICABLE
        is_safari = refund.safari_request_id is not None
        _notify_refund(db, refund, event_type=NotificationEventType.REFUND_COMPLETED, key=f"refund:{refund.id}:completed", title="Safari payment refund completed" if is_safari else "Verification fee refund completed", body="Your full safari payment refund was completed." if is_safari else "Your full verification processing fee refund was completed.")
        logger.info("Provider-confirmed non-booking refund completed", extra={"refund_id": refund.id, "payment_id": refund.payment_id})
        return refund
    succeeded = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0)).where(Refund.cancellation_id == cancellation.id, Refund.id != refund.id, Refund.status.in_((RefundStatus.SUCCEEDED, RefundStatus.PARTIAL)))) or Decimal("0")
    cancellation.refunded_amount = succeeded + refund.amount
    if cancellation.refunded_amount >= cancellation.refundable_amount:
        cancellation.status = CancellationStatus.COMPLETED
        cancellation.requires_manual_review = False
        old = cancellation.booking.status
        cancellation.booking.status = BookingStatus.REFUNDED
        if cancellation.refunded_amount >= refund.payment.amount:
            cancellation.booking.payment_status = PaymentStatus.REFUNDED
            refund.payment.status = PaymentStatus.REFUNDED
        cancellation.booking.status_history.append(BookingStatusHistory(old_status=old, new_status=BookingStatus.REFUNDED, note="Provider-confirmed refund completed"))
    if cancellation.cancellation_type == CancellationType.PAYMENT_RECONCILIATION:
        refund.payment.reconciliation_status = PaymentReconciliationStatus.RESOLVED
        refund.payment.reconciliation_resolved_at = now
    settlement_service.apply_completed_refund(db, refund)
    notification_service.for_booking(db, cancellation.booking, event_type=NotificationEventType.REFUND_COMPLETED, event_key=f"refund:{refund.id}:completed", title="Refund completed", body=f"The refund for booking {cancellation.booking.booking_reference} was completed.", include_hotel=False)
    logger.info("Provider-confirmed refund completed", extra={"refund_id": refund.id, "payment_id": refund.payment_id})
    return refund


def process_webhook(db: Session, provider: str, event_id: str, provider_refund_id: str, outcome: str, amount: Decimal, currency: str, failure_reason: str | None = None) -> Refund | None:
    existing = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider == provider, PaymentWebhookEvent.provider_event_id == event_id))
    if existing:
        return db.get(Refund, existing.refund_id) if existing.refund_id else None
    refund = db.scalar(select(Refund).where(Refund.provider == provider, Refund.provider_refund_id == provider_refund_id).options(selectinload(Refund.payment), selectinload(Refund.cancellation).selectinload(Cancellation.booking)).with_for_update())
    event = PaymentWebhookEvent(provider=provider, provider_event_id=event_id, payment_id=refund.payment_id if refund else None, refund_id=refund.id if refund else None)
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider == provider, PaymentWebhookEvent.provider_event_id == event_id))
        return db.get(Refund, duplicate.refund_id) if duplicate and duplicate.refund_id else None
    if refund is None:
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund instruction not found")
    if refund.amount != amount or refund.currency != currency:
        refund.status = RefundStatus.RECONCILIATION_REQUIRED
        refund.reconciliation_reason = "Provider refund callback financials did not match the approved instruction"
        refund.next_retry_at = None
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refund callback financials do not match")
    refund.provider_status = outcome
    refund.last_checked_at = datetime.now(timezone.utc)
    if outcome == "completed":
        _finalize(db, refund)
    elif outcome == "pending":
        refund.status = RefundStatus.PROCESSING
        refund.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=settings.REFUND_RECONCILIATION_BACKOFF_MINUTES)
    elif outcome == "failed":
        refund.status = RefundStatus.FAILED
        refund.failure_reason = (failure_reason or "Provider rejected the refund")[:255]
        refund.reconciliation_reason = refund.failure_reason
        refund.next_retry_at = None
        if refund.cancellation is not None:
            refund.cancellation.status = CancellationStatus.MANUAL_REVIEW
            refund.cancellation.requires_manual_review = True
        _notify_refund(db, refund, event_type=NotificationEventType.REFUND_FAILED, key=f"refund:{refund.id}:failed", title="Refund requires review", body="Your refund could not be completed automatically and is in reconciliation review.")
    else:
        refund.status = RefundStatus.RECONCILIATION_REQUIRED
        refund.reconciliation_reason = "Provider returned an unknown refund state"
        refund.next_retry_at = None
    db.commit(); db.refresh(refund)
    return refund


def reconcile_refund(db: Session, refund_id: int, *, admin: User | None = None, reason: str = "Reconcile provider refund state") -> Refund:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).options(selectinload(Refund.payment), selectinload(Refund.cancellation).selectinload(Cancellation.booking)).with_for_update())
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    if refund.status == RefundStatus.SUCCEEDED:
        return refund
    if not refund.provider_refund_id:
        return submit_refund(db, refund.id, admin=admin, reason=reason)
    try:
        provider_state = payment_provider.configured_provider().fetch_refund_status(refund.provider_refund_id).lower()
        refund.execution_attempts += 1
        refund.last_checked_at = datetime.now(timezone.utc)
        if provider_state == "completed":
            _finalize(db, refund)
        elif provider_state == "pending":
            refund.status = RefundStatus.PROCESSING
            refund.provider_status = provider_state
            refund.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=settings.REFUND_RECONCILIATION_BACKOFF_MINUTES)
        elif provider_state == "failed":
            refund.status = RefundStatus.FAILED
            refund.provider_status = provider_state
            refund.failure_reason = "Provider reports refund failed"
            refund.next_retry_at = None
            if refund.cancellation is not None:
                refund.cancellation.status = CancellationStatus.MANUAL_REVIEW
                refund.cancellation.requires_manual_review = True
            _notify_refund(db, refund, event_type=NotificationEventType.REFUND_FAILED, key=f"refund:{refund.id}:status-failed", title="Refund requires review", body="Your refund could not be completed automatically and is in reconciliation review.")
        else:
            _schedule(refund, ambiguous=True, reason="Provider refund state is unknown")
        if admin:
            audit_service.record(db, actor=admin, action="REFUND_RECONCILED", target_type="REFUND", target_id=refund.id, reason=reason, previous_value=None, new_value={"status": refund.status.value, "provider_status": refund.provider_status})
        db.commit(); db.refresh(refund)
        return refund
    except HTTPException:
        db.rollback(); refund = db.get(Refund, refund_id); _schedule(refund, ambiguous=False, reason="Provider refund status is temporarily unavailable"); db.commit(); db.refresh(refund); return refund
    except Exception:
        logger.exception("Refund status reconciliation failed", extra={"refund_id": refund_id})
        db.rollback(); refund = db.get(Refund, refund_id); _schedule(refund, ambiguous=True, reason="Provider refund status could not be determined"); db.commit(); db.refresh(refund); return refund


def require_manual_review(db: Session, refund_id: int, *, admin: User, reason: str) -> Refund:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).options(selectinload(Refund.payment), selectinload(Refund.cancellation).selectinload(Cancellation.booking)).with_for_update())
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    if refund.status in (RefundStatus.SUCCEEDED, RefundStatus.PARTIAL):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refund has already been settled")
    previous = refund.status
    refund.status = RefundStatus.MANUAL_REVIEW
    refund.reconciliation_reason = reason
    refund.next_retry_at = None
    refund.executed_by_user_id = admin.id
    if refund.cancellation is not None:
        refund.cancellation.status = CancellationStatus.MANUAL_REVIEW
        refund.cancellation.requires_manual_review = True
    _notify_refund(db, refund, event_type=NotificationEventType.REFUND_REQUIRES_REVIEW, key=f"refund:{refund.id}:manual-review", title="Refund requires review", body="Your refund is in support reconciliation review.")
    audit_service.record(db, actor=admin, action="REFUND_SETTLED", target_type="REFUND", target_id=refund.id, reason=reason, previous_value={"status": previous.value}, new_value={"status": refund.status.value})
    db.commit()
    db.refresh(refund)
    return refund


def ensure_payment_reconciliation_refund(db: Session, payment_id: int) -> Refund:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).options(selectinload(Payment.booking).selectinload(Booking.cancellation)).with_for_update())
    if payment is None or payment.status != PaymentStatus.PAID or payment.reconciliation_status != PaymentReconciliationStatus.REFUND_REQUIRED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment is not eligible for reconciliation refund")
    booking = payment.booking
    cancellation = booking.cancellation
    if cancellation is not None:
        existing = db.scalar(select(Refund).where(Refund.cancellation_id == cancellation.id, Refund.payment_id == payment.id))
        if existing is not None:
            return existing
    if cancellation is None:
        cancellation = Cancellation(booking_id=booking.id, cancellation_type=CancellationType.PAYMENT_RECONCILIATION, status=CancellationStatus.REFUND_PENDING, reason="Verified payment could not be fulfilled", policy_snapshot={**booking.policy_snapshot, "refund_decision": "Full refund required after failed booking confirmation"}, refundable_amount=payment.amount, requires_manual_review=False)
        db.add(cancellation); db.flush()
    refund = create_instruction(db, cancellation, payment, payment.amount, idempotency_key=f"payment-reconciliation-{payment.id}")
    booking.status = BookingStatus.REFUND_PENDING
    booking.payment_status = PaymentStatus.REFUND_PENDING
    db.commit()
    return submit_refund(db, refund.id, reason="Paid booking could not be fulfilled")


def run_due(db: Session) -> int:
    now = datetime.now(timezone.utc)
    payment_ids = list(db.scalars(select(Payment.id).where(Payment.status == PaymentStatus.PAID, Payment.reconciliation_status == PaymentReconciliationStatus.REFUND_REQUIRED, Payment.id.not_in(select(Refund.payment_id))).limit(50)))
    for payment_id in payment_ids:
        try:
            ensure_payment_reconciliation_refund(db, payment_id)
        except HTTPException:
            db.rollback()
    refund_ids = list(db.scalars(select(Refund.id).where(Refund.status.in_((RefundStatus.PROCESSING, RefundStatus.RETRY_REQUIRED)), Refund.next_retry_at.is_not(None), Refund.next_retry_at <= now).limit(50)))
    for refund_id in refund_ids:
        refund = db.get(Refund, refund_id)
        if refund and refund.status == RefundStatus.RETRY_REQUIRED and not refund.provider_refund_id:
            submit_refund(db, refund_id)
        else:
            reconcile_refund(db, refund_id)
    return len(payment_ids) + len(refund_ids)


def admin_detail(db: Session, refund_id: int) -> AdminRefundDetail:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).options(
        selectinload(Refund.payment),
        selectinload(Refund.cancellation).selectinload(Cancellation.booking).selectinload(Booking.user),
        selectinload(Refund.cancellation).selectinload(Cancellation.booking).selectinload(Booking.hotel),
    ))
    if refund is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    cancellation = refund.cancellation
    if cancellation is None:
        if refund.safari_request_id is not None:
            safari_request = db.get(SafariRequest, refund.safari_request_id)
            customer = db.get(User, safari_request.customer_id) if safari_request else None
            return AdminRefundDetail(
                refund=RefundResponse.model_validate(refund), subject_type="SAFARI", verification_id=None,
                safari_request_id=refund.safari_request_id,
                subject_reference=safari_request.request_reference if safari_request else None,
                booking_id=None, booking_reference=None, booking_status=None,
                customer_id=customer.id if customer else None, customer_name=customer.full_name if customer else None,
                hotel_id=None, hotel_name=None, cancellation_id=None, cancellation_type=None,
                cancellation_status=None, cancellation_reason=safari_request.failure_reason if safari_request else "External safari booking failed",
                approved_refund_amount=refund.amount,
                refunded_amount=refund.amount if refund.status == RefundStatus.SUCCEEDED else Decimal("0"),
                payment_id=refund.payment_id, captured_amount=refund.payment.amount, payment_status=refund.payment.status,
            )
        verification = db.get(HotelVerification, refund.verification_id) if refund.verification_id else None
        hotel = db.get(Hotel, verification.hotel_id) if verification else None
        partner = db.get(User, hotel.partner_id) if hotel and hotel.partner_id else None
        return AdminRefundDetail(
            refund=RefundResponse.model_validate(refund), subject_type="VERIFICATION", verification_id=refund.verification_id,
            safari_request_id=None, subject_reference=f"Hotel verification #{verification.id}" if verification else None,
            booking_id=None, booking_reference=None, booking_status=None,
            customer_id=partner.id if partner else None, customer_name=partner.full_name if partner else None,
            hotel_id=hotel.id if hotel else refund.payment.verification_hotel_id or 0, hotel_name=hotel.name if hotel else "Unknown hotel",
            cancellation_id=None, cancellation_type=None, cancellation_status=None,
            cancellation_reason=verification.rejection_reason if verification else "Final verification rejection",
            approved_refund_amount=refund.amount, refunded_amount=refund.amount if refund.status == RefundStatus.SUCCEEDED else Decimal("0"),
            payment_id=refund.payment_id, captured_amount=refund.payment.amount, payment_status=refund.payment.status,
        )
    booking = cancellation.booking
    return AdminRefundDetail(
        refund=RefundResponse.model_validate(refund), subject_type="BOOKING", verification_id=None,
        safari_request_id=None, subject_reference=booking.booking_reference,
        booking_id=booking.id, booking_reference=booking.booking_reference,
        booking_status=booking.status, customer_id=booking.user_id, customer_name=booking.user.full_name,
        hotel_id=booking.hotel_id, hotel_name=booking.hotel.name, cancellation_id=cancellation.id,
        cancellation_type=cancellation.cancellation_type, cancellation_status=cancellation.status,
        cancellation_reason=cancellation.reason, approved_refund_amount=cancellation.refundable_amount,
        refunded_amount=cancellation.refunded_amount, payment_id=refund.payment_id,
        captured_amount=refund.payment.amount, payment_status=refund.payment.status,
    )
