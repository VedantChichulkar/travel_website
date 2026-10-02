"""Server-side payment order and verified callback processing.

The gateway integration boundary is deliberately narrow: browser clients only
receive a server-created order reference; only a signed provider callback can
settle it.  No card, CVV, or UPI PIN fields exist in this module or database.
"""

import logging
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, Payment, PaymentPurpose, PaymentReconciliationStatus, PaymentStatus, PaymentWebhookEvent, Refund
from app.models.hotel import BookingGatewayStatus, InventoryHoldStatus
from app.models.user import User, UserRole
from app.models.advertising import AdvertisingCampaign
from app.models.safari import SafariRequest
from app.services import booking_gateway_service, inventory_service, payment_provider, payment_reconciliation_service
from app.services import notification_service
from app.models.communication import NotificationEventType
from app.schemas.booking import AdminPaymentReconciliationDetail, CustomerPaymentHistoryItem, PaymentOrderResponse, PaymentReceiptResponse
from app.schemas.hotel_verification import VerificationFeeStatusResponse
from app.repositories import hotel_repository


logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: bytes, signature: str | None) -> bool:
    return payment_provider.configured_provider().verify_callback(payload, signature)


def _payment_owned_by(db: Session, payment: Payment, current_user: User) -> bool:
    if payment.booking_id:
        booking = db.get(Booking, payment.booking_id)
        return bool(booking and booking.user_id == current_user.id)
    if payment.safari_request_id:
        item = db.get(SafariRequest, payment.safari_request_id)
        return bool(item and item.customer_id == current_user.id)
    hotel_id = payment.verification_hotel_id
    if payment.advertising_campaign_id:
        campaign = db.get(AdvertisingCampaign, payment.advertising_campaign_id)
        hotel_id = campaign.hotel_id if campaign else None
    hotel = hotel_repository.get_hotel(db, hotel_id) if hotel_id else None
    return bool(hotel and hotel.partner_id == current_user.id)


def confirm_checkout(db: Session, current_user: User, payment_id: int, provider_order_id: str, provider_payment_id: str, signature: str) -> Payment:
    """Verify a hosted-checkout callback and independently assert capture state."""
    payment = db.get(Payment, payment_id)
    if payment is None or not _payment_owned_by(db, payment, current_user):
        raise HTTPException(status_code=404, detail="Payment not found")
    if provider_order_id != payment.provider_order_id:
        raise HTTPException(status_code=422, detail="Checkout order does not match the server-created order")
    provider = payment_provider.configured_provider()
    if provider.name != payment.provider:
        raise HTTPException(status_code=409, detail="Payment provider does not match this order")
    if not provider.verify_checkout_signature(provider_order_id=payment.provider_order_id, provider_payment_id=provider_payment_id, signature=signature):
        raise HTTPException(status_code=401, detail="Invalid checkout signature")
    evidence = provider.fetch_payment(provider_payment_id)
    if evidence.provider_payment_id != provider_payment_id or evidence.provider_order_id != payment.provider_order_id:
        raise HTTPException(status_code=409, detail="Provider payment does not belong to this order")
    if evidence.amount != payment.amount or evidence.currency != payment.currency:
        raise HTTPException(status_code=409, detail="Provider payment financials do not match this order")
    if evidence.status == "captured":
        return process_webhook(db, payment.provider, f"checkout:{provider_payment_id}", payment.provider_order_id, "succeeded", evidence.amount, evidence.currency, provider_payment_id) or payment
    if evidence.status == "failed":
        return process_webhook(db, payment.provider, f"checkout:{provider_payment_id}:failed", payment.provider_order_id, "failed", evidence.amount, evidence.currency, provider_payment_id, "Provider reports payment failed") or payment
    return payment


def process_razorpay_payment_webhook(db: Session, raw_payload: bytes) -> Payment | None:
    """Normalize supported Razorpay events into Maharashtra Tourist Places' state machine."""
    try:
        payload = json.loads(raw_payload)
        event_type = str(payload.get("event", ""))
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        provider_order_id = str(entity.get("order_id", ""))
        provider_payment_id = str(entity.get("id", ""))
        amount = (Decimal(str(entity.get("amount"))) / 100).quantize(Decimal("0.01"))
        currency = str(entity.get("currency", "")).upper()
    except (ValueError, TypeError, AttributeError, KeyError):
        raise HTTPException(status_code=422, detail="Malformed Razorpay payment webhook") from None
    outcomes = {"payment.captured": "succeeded", "order.paid": "succeeded", "payment.failed": "failed", "payment.authorized": "pending"}
    outcome = outcomes.get(event_type)
    if not outcome:
        logger.info("Ignored unsupported Razorpay payment event", extra={"provider": "RAZORPAY", "event_type": event_type})
        return None
    if not provider_order_id or not provider_payment_id or len(currency) != 3:
        raise HTTPException(status_code=422, detail="Razorpay webhook is missing payment identifiers")
    event_id = f"rzp:{hashlib.sha256(raw_payload).hexdigest()}"
    failure = str(entity.get("error_description") or entity.get("error_reason") or "Payment failed")[:255] if outcome == "failed" else None
    return process_webhook(db, "RAZORPAY", event_id, provider_order_id, outcome, amount, currency, provider_payment_id, failure)


def process_razorpay_refund_webhook(db: Session, raw_payload: bytes):
    from app.services import refund_execution_service

    try:
        payload = json.loads(raw_payload)
        event_type = str(payload.get("event", ""))
        entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        provider_refund_id = str(entity.get("id", ""))
        amount = (Decimal(str(entity.get("amount"))) / 100).quantize(Decimal("0.01"))
        currency = str(entity.get("currency", "")).upper()
    except (ValueError, TypeError, AttributeError, KeyError):
        raise HTTPException(status_code=422, detail="Malformed Razorpay refund webhook") from None
    outcomes = {"refund.created": "pending", "refund.processed": "completed", "refund.failed": "failed"}
    outcome = outcomes.get(event_type)
    if not outcome:
        logger.info("Ignored unsupported Razorpay refund event", extra={"provider": "RAZORPAY", "event_type": event_type})
        return None
    if not provider_refund_id or len(currency) != 3:
        raise HTTPException(status_code=422, detail="Razorpay webhook is missing refund identifiers")
    event_id = f"rzp:{hashlib.sha256(raw_payload).hexdigest()}"
    failure = str(entity.get("error_description") or "Provider reports refund failed")[:255] if outcome == "failed" else None
    return refund_execution_service.process_webhook(db, "RAZORPAY", event_id, provider_refund_id, outcome, amount, currency, failure)


def _load_booking_for_customer(db: Session, booking_id: int, current_user: User) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).options(selectinload(Booking.hotel), selectinload(Booking.room_type)))
    if booking is None or booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def _active_hold_or_error(db: Session, booking: Booking):
    if not booking.hold_token:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking has no active inventory hold")
    hold = db.scalar(select(inventory_service.InventoryHold).where(inventory_service.InventoryHold.hold_token == booking.hold_token).with_for_update())
    if hold is None or hold.status != InventoryHoldStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking hold is no longer active")
    expiry = hold.expires_at if hold.expires_at.tzinfo else hold.expires_at.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        inventory_service.expire_holds(db, room_type_id=booking.room_type_id)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking hold has expired; please start again")
    return hold


def create_order(db: Session, current_user: User, booking_id: int) -> Payment:
    if settings.PAYMENT_MODE == "disabled":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment sandbox is disabled")
    if current_user.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the booking customer can create a payment order")
    booking = _load_booking_for_customer(db, booking_id, current_user)
    if booking.status != BookingStatus.PAYMENT_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This booking is not awaiting instant-booking payment")
    if booking_gateway_service.effective_status(db, booking.hotel) != BookingGatewayStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This hotel is not currently accepting instant bookings")
    _active_hold_or_error(db, booking)
    if Decimal(str(booking.price_snapshot.get("total_amount", booking.total_amount))) != booking.total_amount:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking price snapshot does not match its payable amount")
    active_attempt = db.scalar(select(Payment).where(Payment.booking_id == booking.id, Payment.status == PaymentStatus.PENDING).order_by(Payment.created_at.desc()).with_for_update())
    if active_attempt:
        return active_attempt
    provider = payment_provider.configured_provider()
    order = provider.create_order(amount=booking.total_amount, currency=booking.currency, booking_reference=booking.booking_reference)
    payment = Payment(
        booking_id=booking.id,
        provider=provider.name,
        provider_order_id=order.provider_order_id,
        amount=order.amount,
        currency=order.currency,
        status=PaymentStatus.PENDING,
    )
    booking.payment_status = PaymentStatus.PENDING
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info("Payment order created", extra={"payment_id": payment.id, "booking_id": booking.id, "provider": payment.provider, "currency": payment.currency})
    return payment


def _verification_payment(db: Session, hotel_id: int) -> Payment | None:
    return db.scalar(
        select(Payment)
        .where(Payment.verification_hotel_id == hotel_id, Payment.purpose == PaymentPurpose.VERIFICATION_FEE)
        .order_by(Payment.created_at.desc())
    )


def verification_fee_status(db: Session, hotel_id: int) -> VerificationFeeStatusResponse:
    payment = _verification_payment(db, hotel_id)
    refund = None
    if payment is not None:
        refund = db.scalar(select(Refund).where(Refund.payment_id == payment.id).order_by(Refund.created_at.desc()))
    return VerificationFeeStatusResponse(
        amount=payment.amount if payment else settings.VERIFICATION_FEE_AMOUNT,
        currency=payment.currency if payment else settings.VERIFICATION_FEE_CURRENCY.upper(),
        payment_status=payment.status if payment else PaymentStatus.NOT_STARTED,
        payment_id=payment.id if payment else None,
        provider_order_id=payment.provider_order_id if payment else None,
        payment_reference=payment.provider_payment_id if payment else None,
        paid_at=payment.verified_at if payment else None,
        refund_status=refund.status if refund else None,
        refund_id=refund.id if refund else None,
        refund_reference=refund.provider_refund_id if refund else None,
        refund_failure_reason=(refund.failure_reason or refund.reconciliation_reason) if refund else None,
    )


def create_verification_fee_order(db: Session, current_user: User) -> Payment:
    if settings.PAYMENT_MODE == "disabled":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment processing is disabled")
    if current_user.role != UserRole.HOTEL_PARTNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a hotel partner can pay a verification fee")
    hotel = hotel_repository.get_hotel_by_partner_id(db, current_user.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Create a hotel profile before paying the verification fee")
    existing = _verification_payment(db, hotel.id)
    if existing and existing.status in (PaymentStatus.PENDING, PaymentStatus.PAID, PaymentStatus.REFUND_PENDING, PaymentStatus.REFUNDED):
        return existing
    provider = payment_provider.configured_provider()
    currency = settings.VERIFICATION_FEE_CURRENCY.upper()
    order = provider.create_order(amount=settings.VERIFICATION_FEE_AMOUNT, currency=currency, booking_reference=f"VERIFY-HOTEL-{hotel.id}")
    payment = Payment(
        booking_id=None,
        verification_hotel_id=hotel.id,
        purpose=PaymentPurpose.VERIFICATION_FEE,
        provider=provider.name,
        provider_order_id=order.provider_order_id,
        amount=order.amount,
        currency=order.currency,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_booking_payments(db: Session, current_user: User, booking_id: int) -> list[Payment]:
    booking = _load_booking_for_customer(db, booking_id, current_user)
    return list(db.scalars(select(Payment).where(Payment.booking_id == booking.id).order_by(Payment.created_at.desc())))


def list_customer_payment_history(db: Session, current_user: User) -> list[CustomerPaymentHistoryItem]:
    payments = list(db.scalars(
        select(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Booking.user_id == current_user.id)
        .options(selectinload(Payment.booking).selectinload(Booking.hotel))
        .order_by(Payment.created_at.desc())
    ))
    return [CustomerPaymentHistoryItem(**PaymentOrderResponse.model_validate(item).model_dump(), booking_reference=item.booking.booking_reference, hotel_name=item.booking.hotel.name) for item in payments]


def receipt(db: Session, current_user: User, booking_id: int, payment_id: int) -> PaymentReceiptResponse:
    booking = _load_booking_for_customer(db, booking_id, current_user)
    payment = db.scalar(select(Payment).where(Payment.id == payment_id, Payment.booking_id == booking.id))
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.status != PaymentStatus.PAID or payment.verified_at is None or not payment.provider_payment_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A verified payment receipt is not available")
    return PaymentReceiptResponse(booking_reference=booking.booking_reference, payment_reference=payment.provider_payment_id, provider_order_id=payment.provider_order_id, paid_at=payment.verified_at, hotel_name=booking.hotel.name, amount=payment.amount, currency=payment.currency, payment_status=payment.status, reconciliation_status=payment.reconciliation_status)


def admin_detail(db: Session, payment_id: int) -> AdminPaymentReconciliationDetail:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).options(selectinload(Payment.booking).selectinload(Booking.user), selectinload(Payment.booking).selectinload(Booking.hotel), selectinload(Payment.booking).selectinload(Booking.room_type)))
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    booking = payment.booking
    hold = db.scalar(select(inventory_service.InventoryHold).where(inventory_service.InventoryHold.hold_token == booking.hold_token)) if booking.hold_token else None
    return AdminPaymentReconciliationDetail(
        payment=PaymentOrderResponse.model_validate(payment), booking_id=booking.id, booking_reference=booking.booking_reference,
        booking_status=booking.status, customer_id=booking.user_id, customer_name=booking.user.full_name,
        hotel_id=booking.hotel_id, hotel_name=booking.hotel.name, room_type_id=booking.room_type_id,
        room_name=booking.room_type.name, expected_amount=booking.total_amount, expected_currency=booking.currency,
        hold_token=booking.hold_token, hold_status=hold.status if hold else None, hold_expires_at=hold.expires_at if hold else None,
        created_at=payment.created_at, updated_at=payment.updated_at,
    )


def process_webhook(db: Session, provider: str, event_id: str, provider_order_id: str, outcome: str, amount: Decimal, currency: str, provider_payment_id: str | None = None, failure_reason: str | None = None) -> Payment | None:
    """Idempotently record a verified provider event and settle the booking.

    Caller must verify the raw HTTP signature before invoking this function.
    """
    existing_event = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider == provider, PaymentWebhookEvent.provider_event_id == event_id))
    if existing_event:
        return db.get(Payment, existing_event.payment_id) if existing_event.payment_id else None
    payment = db.scalar(select(Payment).where(Payment.provider == provider, Payment.provider_order_id == provider_order_id).with_for_update())
    # The first lookup is optimistic. Recheck only after obtaining the payment
    # lock so two concurrently delivered callbacks serialize before inserting
    # the unique event ledger entry.
    existing_event = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider == provider, PaymentWebhookEvent.provider_event_id == event_id))
    if existing_event:
        return db.get(Payment, existing_event.payment_id) if existing_event.payment_id else None
    event = PaymentWebhookEvent(provider=provider, provider_event_id=event_id, payment_id=payment.id if payment else None)
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent callback may win the unique provider/event insert. Treat
        # that race exactly like an ordinary duplicate delivery.
        db.rollback()
        existing_event = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider == provider, PaymentWebhookEvent.provider_event_id == event_id))
        return db.get(Payment, existing_event.payment_id) if existing_event and existing_event.payment_id else None
    if payment is None:
        logger.warning("Verified callback referenced unknown payment order", extra={"provider": provider, "provider_event_id": event_id})
        db.commit()
        return None
    booking = db.get(Booking, payment.booking_id) if payment.booking_id else None
    snapshot_amount = Decimal(str(booking.price_snapshot.get("total_amount", booking.total_amount))) if booking else None
    financials_match = payment.amount == amount and payment.currency == currency
    if payment.purpose == PaymentPurpose.BOOKING:
        financials_match = financials_match and snapshot_amount == payment.amount
    elif payment.purpose == PaymentPurpose.ADVERTISING_CAMPAIGN:
        from app.models.advertising import AdvertisingCampaign
        campaign = db.get(AdvertisingCampaign, payment.advertising_campaign_id)
        financials_match = financials_match and campaign is not None and campaign.price_amount == payment.amount and campaign.currency == payment.currency
    elif payment.purpose == PaymentPurpose.SAFARI_BOOKING:
        from app.models.safari import SafariRequest
        safari_request = db.get(SafariRequest, payment.safari_request_id)
        financials_match = financials_match and safari_request is not None and safari_request.payable_amount == payment.amount and safari_request.currency == payment.currency
    if not financials_match:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Gateway amount or currency did not match the server-created payment order"
        if booking:
            notification_service.for_booking(db, booking, event_type=NotificationEventType.PAYMENT_FAILURE, event_key=event_id, title="Payment could not be verified", body=f"Payment for booking {booking.booking_reference} failed verification.", include_hotel=False)
        db.commit()
        logger.warning("Payment callback financial mismatch", extra={"payment_id": payment.id, "booking_id": payment.booking_id, "provider_event_id": event_id})
        return payment
    if outcome == "failed":
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = (failure_reason or "Payment failed")[:255]
        booking = db.get(Booking, payment.booking_id) if payment.booking_id else None
        if booking and booking.status == BookingStatus.PAYMENT_PENDING:
            booking.payment_status = PaymentStatus.FAILED
            notification_service.for_booking(db, booking, event_type=NotificationEventType.PAYMENT_FAILURE, event_key=event_id, title="Payment failed", body=f"Payment for booking {booking.booking_reference} was unsuccessful. You can retry from your booking.", include_hotel=False)
        db.commit()
        return payment
    if outcome != "succeeded":
        # Pending is a state update only; the hold remains usable for retries.
        payment.status = PaymentStatus.PENDING
        db.commit()
        return payment

    linked_payment_id = db.scalar(select(Payment.id).where(
        Payment.provider == provider,
        Payment.provider_payment_id == provider_payment_id,
        Payment.id != payment.id,
    ))
    if linked_payment_id is not None:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = "Provider payment reference is already linked to another order"
        db.commit()
        logger.warning("Rejected callback with mismatched provider payment relationship", extra={"payment_id": payment.id, "booking_id": payment.booking_id, "provider_event_id": event_id})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider payment reference is already linked to another order")

    payment.status = PaymentStatus.PAID
    payment.provider_payment_id = provider_payment_id
    payment.verified_at = datetime.now(timezone.utc)
    payment.receipt_status = "AVAILABLE"
    payment.receipt_requested_at = payment.receipt_requested_at or payment.verified_at
    if booking:
        booking.payment_status = PaymentStatus.PAID
        notification_service.for_booking(db, booking, event_type=NotificationEventType.PAYMENT_SUCCESS, event_key=event_id, title="Payment successful", body=f"Payment for booking {booking.booking_reference} was verified.", include_hotel=False)
    elif payment.verification_hotel_id:
        hotel = hotel_repository.get_hotel(db, payment.verification_hotel_id)
        if hotel and hotel.partner_id:
            notification_service.create(
                db,
                recipient_user_id=hotel.partner_id,
                event_type=NotificationEventType.VERIFICATION_PAYMENT_SUCCESS,
                dedupe_key=f"verification-payment:{payment.id}:paid",
                title="Verification fee paid",
                body="Your verification processing fee was received. Payment does not guarantee approval; submit your application for Admin review.",
                data={"hotel_id": hotel.id, "payment_id": payment.id},
            )
    elif payment.advertising_campaign_id:
        from app.services import advertising_service
        advertising_service.payment_succeeded(db, payment)
    elif payment.safari_request_id:
        from app.services import safari_service
        safari_service.payment_succeeded(db, payment)
    db.commit()  # Preserve verified funds even if inventory confirmation later fails.
    logger.info("Verified payment callback", extra={"payment_id": payment.id, "booking_id": payment.booking_id, "provider_event_id": event_id})
    if payment.purpose == PaymentPurpose.VERIFICATION_FEE:
        payment.reconciliation_status = PaymentReconciliationStatus.RESOLVED
        payment.reconciliation_resolved_at = datetime.now(timezone.utc)
        db.commit()
        return payment
    if payment.purpose == PaymentPurpose.ADVERTISING_CAMPAIGN:
        db.commit()
        return payment
    if payment.purpose == PaymentPurpose.SAFARI_BOOKING:
        db.commit()
        return payment
    return payment_reconciliation_service.attempt_confirmation(db, payment.id, reason="Initial confirmation after verified provider callback")
