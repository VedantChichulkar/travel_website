import re
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.booking import Booking
from app.models.communication import NotificationEventType
from app.models.safari import SafariRequest
from app.models.support import SupportEnquiry, SupportEnquiryType
from app.models.user import User, UserRole, UserStatus
from app.schemas.support import AdminSupportEnquiry, SupportEnquiryCreate, SupportEnquiryReceipt
from app.services import notification_service


NEXT_STEP = "Maharashtra Tourist Places support has received your enquiry. Keep the reference for any follow-up."


def contact_config() -> dict[str, str | None]:
    email = settings.PUBLIC_SUPPORT_EMAIL.strip() or None
    phone = settings.PUBLIC_WHATSAPP_NUMBER.strip()
    whatsapp = None
    if phone and re.fullmatch(r"\+?[1-9]\d{7,14}", phone):
        whatsapp = f"https://wa.me/{phone.lstrip('+')}"
    return {"email": email, "whatsapp_url": whatsapp}


def find_by_idempotency(db: Session, key: str) -> SupportEnquiry | None:
    return db.scalar(select(SupportEnquiry).where(SupportEnquiry.idempotency_key == key))


def _reference(db: Session) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(5):
        value = f"ENQ-{day}-{secrets.token_hex(4).upper()}"
        if db.scalar(select(SupportEnquiry.id).where(SupportEnquiry.reference == value)) is None:
            return value
    raise RuntimeError("Could not allocate enquiry reference")


def _resolve_owned_reference(db: Session, user: User | None, data: SupportEnquiryCreate) -> tuple[int | None, int | None]:
    if user is None or not data.customer_reference:
        return None, None
    if user.role not in {UserRole.CUSTOMER, UserRole.USER}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    if data.enquiry_type in {SupportEnquiryType.BOOKING_HELP, SupportEnquiryType.CANCELLATION_REFUND}:
        booking = db.scalar(select(Booking).where(Booking.booking_reference == data.customer_reference, Booking.user_id == user.id))
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
        return booking.id, None
    if data.enquiry_type == SupportEnquiryType.SAFARI_HELP:
        request = db.scalar(select(SafariRequest).where(SafariRequest.request_reference == data.customer_reference, SafariRequest.customer_id == user.id))
        if request is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
        return None, request.id
    return None, None


def create_enquiry(db: Session, data: SupportEnquiryCreate, user: User | None) -> SupportEnquiry:
    existing = find_by_idempotency(db, data.idempotency_key)
    if existing:
        return existing
    booking_id, safari_request_id = _resolve_owned_reference(db, user, data)
    item = SupportEnquiry(
        reference=_reference(db), idempotency_key=data.idempotency_key, user_id=user.id if user else None,
        enquiry_type=data.enquiry_type, name=data.name.strip(), email=str(data.email).lower(), mobile=data.mobile,
        message=data.message.strip(), customer_reference=data.customer_reference,
        property_name=data.property_name.strip() if data.property_name else None,
        location=data.location.strip() if data.location else None,
        booking_id=booking_id, safari_request_id=safari_request_id,
    )
    savepoint = db.begin_nested()
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        savepoint.rollback()
        duplicate = find_by_idempotency(db, data.idempotency_key)
        if duplicate:
            return duplicate
        raise
    else:
        savepoint.commit()

    admins = db.scalars(select(User).where(User.role == UserRole.ADMIN, User.status == UserStatus.ACTIVE, User.is_active.is_(True))).all()
    for admin in admins:
        notification_service.create(
            db, recipient_user_id=admin.id, event_type=NotificationEventType.SUPPORT_ENQUIRY_RECEIVED,
            dedupe_key=f"SUPPORT_ENQUIRY_RECEIVED:{item.reference}", title="New support enquiry",
            body=f"A {item.enquiry_type.value.replace('_', ' ').title()} enquiry was received with reference {item.reference}.",
            data={"enquiry_reference": item.reference, "enquiry_type": item.enquiry_type.value}, channels=(),
        )
    db.commit(); db.refresh(item)
    return item


def receipt(item: SupportEnquiry) -> SupportEnquiryReceipt:
    return SupportEnquiryReceipt(reference=item.reference, enquiry_type=item.enquiry_type, created_at=item.created_at, next_step=NEXT_STEP)


def admin_list(db: Session) -> list[SupportEnquiry]:
    return list(db.scalars(select(SupportEnquiry).order_by(SupportEnquiry.created_at.desc(), SupportEnquiry.id.desc()).limit(200)))


def admin_get(db: Session, reference: str) -> SupportEnquiry:
    item = db.scalar(select(SupportEnquiry).where(SupportEnquiry.reference == reference))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enquiry not found")
    return item


def admin_view(item: SupportEnquiry) -> AdminSupportEnquiry:
    return AdminSupportEnquiry(
        reference=item.reference, enquiry_type=item.enquiry_type, status=item.status,
        name=item.name, email=item.email, mobile=item.mobile, message=item.message,
        customer_reference=item.customer_reference, property_name=item.property_name,
        location=item.location, created_at=item.created_at,
    )
