import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.core.config import settings
from app.core.permission import require_customer
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingListResponse, BookingQuote, BookingResponse, BookingStayRequest, CancellationRequest, CancellationResponse, CheckoutConfirmation, CustomerPaymentHistoryResponse, InventoryHoldCreate, InventoryHoldResponse, PaymentHistoryResponse, PaymentOrderResponse, PaymentReceiptResponse, PaymentWebhookPayload, RefundWebhookPayload
from app.services import booking_service, cancellation_service, payment_provider, payment_service, refund_execution_service
from app.schemas.review import ReviewCreate, ReviewRead
from app.services import review_service


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{booking_id}/review", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(booking_id: int, data: ReviewCreate, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return review_service.create_review(db, current_user, booking_id, data)


@router.get("/{booking_id}/review", response_model=ReviewRead)
def get_review(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return review_service.get_customer_review(db, current_user, booking_id)


@router.post("/quote", response_model=BookingQuote)
def quote_booking(data: BookingStayRequest, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return booking_service.quote(db, data)


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(data: BookingCreate, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return booking_service.create_booking(db, current_user, data)


@router.post("/holds", response_model=InventoryHoldResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_hold(data: InventoryHoldCreate, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    """Create a temporary capacity hold; this deliberately does not create a booking or payment."""
    return booking_service.create_inventory_hold(db, current_user, data)


@router.get("/me", response_model=BookingListResponse)
def list_my_bookings(db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return booking_service.list_my_bookings(db, current_user)


@router.get("/payments/me", response_model=CustomerPaymentHistoryResponse)
def list_my_payments(db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    items = payment_service.list_customer_payment_history(db, current_user)
    return CustomerPaymentHistoryResponse(items=items, total=len(items))


@router.post("/{booking_id}/payments/orders", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
def create_payment_order(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return payment_service.create_order(db, current_user, booking_id)


@router.get("/{booking_id}/payments", response_model=PaymentHistoryResponse)
def payment_history(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    items = payment_service.list_booking_payments(db, current_user, booking_id)
    return PaymentHistoryResponse(items=items, total=len(items))


@router.get("/{booking_id}/payments/{payment_id}/receipt", response_model=PaymentReceiptResponse)
def payment_receipt(booking_id: int, payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return payment_service.receipt(db, current_user, booking_id, payment_id)


@router.post("/{booking_id}/cancellations", response_model=CancellationResponse, status_code=status.HTTP_201_CREATED)
def request_cancellation(booking_id: int, data: CancellationRequest, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return cancellation_service.request_customer_cancellation(db, current_user, booking_id, data.reason)


@router.get("/{booking_id}/cancellation", response_model=CancellationResponse | None)
def cancellation_status(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return cancellation_service.get_cancellation(db, booking_id, current_user)


@router.post("/payments/{payment_id}/confirm", response_model=PaymentOrderResponse)
def confirm_checkout(payment_id: int, data: CheckoutConfirmation, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return payment_service.confirm_checkout(db, current_user, payment_id, data.provider_order_id, data.provider_payment_id, data.signature)


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_customer)):
    return booking_service.get_booking(db, current_user, booking_id)


@router.post("/payments/webhooks/{provider}", status_code=status.HTTP_200_OK)
async def payment_webhook(provider: str, request: Request, db: Session = Depends(get_db), x_vayora_signature: str | None = Header(default=None), x_razorpay_signature: str | None = Header(default=None)):
    if settings.PAYMENT_MODE == "disabled" or provider != settings.PAYMENT_PROVIDER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment provider not configured")
    raw_payload = await request.body()
    if len(raw_payload) > 1_000_000:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Webhook payload too large")
    signature = x_razorpay_signature if provider == "RAZORPAY" else x_vayora_signature
    if not payment_service.verify_webhook_signature(raw_payload, signature):
        logger.warning("Rejected payment callback with invalid signature", extra={"provider": provider})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payment webhook signature")
    if provider == "RAZORPAY":
        payment = payment_service.process_razorpay_payment_webhook(db, raw_payload)
    else:
        payload = PaymentWebhookPayload.model_validate_json(raw_payload)
        payment = payment_service.process_webhook(db, provider, **payload.model_dump())
    return {"accepted": True, "payment_id": payment.id if payment else None}


@router.post("/payments/refunds/webhooks/{provider}", status_code=status.HTTP_200_OK)
async def refund_webhook(provider: str, request: Request, db: Session = Depends(get_db), x_vayora_signature: str | None = Header(default=None), x_razorpay_signature: str | None = Header(default=None)):
    if settings.PAYMENT_MODE == "disabled" or provider != settings.PAYMENT_PROVIDER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment provider not configured")
    raw_payload = await request.body()
    if len(raw_payload) > 1_000_000:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Webhook payload too large")
    signature = x_razorpay_signature if provider == "RAZORPAY" else x_vayora_signature
    if not payment_provider.configured_provider().verify_refund_webhook(raw_payload, signature):
        logger.warning("Rejected refund callback with invalid signature", extra={"provider": provider})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refund webhook signature")
    if provider == "RAZORPAY":
        refund = payment_service.process_razorpay_refund_webhook(db, raw_payload)
    else:
        payload = RefundWebhookPayload.model_validate_json(raw_payload)
        refund = refund_execution_service.process_webhook(db, provider, **payload.model_dump())
    return {"accepted": True, "refund_id": refund.id if refund else None}
