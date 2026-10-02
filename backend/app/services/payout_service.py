"""Durable payout initiation, verified callbacks, and provider reconciliation."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.communication import NotificationEventType
from app.models.hotel_verification import HotelVerification, VerificationStatus
from app.models.settlement import Payout, PayoutStatus, PayoutWebhookEvent, Settlement, SettlementEvent, SettlementStatus
from app.models.user import User
from app.services import audit_service, notification_service, payout_provider, settlement_service


logger = logging.getLogger(__name__)
PROCESSING_STATES = {"accepted", "pending", "processing", "queued"}
SUCCESS_STATES = {"success", "succeeded", "completed", "paid", "processed"}
FAILED_STATES = {"failed", "rejected", "cancelled", "canceled"}
REVERSED_STATES = {"reversed"}


def _load_payout(db: Session, payout_id: int, *, lock: bool = False) -> Payout:
    query = select(Payout).where(Payout.id == payout_id).options(
        selectinload(Payout.settlement).selectinload(Settlement.booking),
        selectinload(Payout.settlement).selectinload(Settlement.events),
    )
    if lock:
        query = query.with_for_update()
    payout = db.scalar(query)
    if payout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    return payout


def _notify(db: Session, payout: Payout, event_type: NotificationEventType, title: str, body: str) -> None:
    settlement = payout.settlement
    if not settlement.hotel.partner_id:
        return
    notification_service.create(
        db, recipient_user_id=settlement.hotel.partner_id, event_type=event_type,
        dedupe_key=f"{event_type.value}:payout:{payout.id}:{payout.status.value}", title=title, body=body,
        data={"booking_id": settlement.booking_id, "booking_reference": settlement.booking.booking_reference, "hotel_id": settlement.hotel_id, "settlement_id": settlement.id, "payout_id": payout.id},
    )


def _require_reconciliation(payout: Payout, note: str, *, actor_user_id: int | None = None) -> None:
    """Keep the payout and settlement review states aligned and auditable."""
    settlement = payout.settlement
    previous = settlement.status
    settlement.status = SettlementStatus.RECONCILIATION_REQUIRED
    settlement.hold_reason = note[:255]
    settlement.held_at = datetime.now(timezone.utc)
    if previous != SettlementStatus.RECONCILIATION_REQUIRED:
        settlement.events.append(SettlementEvent(
            old_status=previous,
            new_status=SettlementStatus.RECONCILIATION_REQUIRED,
            note=note,
            actor_user_id=actor_user_id,
        ))


def _destination(db: Session, settlement: Settlement) -> payout_provider.PayoutDestination:
    verification = db.scalar(select(HotelVerification).where(HotelVerification.hotel_id == settlement.hotel_id).with_for_update())
    if verification is None or verification.verification_status != VerificationStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel verification is not approved for payout")
    if not all((verification.bank_account_number, verification.bank_ifsc, verification.bank_beneficiary_name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel payout details are incomplete")
    normalized = "|".join((verification.bank_account_number, verification.bank_ifsc, verification.bank_beneficiary_name))
    fingerprint = hmac.new((settings.DATA_ENCRYPTION_KEY or settings.SECRET_KEY).encode(), normalized.encode(), hashlib.sha256).hexdigest()
    return payout_provider.PayoutDestination(
        reference=f"hotel-verification:{verification.id}", beneficiary_name=verification.bank_beneficiary_name,
        bank_account_number=verification.bank_account_number, bank_ifsc=verification.bank_ifsc, fingerprint=fingerprint,
    )


def _still_payable(db: Session, settlement: Settlement, *, allowed_statuses: tuple[SettlementStatus, ...] = (SettlementStatus.ELIGIBLE,)) -> None:
    eligibility = settlement_service.calculate_eligibility(db, settlement.booking)
    if eligibility is None or eligibility.blocker:
        issue = eligibility.blocker if eligibility else "Booking is no longer settlement eligible"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=issue)
    if settlement.status not in allowed_statuses:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Settlement state does not permit payout submission")
    if settlement.commission_rate is None or not settlement.commission_rule:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Settlement has no immutable commission snapshot")
    if settlement.net_payable <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Net payable must be positive")
    if settlement.currency.upper() != "INR":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel payout currency is not supported")
    if settings.PAYOUT_PROVIDER == "RAZORPAYX" and settlement.net_payable < settings.RAZORPAYX_MIN_PAYOUT_AMOUNT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Net payable is below the configured provider minimum")
    if eligibility.refund_deductions != settlement.refund_deductions:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Refund state changed after settlement calculation")


def initiate(db: Session, settlement_id: int, *, admin: User | None = None, reason: str = "Approved payout initiation") -> Settlement:
    """Create the durable local instruction before contacting the provider."""
    settlement = settlement_service.get_admin(db, settlement_id, lock=True)
    if settlement.payout is not None:
        return settlement
    provider = payout_provider.configured_provider()
    _still_payable(db, settlement)
    destination = _destination(db, settlement)
    now = datetime.now(timezone.utc)
    payout = Payout(
        settlement_id=settlement.id, provider=provider.name,
        idempotency_key=f"settlement-{settlement.id}-v1", beneficiary_reference=destination.reference,
        destination_fingerprint=destination.fingerprint,
        amount=settlement.net_payable, currency=settlement.currency, status=PayoutStatus.PENDING,
    )
    db.add(payout)
    settlement.status, settlement.payout_provider, settlement.processing_at = SettlementStatus.PROCESSING, provider.name, now
    settlement.events.append(SettlementEvent(old_status=SettlementStatus.ELIGIBLE, new_status=SettlementStatus.PROCESSING, note=f"Durable payout instruction created for {provider.name}", actor_user_id=admin.id if admin else None))
    if admin:
        audit_service.record(db, actor=admin, action="PAYOUT_INITIATED", target_type="SETTLEMENT", target_id=settlement.id, reason=reason, previous_value={"status": SettlementStatus.ELIGIBLE.value}, new_value={"status": SettlementStatus.PROCESSING.value, "provider": provider.name})
    db.commit()
    db.refresh(payout)
    payout_id = payout.id

    try:
        instruction = provider.create_payout(
            destination=destination, amount=payout.amount,
            currency=payout.currency, idempotency_key=payout.idempotency_key,
        )
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        if instruction.amount != payout.amount or instruction.currency != payout.currency:
            payout.status = PayoutStatus.RECONCILIATION_REQUIRED
            payout.reconciliation_reason = "Provider acceptance did not match the approved payout financials"
            _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id if admin else None)
        else:
            payout.provider_payout_id = instruction.provider_payout_id
            payout.provider_contact_id = instruction.provider_contact_id
            payout.provider_fund_account_id = instruction.provider_fund_account_id
            payout.provider_utr = instruction.utr
            payout.provider_status = instruction.status
            payout.status = PayoutStatus.PROCESSING
            payout.initiated_at = payout.last_checked_at
            payout.next_retry_at = payout.last_checked_at + timedelta(minutes=settings.PAYOUT_RECONCILIATION_BACKOFF_MINUTES)
            _notify(db, payout, NotificationEventType.PAYOUT_INITIATED, "Hotel payout initiated", f"Payout for booking {payout.settlement.booking.booking_reference} is processing.")
        db.commit()
    except HTTPException:
        db.rollback()
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = "Payout provider was unavailable before submission"
        payout.next_retry_at = None
        _require_reconciliation(payout, payout.failure_reason, actor_user_id=admin.id if admin else None)
        _notify(db, payout, NotificationEventType.PAYOUT_FAILED, "Hotel payout requires review", payout.failure_reason)
        db.commit()
    except Exception:
        logger.exception("Payout submission outcome is uncertain", extra={"payout_id": payout_id})
        db.rollback()
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        payout.status = PayoutStatus.RECONCILIATION_REQUIRED
        payout.reconciliation_reason = "Provider request outcome is unknown; do not issue another payout"
        payout.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PAYOUT_RECONCILIATION_BACKOFF_MINUTES)
        _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id if admin else None)
        _notify(db, payout, NotificationEventType.PAYOUT_REQUIRES_REVIEW, "Hotel payout requires reconciliation", payout.reconciliation_reason)
        db.commit()
    return settlement_service.get_admin(db, settlement_id)


def retry_submission(db: Session, settlement_id: int, *, admin: User, reason: str) -> Settlement:
    """Retry only after provider lookup established that no payout exists."""
    settlement = settlement_service.get_admin(db, settlement_id, lock=True)
    payout = settlement.payout
    if payout is None or payout.provider_payout_id:
        raise HTTPException(status_code=409, detail="This payout cannot be resubmitted")
    safe_absence = (payout.reconciliation_reason or "").startswith("No provider payout exists")
    if payout.status != PayoutStatus.FAILED and not safe_absence:
        raise HTTPException(status_code=409, detail="Reconcile the provider outcome before retrying payout submission")
    _still_payable(db, settlement, allowed_statuses=(SettlementStatus.PROCESSING, SettlementStatus.RECONCILIATION_REQUIRED))
    destination = _destination(db, settlement)
    if not payout.destination_fingerprint or not hmac.compare_digest(payout.destination_fingerprint, destination.fingerprint):
        raise HTTPException(status_code=409, detail="Payout destination changed after authorization; finance review is required")
    provider = payout_provider.configured_provider()
    old_settlement_status = settlement.status
    payout.status = PayoutStatus.PENDING
    payout.failure_reason = None
    payout.reconciliation_reason = "Controlled retry reserved with the original idempotency identity"
    payout.next_retry_at = None
    settlement.status = SettlementStatus.PROCESSING
    settlement.hold_reason = None
    settlement.events.append(SettlementEvent(old_status=old_settlement_status, new_status=SettlementStatus.PROCESSING, note="Payout retry reserved after provider absence was confirmed", actor_user_id=admin.id))
    audit_service.record(db, actor=admin, action="PAYOUT_RETRIED", target_type="PAYOUT", target_id=payout.id, reason=reason, previous_value={"provider_reference_recorded": False}, new_value={"same_idempotency_key": True})
    db.commit()
    payout_id = payout.id
    try:
        result = provider.create_payout(destination=destination, amount=payout.amount, currency=payout.currency, idempotency_key=payout.idempotency_key)
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        if result.amount != payout.amount or result.currency != payout.currency:
            payout.status = PayoutStatus.RECONCILIATION_REQUIRED
            payout.reconciliation_reason = "Provider retry acceptance did not match approved financials"
            _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id)
        else:
            payout.provider_payout_id = result.provider_payout_id
            payout.provider_contact_id = result.provider_contact_id
            payout.provider_fund_account_id = result.provider_fund_account_id
            payout.provider_utr = result.utr
            payout.initiated_at = payout.last_checked_at
            _apply_state(db, payout, result.status, actor_user_id=admin.id, utr=result.utr)
        db.commit()
    except HTTPException:
        db.rollback()
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = "Payout provider rejected the controlled retry"
        payout.next_retry_at = None
        _require_reconciliation(payout, payout.failure_reason, actor_user_id=admin.id)
        db.commit()
    except Exception:
        db.rollback()
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        payout.status = PayoutStatus.RECONCILIATION_REQUIRED
        payout.reconciliation_reason = "Provider retry outcome is unknown; do not issue another payout"
        payout.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PAYOUT_RECONCILIATION_BACKOFF_MINUTES)
        _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id)
        db.commit()
    return settlement_service.get_admin(db, settlement_id)


def _apply_state(db: Session, payout: Payout, provider_state: str, *, actor_user_id: int | None = None, failure_reason: str | None = None, utr: str | None = None) -> None:
    state = provider_state.strip().lower()
    if payout.status == PayoutStatus.REVERSED:
        return
    if payout.status == PayoutStatus.SUCCESS and state not in REVERSED_STATES:
        return
    payout.provider_status = state
    payout.provider_utr = utr or payout.provider_utr
    payout.last_checked_at = datetime.now(timezone.utc)
    settlement = payout.settlement
    if state in SUCCESS_STATES:
        if payout.status == PayoutStatus.SUCCESS and settlement.status == SettlementStatus.SETTLED:
            return
        previous = settlement.status
        payout.status, payout.completed_at, payout.next_retry_at = PayoutStatus.SUCCESS, payout.last_checked_at, None
        settlement.status, settlement.settled_at = SettlementStatus.SETTLED, payout.completed_at
        settlement.hold_reason, settlement.held_at, settlement.held_by_user_id = None, None, None
        settlement.payout_provider_reference = payout.provider_payout_id
        settlement.events.append(SettlementEvent(old_status=previous, new_status=SettlementStatus.SETTLED, note="Payout success verified with provider", actor_user_id=actor_user_id))
        _notify(db, payout, NotificationEventType.PAYOUT_COMPLETED, "Hotel payout completed", f"Payout for booking {settlement.booking.booking_reference} was confirmed by the provider.")
    elif state in PROCESSING_STATES:
        payout.status = PayoutStatus.PROCESSING
        payout.next_retry_at = payout.last_checked_at + timedelta(minutes=settings.PAYOUT_RECONCILIATION_BACKOFF_MINUTES)
        if settlement.status == SettlementStatus.RECONCILIATION_REQUIRED:
            settlement.status = SettlementStatus.PROCESSING
            settlement.hold_reason, settlement.held_at, settlement.held_by_user_id = None, None, None
            settlement.events.append(SettlementEvent(old_status=SettlementStatus.RECONCILIATION_REQUIRED, new_status=SettlementStatus.PROCESSING, note="Provider payout recovered and remains in progress", actor_user_id=actor_user_id))
    elif state in FAILED_STATES:
        payout.status, payout.failure_reason, payout.next_retry_at = PayoutStatus.FAILED, (failure_reason or f"Provider reports payout {state}")[:255], None
        _require_reconciliation(payout, payout.failure_reason, actor_user_id=actor_user_id)
        _notify(db, payout, NotificationEventType.PAYOUT_FAILED, "Hotel payout failed", f"Payout for booking {settlement.booking.booking_reference} requires review.")
    elif state in REVERSED_STATES:
        previous = settlement.status
        payout.status, payout.failure_reason, payout.next_retry_at = PayoutStatus.REVERSED, (failure_reason or "Provider confirmed payout reversal")[:255], None
        settlement.status = SettlementStatus.RECONCILIATION_REQUIRED
        settlement.hold_reason = "Provider confirmed payout reversal; finance reconciliation required"
        settlement.held_at = payout.last_checked_at
        settlement.events.append(SettlementEvent(old_status=previous, new_status=settlement.status, note=settlement.hold_reason, actor_user_id=actor_user_id))
        _notify(db, payout, NotificationEventType.PAYOUT_REQUIRES_REVIEW, "Hotel payout reversed", f"Payout for booking {settlement.booking.booking_reference} requires finance review.")
    else:
        payout.status, payout.reconciliation_reason, payout.next_retry_at = PayoutStatus.RECONCILIATION_REQUIRED, f"Unknown provider payout state: {state or 'empty'}", None
        _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=actor_user_id)
        _notify(db, payout, NotificationEventType.PAYOUT_REQUIRES_REVIEW, "Hotel payout requires reconciliation", f"Payout for booking {settlement.booking.booking_reference} requires review.")


def reconcile(db: Session, payout_id: int, *, admin: User | None = None, reason: str = "Provider payout reconciliation") -> Payout:
    payout = _load_payout(db, payout_id, lock=True)
    if payout.status == PayoutStatus.SUCCESS:
        return payout
    if payout.attempts >= settings.PAYOUT_RECONCILIATION_MAX_ATTEMPTS:
        payout.status = PayoutStatus.RECONCILIATION_REQUIRED
        payout.reconciliation_reason = "Payout reconciliation retry limit reached"
        payout.next_retry_at = None
        _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id if admin else None)
        db.commit(); db.refresh(payout)
        return payout
    provider = payout_provider.configured_provider()
    try:
        result = provider.fetch_payout(payout.provider_payout_id) if payout.provider_payout_id else provider.find_payout_by_reference(payout.idempotency_key)
        payout.attempts += 1
        if result is None:
            payout.status = PayoutStatus.RECONCILIATION_REQUIRED
            payout.reconciliation_reason = "No provider payout exists for the stable Maharashtra Tourist Places reference; manual retry is permitted"
            payout.next_retry_at = None
            _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id if admin else None)
        elif result.amount != payout.amount or result.currency != payout.currency:
            payout.status = PayoutStatus.RECONCILIATION_REQUIRED
            payout.reconciliation_reason = "Provider lookup financials do not match the approved payout"
            payout.next_retry_at = None
            _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id if admin else None)
        else:
            payout.provider_payout_id = result.provider_payout_id
            payout.provider_contact_id = result.provider_contact_id or payout.provider_contact_id
            payout.provider_fund_account_id = result.provider_fund_account_id or payout.provider_fund_account_id
            _apply_state(db, payout, result.status, actor_user_id=admin.id if admin else None, utr=result.utr)
        if admin:
            audit_service.record(db, actor=admin, action="PAYOUT_RECONCILED", target_type="PAYOUT", target_id=payout.id, reason=reason, previous_value=None, new_value={"status": payout.status.value, "provider_status": payout.provider_status})
        db.commit(); db.refresh(payout)
        return payout
    except Exception:
        logger.exception("Payout status reconciliation failed", extra={"payout_id": payout.id})
        db.rollback()
        payout = _load_payout(db, payout_id, lock=True)
        payout.attempts += 1
        payout.last_checked_at = datetime.now(timezone.utc)
        if payout.attempts >= settings.PAYOUT_RECONCILIATION_MAX_ATTEMPTS:
            payout.status, payout.reconciliation_reason, payout.next_retry_at = PayoutStatus.RECONCILIATION_REQUIRED, "Provider status remained unavailable after bounded retries", None
            _require_reconciliation(payout, payout.reconciliation_reason, actor_user_id=admin.id if admin else None)
        else:
            payout.next_retry_at = payout.last_checked_at + timedelta(minutes=settings.PAYOUT_RECONCILIATION_BACKOFF_MINUTES)
        db.commit(); db.refresh(payout)
        return payout


def handle_callback(db: Session, payload: bytes, signature: str | None, event_id: str | None = None) -> Payout:
    provider = payout_provider.configured_provider()
    if not provider.verify_payout_callback(payload, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payout callback signature")
    event = provider.parse_payout_callback(payload, event_id)
    duplicate = db.scalar(select(PayoutWebhookEvent).where(PayoutWebhookEvent.provider == provider.name, PayoutWebhookEvent.provider_event_id == event.event_id))
    if duplicate is not None and duplicate.payout_id is not None:
        return _load_payout(db, duplicate.payout_id)
    payout = db.scalar(select(Payout).where(Payout.provider == provider.name, Payout.provider_payout_id == event.provider_payout_id).options(selectinload(Payout.settlement).selectinload(Settlement.booking), selectinload(Payout.settlement).selectinload(Settlement.events)).with_for_update())
    if payout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    ledger_event = PayoutWebhookEvent(provider=provider.name, provider_event_id=event.event_id, payout_id=payout.id, payload_hash=hashlib.sha256(payload).hexdigest())
    db.add(ledger_event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(PayoutWebhookEvent).where(PayoutWebhookEvent.provider == provider.name, PayoutWebhookEvent.provider_event_id == event.event_id))
        if duplicate is not None and duplicate.payout_id is not None:
            return _load_payout(db, duplicate.payout_id)
        raise
    if event.amount != payout.amount or event.currency != payout.currency:
        payout.status = PayoutStatus.RECONCILIATION_REQUIRED
        payout.reconciliation_reason = "Callback financials do not match the approved payout"
        payout.next_retry_at = None
        _require_reconciliation(payout, payout.reconciliation_reason)
    else:
        _apply_state(db, payout, event.status, failure_reason=event.failure_reason, utr=event.utr)
    db.commit(); db.refresh(payout)
    return payout


def run_due(db: Session) -> tuple[int, int]:
    initiated = 0
    if settings.PAYOUT_AUTO_INITIATE:
        settlement_ids = list(db.scalars(select(Settlement.id).where(Settlement.status == SettlementStatus.ELIGIBLE, Settlement.id.not_in(select(Payout.settlement_id))).limit(25)))
        for settlement_id in settlement_ids:
            try:
                initiate(db, settlement_id, reason="Automatic eligible-settlement payout")
                initiated += 1
            except HTTPException:
                db.rollback()
    now = datetime.now(timezone.utc)
    payout_ids = list(db.scalars(select(Payout.id).where(
        Payout.status.in_((PayoutStatus.PROCESSING, PayoutStatus.RECONCILIATION_REQUIRED)),
        Payout.next_retry_at.is_not(None), Payout.next_retry_at <= now,
    ).limit(50)))
    for payout_id in payout_ids:
        reconcile(db, payout_id)
    return initiated, len(payout_ids)
