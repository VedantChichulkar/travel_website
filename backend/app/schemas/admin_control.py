from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.booking import BookingStatus, CancellationStatus, CancellationType, PaymentReconciliationStatus, PaymentStatus, RefundStatus
from app.models.communication import ConversationKind, ConversationStatus, NotificationEventType, NotificationJobStatus
from app.models.user import UserRole, UserStatus
from app.models.hotel import HotelStatus


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AdminOverview(BaseModel):
    users: dict[str, int]
    hotels: dict[str, int]
    bookings: dict[str, int]
    finance: dict[str, int]
    governance: dict[str, int]


class AdminUserRead(BaseModel):
    id: int
    full_name: str
    masked_email: str
    masked_phone: str
    role: UserRole
    status: UserStatus
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime


class AdminUserStatusUpdate(BaseModel):
    status: UserStatus
    reason: str = Field(min_length=5, max_length=1000)


class AdminHotelStatusUpdate(BaseModel):
    status: HotelStatus
    reason: str = Field(min_length=5, max_length=1000)


class AdminBookingRead(BaseModel):
    id: int
    booking_reference: str
    customer_id: int
    hotel_id: int
    hotel_name: str
    status: BookingStatus
    payment_status: PaymentStatus
    check_in: date
    check_out: date
    rooms: int
    currency: str
    total_amount: Decimal
    created_at: datetime


class AdminPaymentRead(OrmModel):
    id: int
    booking_id: int | None
    provider: str
    provider_order_id: str
    provider_payment_id: str | None
    amount: Decimal
    currency: str
    status: PaymentStatus
    reconciliation_status: PaymentReconciliationStatus
    failure_reason: str | None
    verified_at: datetime | None
    reconciliation_attempts: int
    reconciliation_next_retry_at: datetime | None
    reconciliation_reason: str | None
    created_at: datetime


class AdminCancellationRead(OrmModel):
    id: int
    booking_id: int
    cancellation_type: CancellationType
    status: CancellationStatus
    reason: str
    refundable_amount: Decimal
    refunded_amount: Decimal
    requires_manual_review: bool
    created_at: datetime


class AdminRefundRead(OrmModel):
    id: int
    cancellation_id: int | None
    verification_id: int | None
    safari_request_id: int | None
    payment_id: int
    amount: Decimal
    currency: str
    status: RefundStatus
    provider_refund_id: str | None
    provider: str
    provider_status: str | None
    failure_reason: str | None
    reconciliation_reason: str | None
    execution_attempts: int
    next_retry_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AdminIssueRead(BaseModel):
    category: str
    booking_id: int
    booking_reference: str
    hotel_id: int
    status: str
    summary: str
    created_at: datetime


class AdminDisputeRead(BaseModel):
    id: int
    hotel_id: int
    customer_id: int
    booking_id: int | None
    subject: str
    kind: ConversationKind
    status: ConversationStatus
    message_count: int
    updated_at: datetime


class AdminNotificationRead(BaseModel):
    id: int
    recipient_user_id: int
    event_type: NotificationEventType
    title: str
    read_at: datetime | None
    created_at: datetime
    delivery_statuses: dict[str, NotificationJobStatus]


class AuditLogRead(OrmModel):
    id: int
    actor_user_id: int
    action: str
    target_type: str
    target_id: str
    previous_value: dict[str, object] | None
    new_value: dict[str, object] | None
    reason: str
    created_at: datetime


class AdminReason(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class SettlementReleaseRequest(AdminReason):
    pass
