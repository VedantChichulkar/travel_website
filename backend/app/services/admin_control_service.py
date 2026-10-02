from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from fastapi import HTTPException, status

from app.models.booking import Booking, BookingStatus, Cancellation, CancellationStatus, CancellationType, Payment, PaymentPurpose, PaymentReconciliationStatus, PaymentStatus, Refund, RefundStatus
from app.models.advertising import AdvertisingCampaign, AdvertisingCampaignStatus
from app.models.communication import Conversation, ConversationKind, ConversationStatus, Notification, NotificationJob, NotificationJobStatus
from app.models.hotel import Hotel, HotelStatus, RoomType, RoomTypeStatus
from app.models.hotel_verification import HotelVerification, VerificationStatus
from app.models.review import ReviewChallenge, ReviewChallengeStatus
from app.models.safari import SafariRequest, SafariRequestStatus
from app.models.settlement import Settlement, SettlementStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.admin_control import AdminBookingRead, AdminCancellationRead, AdminDisputeRead, AdminIssueRead, AdminNotificationRead, AdminOverview, AdminPaymentRead, AdminRefundRead, AdminUserRead
from app.services import audit_service


def _count(db: Session, model, *criteria) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)


def overview(db: Session) -> AdminOverview:
    return AdminOverview(
        users={"total": _count(db, User), "customers": _count(db, User, User.role.in_((UserRole.CUSTOMER, UserRole.USER))), "partners": _count(db, User, User.role == UserRole.HOTEL_PARTNER), "suspended": _count(db, User, User.status == UserStatus.SUSPENDED)},
        hotels={"total": _count(db, Hotel), "active": _count(db, Hotel, Hotel.status == HotelStatus.ACTIVE), "pending": _count(db, Hotel, Hotel.status == HotelStatus.PENDING), "suspended": _count(db, Hotel, Hotel.status == HotelStatus.SUSPENDED)},
        bookings={"total": _count(db, Booking), "confirmed": _count(db, Booking, Booking.status == BookingStatus.CONFIRMED), "no_shows": _count(db, Booking, Booking.status == BookingStatus.NO_SHOW), "operational_issues": _count(db, Booking, Booking.status == BookingStatus.CHECK_IN_ISSUE)},
        finance={"payment_failures": _count(db, Payment, Payment.status == PaymentStatus.FAILED), "payment_reconciliations": _count(db, Payment, Payment.reconciliation_status.in_((PaymentReconciliationStatus.CONFIRMATION_REQUIRED, PaymentReconciliationStatus.REFUND_REQUIRED, PaymentReconciliationStatus.MANUAL_REVIEW))), "refund_reviews": _count(db, Refund, Refund.status.in_((RefundStatus.RETRY_REQUIRED, RefundStatus.RECONCILIATION_REQUIRED, RefundStatus.MANUAL_REVIEW, RefundStatus.FAILED))), "settlements_on_hold": _count(db, Settlement, Settlement.status == SettlementStatus.ON_HOLD), "settlements_processing": _count(db, Settlement, Settlement.status == SettlementStatus.PROCESSING)},
        governance={"verifications_pending": _count(db, HotelVerification, HotelVerification.verification_status == VerificationStatus.PENDING), "rooms_pending": _count(db, RoomType, RoomType.status == RoomTypeStatus.PENDING), "safaris_awaiting_action": _count(db, SafariRequest, SafariRequest.status.in_((SafariRequestStatus.AVAILABILITY_REQUESTED, SafariRequestStatus.CHECKING_AVAILABILITY, SafariRequestStatus.DETAILS_SUBMITTED, SafariRequestStatus.BOOKING_IN_PROGRESS))), "advertising_pending": _count(db, AdvertisingCampaign, AdvertisingCampaign.status == AdvertisingCampaignStatus.PENDING_REVIEW), "review_challenges": _count(db, ReviewChallenge, ReviewChallenge.status == ReviewChallengeStatus.OPEN), "open_disputes": _count(db, Conversation, Conversation.kind == ConversationKind.DISPUTE, Conversation.status == ConversationStatus.OPEN), "delivery_jobs_unavailable": _count(db, NotificationJob, NotificationJob.status == NotificationJobStatus.PROVIDER_UNAVAILABLE)},
    )


def _mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"


def _mask_phone(value: str) -> str:
    return f"***{value[-4:]}" if len(value) >= 4 else "***"


def users(db: Session, *, role: UserRole | None = None, user_status: UserStatus | None = None, search: str | None = None, limit: int = 200) -> list[AdminUserRead]:
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if user_status:
        query = query.where(User.status == user_status)
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.where(or_(func.lower(User.full_name).like(term), func.lower(User.email).like(term)))
    items = list(db.scalars(query.order_by(User.created_at.desc()).limit(limit)))
    return [AdminUserRead(id=item.id, full_name=item.full_name, masked_email=_mask_email(item.email), masked_phone=_mask_phone(item.phone), role=item.role, status=item.status, is_active=item.is_active, is_email_verified=item.is_email_verified, is_phone_verified=item.is_phone_verified, created_at=item.created_at) for item in items]


def update_user_status(db: Session, admin: User, user_id: int, new_status: UserStatus, reason: str) -> AdminUserRead:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and new_status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Administrators cannot suspend their own active session")
    old = {"status": user.status.value, "is_active": user.is_active}
    user.status = new_status
    user.is_active = new_status == UserStatus.ACTIVE
    audit_service.record(db, actor=admin, action="USER_STATUS_CHANGED", target_type="USER", target_id=user.id, reason=reason, previous_value=old, new_value={"status": user.status.value, "is_active": user.is_active})
    db.commit(); db.refresh(user)
    return AdminUserRead(id=user.id, full_name=user.full_name, masked_email=_mask_email(user.email), masked_phone=_mask_phone(user.phone), role=user.role, status=user.status, is_active=user.is_active, is_email_verified=user.is_email_verified, is_phone_verified=user.is_phone_verified, created_at=user.created_at)


def update_hotel_status(db: Session, admin: User, hotel_id: int, new_status: HotelStatus, reason: str) -> Hotel:
    hotel = db.scalar(select(Hotel).where(Hotel.id == hotel_id).with_for_update())
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    change_hotel_status(db, admin, hotel, new_status, reason=reason)
    db.commit(); db.refresh(hotel)
    return hotel


def change_hotel_status(
    db: Session,
    admin: User,
    hotel: Hotel,
    new_status: HotelStatus,
    *,
    reason: str,
    action: str = "HOTEL_STATUS_CHANGED",
    target_type: str = "HOTEL",
    target_id: int | str | None = None,
    previous_value: dict[str, object] | None = None,
    new_value: dict[str, object] | None = None,
) -> None:
    """Authoritative, transaction-neutral hotel governance mutation."""
    old = hotel.status
    hotel.status = new_status
    audit_service.record(
        db,
        actor=admin,
        action=action,
        target_type=target_type,
        target_id=target_id if target_id is not None else hotel.id,
        reason=reason,
        previous_value=previous_value or {"status": old.value},
        new_value=new_value or {"status": new_status.value},
    )


def bookings(db: Session, *, booking_status: BookingStatus | None = None, hotel_id: int | None = None, limit: int = 200) -> list[AdminBookingRead]:
    query = select(Booking, Hotel.name).join(Hotel, Hotel.id == Booking.hotel_id)
    if booking_status:
        query = query.where(Booking.status == booking_status)
    if hotel_id:
        query = query.where(Booking.hotel_id == hotel_id)
    rows = db.execute(query.order_by(Booking.created_at.desc()).limit(limit)).all()
    return [AdminBookingRead(id=item.id, booking_reference=item.booking_reference, customer_id=item.user_id, hotel_id=item.hotel_id, hotel_name=hotel_name, status=item.status, payment_status=item.payment_status, check_in=item.check_in, check_out=item.check_out, rooms=item.rooms, currency=item.currency, total_amount=item.total_amount, created_at=item.created_at) for item, hotel_name in rows]


def payments(db: Session, *, payment_status: PaymentStatus | None = None, limit: int = 200) -> list[Payment]:
    query = select(Payment).where(Payment.purpose == PaymentPurpose.BOOKING)
    if payment_status:
        query = query.where(Payment.status == payment_status)
    return list(db.scalars(query.order_by(Payment.created_at.desc()).limit(limit)))


def cancellations(db: Session, *, cancellation_status: CancellationStatus | None = None, limit: int = 200) -> list[Cancellation]:
    query = select(Cancellation)
    if cancellation_status:
        query = query.where(Cancellation.status == cancellation_status)
    return list(db.scalars(query.order_by(Cancellation.created_at.desc()).limit(limit)))


def refunds(db: Session, *, refund_status: RefundStatus | None = None, limit: int = 200) -> list[Refund]:
    query = select(Refund)
    if refund_status:
        query = query.where(Refund.status == refund_status)
    return list(db.scalars(query.order_by(Refund.created_at.desc()).limit(limit)))


def no_shows(db: Session, limit: int = 200) -> list[AdminIssueRead]:
    items = list(db.scalars(select(Booking).where(Booking.status == BookingStatus.NO_SHOW).order_by(Booking.updated_at.desc()).limit(limit)))
    return [AdminIssueRead(category="NO_SHOW", booking_id=item.id, booking_reference=item.booking_reference, hotel_id=item.hotel_id, status=item.status.value, summary="No-show recorded; review cancellation and settlement impact.", created_at=item.updated_at) for item in items]


def hotel_failures(db: Session, limit: int = 200) -> list[AdminIssueRead]:
    issues = list(db.scalars(select(Booking).where(Booking.status == BookingStatus.CHECK_IN_ISSUE).order_by(Booking.updated_at.desc()).limit(limit)))
    caused = list(db.scalars(select(Cancellation).where(Cancellation.cancellation_type == CancellationType.HOTEL_CAUSED).options(selectinload(Cancellation.booking)).order_by(Cancellation.created_at.desc()).limit(limit)))
    result = [AdminIssueRead(category="CHECK_IN_ISSUE", booking_id=item.id, booking_reference=item.booking_reference, hotel_id=item.hotel_id, status=item.status.value, summary="Hotel-reported check-in or operational issue.", created_at=item.updated_at) for item in issues]
    result.extend(AdminIssueRead(category="HOTEL_CAUSED_CANCELLATION", booking_id=item.booking_id, booking_reference=item.booking.booking_reference, hotel_id=item.booking.hotel_id, status=item.status.value, summary="Hotel-caused cancellation requiring refund oversight.", created_at=item.created_at) for item in caused)
    return sorted(result, key=lambda item: item.created_at, reverse=True)[:limit]


def disputes(db: Session, limit: int = 200) -> list[AdminDisputeRead]:
    items = list(db.scalars(select(Conversation).where(Conversation.kind == ConversationKind.DISPUTE).options(selectinload(Conversation.messages)).order_by(Conversation.updated_at.desc()).limit(limit)))
    return [AdminDisputeRead(id=item.id, hotel_id=item.hotel_id, customer_id=item.customer_id, booking_id=item.booking_id, subject=item.subject, kind=item.kind, status=item.status, message_count=len(item.messages), updated_at=item.updated_at) for item in items]


def notifications(db: Session, limit: int = 200) -> list[AdminNotificationRead]:
    items = list(db.scalars(select(Notification).options(selectinload(Notification.jobs)).order_by(Notification.created_at.desc()).limit(limit)))
    return [AdminNotificationRead(id=item.id, recipient_user_id=item.recipient_user_id, event_type=item.event_type, title=item.title, read_at=item.read_at, created_at=item.created_at, delivery_statuses={job.channel.value: job.status for job in item.jobs}) for item in items]
