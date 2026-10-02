"""Authoritative settlement eligibility and immutable financial snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import (
    Booking, BookingStatus, Cancellation, CancellationStatus, CancellationType,
    PaymentReconciliationStatus, PaymentStatus, Refund, RefundStatus, SettlementImpactStatus,
)
from app.models.communication import Conversation, ConversationKind, ConversationStatus, NotificationEventType
from app.models.settlement import Settlement, SettlementAdjustment, SettlementAdjustmentKind, SettlementEvent, SettlementStatus
from app.models.user import User
from app.repositories import hotel_repository
from app.services import audit_service, notification_service


MONEY = Decimal("0.01")
UNRESOLVED_REFUNDS = {
    RefundStatus.PENDING, RefundStatus.PROCESSING, RefundStatus.RETRY_REQUIRED,
    RefundStatus.RECONCILIATION_REQUIRED, RefundStatus.MANUAL_REVIEW, RefundStatus.FAILED,
}


@dataclass(frozen=True)
class SettlementEligibility:
    eligibility_date: datetime
    gross_amount: Decimal
    refund_deductions: Decimal
    commission_rate: Decimal | None
    commission_rule: str | None
    commission_amount: Decimal
    blocker: str | None
    outcome: str


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc) if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _load_options():
    return (
        selectinload(Settlement.booking).selectinload(Booking.cancellation).selectinload(Cancellation.refunds),
        selectinload(Settlement.booking).selectinload(Booking.payments),
        selectinload(Settlement.booking).selectinload(Booking.status_history),
        selectinload(Settlement.adjustments), selectinload(Settlement.applied_adjustments),
        selectinload(Settlement.events), selectinload(Settlement.hotel), selectinload(Settlement.payout),
    )


def _refund_deduction(booking: Booking) -> Decimal:
    return _money(booking.cancellation.refunded_amount if booking.cancellation is not None else Decimal("0.00"))


def _no_show_anchor(booking: Booking) -> datetime | None:
    event = next((item for item in reversed(booking.status_history) if item.new_status == BookingStatus.NO_SHOW), None)
    return _utc(event.created_at) if event and event.created_at else None


def _financial_blocker(db: Session, booking: Booking) -> str | None:
    paid = [payment for payment in booking.payments if payment.status == PaymentStatus.PAID]
    if not paid:
        return "No provider-verified customer payment is available"
    if any(payment.currency != booking.currency for payment in paid):
        return "Payment currency requires reconciliation"
    if any(payment.reconciliation_status in (
        PaymentReconciliationStatus.CONFIRMATION_REQUIRED,
        PaymentReconciliationStatus.REFUND_REQUIRED,
        PaymentReconciliationStatus.MANUAL_REVIEW,
    ) for payment in booking.payments):
        return "Payment reconciliation requires review"
    if db.scalar(select(Conversation.id).where(
        Conversation.booking_id == booking.id,
        Conversation.kind == ConversationKind.DISPUTE,
        Conversation.status == ConversationStatus.OPEN,
    ).limit(1)) is not None:
        return "An unresolved customer dispute is open"
    cancellation = booking.cancellation
    if cancellation is None:
        return None
    if cancellation.requires_manual_review or cancellation.status == CancellationStatus.MANUAL_REVIEW:
        return "Cancellation or no-show policy requires financial review"
    if any(refund.status in UNRESOLVED_REFUNDS for refund in cancellation.refunds):
        return "Refund execution or reconciliation is not finalized"
    return None


def calculate_eligibility(db: Session, booking: Booking, *, now: datetime | None = None) -> SettlementEligibility | None:
    """Single authoritative calculation for checkout and finalized no-show outcomes."""
    del now
    if booking.status == BookingStatus.CHECKED_OUT and booking.checked_out_at is not None:
        outcome, anchor = "CHECKED_OUT", _utc(booking.checked_out_at)
    elif booking.cancellation and booking.cancellation.cancellation_type == CancellationType.NO_SHOW:
        outcome, anchor = "NO_SHOW", _no_show_anchor(booking)
    else:
        return None
    if anchor is None:
        return None

    refunds = _refund_deduction(booking)
    gross = _money(booking.total_amount)
    blocker = _financial_blocker(db, booking)
    if outcome == "NO_SHOW":
        cancellation = booking.cancellation
        if cancellation is None or cancellation.status != CancellationStatus.COMPLETED:
            blocker = blocker or "No-show financial outcome is not finalized"
        decision = str((cancellation.policy_snapshot if cancellation else {}).get("refund_decision") or "")
        if not decision:
            blocker = blocker or "No-show policy snapshot cannot be interpreted safely"
        if refunds > gross:
            blocker = blocker or "No-show refund exceeds the captured booking amount"

    rate = settings.VAYORA_COMMISSION_RATE
    rule = settings.VAYORA_COMMISSION_RULE if rate is not None else None
    if rate is None:
        blocker = blocker or "Maharashtra Tourist Places commission is not configured"
        commission = Decimal("0.00")
    else:
        commission = _money(max(Decimal("0.00"), gross - refunds) * rate)
    return SettlementEligibility(
        eligibility_date=anchor + timedelta(days=settings.SETTLEMENT_ELIGIBILITY_DAYS),
        gross_amount=gross, refund_deductions=refunds, commission_rate=rate,
        commission_rule=rule, commission_amount=commission, blocker=blocker, outcome=outcome,
    )


def _event(settlement: Settlement, old: SettlementStatus | None, new: SettlementStatus, note: str, actor_id: int | None = None) -> None:
    settlement.events.append(SettlementEvent(old_status=old, new_status=new, note=note, actor_user_id=actor_id))


def _notify(db: Session, settlement: Settlement, *, title: str = "Settlement updated") -> None:
    db.flush()
    if not settlement.hotel.partner_id:
        return
    notification_service.create(
        db, recipient_user_id=settlement.hotel.partner_id,
        event_type=NotificationEventType.SETTLEMENT_UPDATE,
        dedupe_key=f"SETTLEMENT_UPDATE:{settlement.id}:{len(settlement.events)}:{settlement.status.value}", title=title,
        body=f"Settlement for booking {settlement.booking.booking_reference} is {settlement.status.value.lower().replace('_', ' ')}.",
        data={"booking_id": settlement.booking_id, "booking_reference": settlement.booking.booking_reference, "hotel_id": settlement.hotel_id, "settlement_id": settlement.id},
    )


def _consume_pending_adjustments(db: Session, settlement: Settlement, now: datetime) -> Decimal:
    pending = list(db.scalars(
        select(SettlementAdjustment).join(Settlement, Settlement.id == SettlementAdjustment.settlement_id)
        .where(
            Settlement.hotel_id == settlement.hotel_id, Settlement.currency == settlement.currency,
            SettlementAdjustment.applies_to_current_settlement.is_(False),
            SettlementAdjustment.applied_to_settlement_id.is_(None),
        ).order_by(SettlementAdjustment.id).with_for_update(skip_locked=True)
    ))
    total = Decimal("0.00")
    for adjustment in pending:
        adjustment.applied_to_settlement_id = settlement.id
        adjustment.applied_at = now
        total += adjustment.amount
    return _money(total)


def apply_completed_refund(db: Session, refund: Refund) -> None:
    """Record a provider-confirmed refund without rewriting settled history."""
    settlement = db.scalar(select(Settlement).where(Settlement.booking_id == refund.cancellation.booking_id).options(*_load_options()))
    if settlement is None:
        refund.settlement_impact_status = SettlementImpactStatus.PENDING
        return
    if settlement.status == SettlementStatus.SETTLED or (settlement.payout is not None and settlement.payout.completed_at is not None):
        marker = f"refund #{refund.id}"
        if not any(item.kind == SettlementAdjustmentKind.REVERSAL and marker in item.reason for item in settlement.adjustments):
            settlement.adjustments.append(SettlementAdjustment(
                kind=SettlementAdjustmentKind.REVERSAL, amount=-_money(refund.amount),
                reason=f"Provider-confirmed {marker} after settlement", applies_to_current_settlement=False,
                created_by_user_id=refund.executed_by_user_id or refund.cancellation.booking.user_id,
            ))
            _event(settlement, SettlementStatus.SETTLED, SettlementStatus.SETTLED, f"Refund #{refund.id} recorded as future payout reversal")
        refund.settlement_impact_status = SettlementImpactStatus.RECORDED
        return
    # Use the locked refund aggregate directly; the booking's one-to-one
    # cancellation relationship may still be cached as None in this session.
    settlement.refund_deductions = _money(refund.cancellation.refunded_amount)
    if settlement.commission_rate is not None:
        settlement.vayora_fee = _money(max(Decimal("0.00"), settlement.gross_amount - settlement.refund_deductions) * settlement.commission_rate)
    settlement.net_payable = max(Decimal("0.00"), _money(settlement.gross_amount - settlement.vayora_fee - settlement.refund_deductions + settlement.adjustment_total))
    if settlement.status == SettlementStatus.PROCESSING:
        settlement.status = SettlementStatus.ON_HOLD
        settlement.hold_reason = "Provider-confirmed customer refund requires payout reconciliation"
        settlement.held_at = datetime.now(timezone.utc)
        _event(settlement, SettlementStatus.PROCESSING, SettlementStatus.ON_HOLD, settlement.hold_reason)
    refund.settlement_impact_status = SettlementImpactStatus.RECORDED


def refresh_due_settlements(
    db: Session,
    now: datetime | None = None,
    *,
    admin: User | None = None,
    reason: str | None = None,
) -> list[Settlement]:
    """Create each due obligation once and re-evaluate every unpaid obligation."""
    moment = now or datetime.now(timezone.utc)
    bookings = list(db.scalars(
        select(Booking).outerjoin(Cancellation, Cancellation.booking_id == Booking.id)
        .where(or_(Booking.status == BookingStatus.CHECKED_OUT, Cancellation.cancellation_type == CancellationType.NO_SHOW))
        .options(
            selectinload(Booking.cancellation).selectinload(Cancellation.refunds),
            selectinload(Booking.payments), selectinload(Booking.status_history),
        ).with_for_update(skip_locked=True)
    ).unique())
    changed: list[Settlement] = []
    for booking in bookings:
        eligibility = calculate_eligibility(db, booking, now=moment)
        if eligibility is None or moment < eligibility.eligibility_date:
            continue
        existing = db.scalar(select(Settlement).where(Settlement.booking_id == booking.id).options(*_load_options()))
        if existing is not None:
            issue = eligibility.blocker
            if eligibility.refund_deductions != existing.refund_deductions:
                issue = issue or "Refund deduction changed after settlement calculation"
            if issue and existing.status in (SettlementStatus.ELIGIBLE, SettlementStatus.PROCESSING):
                old = existing.status
                existing.status, existing.hold_reason = SettlementStatus.ON_HOLD, issue
                existing.held_at, existing.held_by_user_id = moment, None
                _event(existing, old, SettlementStatus.ON_HOLD, f"Automatically held: {issue}")
                _notify(db, existing, title="Settlement placed on hold")
                changed.append(existing)
            continue

        initial_status = SettlementStatus.ON_HOLD if eligibility.blocker else SettlementStatus.ELIGIBLE
        settlement = Settlement(
            hotel_id=booking.hotel_id, booking_id=booking.id, currency=booking.currency,
            gross_amount=eligibility.gross_amount, commission_rate=eligibility.commission_rate,
            commission_rule=eligibility.commission_rule, vayora_fee=eligibility.commission_amount,
            refund_deductions=eligibility.refund_deductions, adjustment_total=Decimal("0.00"),
            net_payable=Decimal("0.00"), eligibility_date=eligibility.eligibility_date,
            status=initial_status, hold_reason=eligibility.blocker, held_at=moment if eligibility.blocker else None,
        )
        try:
            with db.begin_nested():
                db.add(settlement)
                db.flush()
        except IntegrityError:
            continue
        settlement.adjustment_total = _consume_pending_adjustments(db, settlement, moment)
        calculated_net = _money(settlement.gross_amount - settlement.vayora_fee - settlement.refund_deductions + settlement.adjustment_total)
        if calculated_net < 0:
            settlement.status, settlement.hold_reason = SettlementStatus.ON_HOLD, "Carried adjustments exceed the current hotel payable"
            settlement.held_at, settlement.net_payable = moment, Decimal("0.00")
        else:
            settlement.net_payable = calculated_net
        note = f"Created on hold: {settlement.hold_reason}" if settlement.status == SettlementStatus.ON_HOLD else f"{eligibility.outcome} completed the configured post-stay waiting period"
        _event(settlement, None, settlement.status, note)
        if settlement.adjustment_total:
            _event(settlement, settlement.status, settlement.status, f"Applied carried adjustments totaling {settlement.adjustment_total}")
        _notify(db, settlement, title="Settlement generated" if settlement.status == SettlementStatus.ELIGIBLE else "Settlement placed on hold")
        if booking.cancellation:
            for refund in booking.cancellation.refunds:
                if refund.status in (RefundStatus.SUCCEEDED, RefundStatus.PARTIAL):
                    refund.settlement_impact_status = SettlementImpactStatus.RECORDED
        changed.append(settlement)
    if admin is not None:
        audit_service.record(
            db,
            actor=admin,
            action="SETTLEMENT_ELIGIBILITY_REFRESHED",
            target_type="SETTLEMENT_BATCH",
            target_id="due",
            reason=reason or "Manual settlement eligibility refresh",
            previous_value=None,
            new_value={"changed_count": len(changed), "settlement_ids": [item.id for item in changed]},
        )
    if changed or admin is not None:
        db.commit()
        for item in changed:
            db.refresh(item)
    return changed


def _partner_hotel_id(db: Session, partner: User) -> int:
    hotel = hotel_repository.get_hotel_by_partner_id(db, partner.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return hotel.id


def list_partner(db: Session, partner: User) -> list[Settlement]:
    hotel_id = _partner_hotel_id(db, partner)
    return list(db.scalars(select(Settlement).where(Settlement.hotel_id == hotel_id).options(*_load_options()).order_by(Settlement.eligibility_date.desc())))


def get_partner(db: Session, partner: User, settlement_id: int) -> Settlement:
    hotel_id = _partner_hotel_id(db, partner)
    item = db.scalar(select(Settlement).where(Settlement.id == settlement_id, Settlement.hotel_id == hotel_id).options(*_load_options()))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")
    return item


def list_admin(db: Session, settlement_status: SettlementStatus | None = None) -> list[Settlement]:
    query = select(Settlement).options(*_load_options()).order_by(Settlement.eligibility_date.desc())
    if settlement_status is not None:
        query = query.where(Settlement.status == settlement_status)
    return list(db.scalars(query))


def get_admin(db: Session, settlement_id: int, *, lock: bool = False) -> Settlement:
    query = select(Settlement).where(Settlement.id == settlement_id).options(*_load_options()).execution_options(populate_existing=True)
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found")
    return item


def hold(db: Session, admin: User, settlement_id: int, reason: str, now: datetime | None = None) -> Settlement:
    item = get_admin(db, settlement_id, lock=True)
    if item.status == SettlementStatus.SETTLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A settled record is immutable; add an adjustment or reversal")
    if item.status == SettlementStatus.ON_HOLD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Settlement is already on hold")
    old = item.status
    item.status, item.hold_reason = SettlementStatus.ON_HOLD, reason.strip()
    item.held_by_user_id, item.held_at = admin.id, now or datetime.now(timezone.utc)
    _event(item, old, item.status, f"Admin hold: {item.hold_reason}", admin.id)
    audit_service.record(db, actor=admin, action="SETTLEMENT_HELD", target_type="SETTLEMENT", target_id=item.id, reason=reason, previous_value={"status": old.value}, new_value={"status": item.status.value})
    _notify(db, item, title="Settlement placed on hold")
    db.commit(); db.refresh(item)
    return item


def release(db: Session, admin: User, settlement_id: int, reason: str | None = None) -> Settlement:
    item = get_admin(db, settlement_id, lock=True)
    if item.status != SettlementStatus.ON_HOLD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an on-hold settlement can be released")
    eligibility = calculate_eligibility(db, item.booking)
    if eligibility is None or eligibility.blocker:
        issue = eligibility.blocker if eligibility else "Booking outcome is not settlement eligible"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Settlement cannot be released: {issue}")
    if item.commission_rate is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The settlement has no commission snapshot and must be reviewed")
    item.refund_deductions = eligibility.refund_deductions
    item.vayora_fee = _money(max(Decimal("0.00"), item.gross_amount - item.refund_deductions) * item.commission_rate)
    item.net_payable = max(Decimal("0.00"), _money(item.gross_amount - item.vayora_fee - item.refund_deductions + item.adjustment_total))
    item.status, item.hold_reason, item.held_by_user_id, item.held_at = SettlementStatus.ELIGIBLE, None, None, None
    _event(item, SettlementStatus.ON_HOLD, item.status, "Released by administrator after financial review", admin.id)
    audit_service.record(db, actor=admin, action="SETTLEMENT_RELEASED", target_type="SETTLEMENT", target_id=item.id, reason=reason or "Financial review completed", previous_value={"status": SettlementStatus.ON_HOLD.value}, new_value={"status": item.status.value, "net_payable": str(item.net_payable)})
    _notify(db, item)
    db.commit(); db.refresh(item)
    return item


def add_adjustment(db: Session, admin: User, settlement_id: int, kind: SettlementAdjustmentKind, amount: Decimal, reason: str) -> Settlement:
    item = get_admin(db, settlement_id, lock=True)
    signed = _money(amount)
    if signed == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Adjustment amount cannot be zero")
    applies = item.status not in (SettlementStatus.PROCESSING, SettlementStatus.SETTLED)
    previous_total = item.adjustment_total
    if applies:
        new_total = _money(item.adjustment_total + signed)
        new_net = _money(item.gross_amount - item.vayora_fee - item.refund_deductions + new_total)
        if new_net < 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Adjustment would make net payable negative")
        item.adjustment_total, item.net_payable = new_total, new_net
    item.adjustments.append(SettlementAdjustment(kind=kind, amount=signed, reason=reason.strip(), applies_to_current_settlement=applies, created_by_user_id=admin.id))
    note = "Applied adjustment before payout" if applies else "Recorded for exactly one future settlement; current snapshot unchanged"
    _event(item, item.status, item.status, f"{kind.value}: {signed} — {note}", admin.id)
    audit_service.record(db, actor=admin, action="SETTLEMENT_ADJUSTED", target_type="SETTLEMENT", target_id=item.id, reason=reason, previous_value={"adjustment_total": str(previous_total)}, new_value={"adjustment_total": str(item.adjustment_total), "amount": str(signed), "kind": kind.value, "applies_now": applies})
    _notify(db, item)
    db.commit(); db.refresh(item)
    return item
