import re
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Self

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.booking import BookingStatus, CancellationStatus, CancellationType, PaymentPurpose, PaymentReconciliationStatus, PaymentStatus, RefundStatus, SettlementImpactStatus
from app.models.hotel import BookingGatewayStatus, InventoryHoldStatus
from app.core.config import settings


PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BookingStayRequest(BaseModel):
    hotel_id: int = Field(gt=0)
    room_type_id: int = Field(gt=0)
    check_in: date = Field(validation_alias=AliasChoices("check_in", "check_in_date"))
    check_out: date = Field(validation_alias=AliasChoices("check_out", "check_out_date"))
    rooms: int = Field(ge=1, le=10, validation_alias=AliasChoices("rooms", "rooms_booked"))
    adults: int = Field(ge=1, le=50)
    children: int = Field(default=0, ge=0, le=50)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if self.check_in < date.today():
            raise ValueError("check_in cannot be in the past")
        return self


class InventoryHoldCreate(BookingStayRequest):
    """Authenticated caller's temporary capacity reservation; no payment or booking is created."""


class InventoryHoldResponse(OrmModel):
    hold_token: str
    hotel_id: int
    room_type_id: int
    check_in: date
    check_out: date
    rooms: int
    expires_at: datetime
    status: InventoryHoldStatus
    booking_mode: BookingGatewayStatus | None = None


class TravellerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=0, le=120)
    gender: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    phone: str | None = None
    is_primary: bool = Field(default=False, validation_alias=AliasChoices("is_primary", "is_primary_guest"))

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"[\s()-]", "", value)
        if not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("phone must use E.164 format")
        return normalized


class BookingCreate(BookingStayRequest):
    hold_token: str = Field(min_length=32, max_length=64)
    travellers: list[TravellerCreate] = Field(min_length=1, max_length=60)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=64)

    @model_validator(mode="after")
    def validate_travellers(self) -> Self:
        if len(self.travellers) != self.adults + self.children:
            raise ValueError("one traveller is required for each adult and child")
        if sum(item.is_primary for item in self.travellers) != 1:
            raise ValueError("exactly one traveller must be primary")
        return self


class NightlyPrice(BaseModel):
    date: date
    unit_price: Decimal
    rooms: int
    amount: Decimal


class BookingQuote(BaseModel):
    hotel_id: int
    room_type_id: int
    check_in: date
    check_out: date
    rooms: int
    adults: int
    children: int
    nights: int
    currency: str
    nightly_prices: list[NightlyPrice]
    subtotal: Decimal
    taxes: Decimal
    platform_fee: Decimal
    discount: Decimal
    total_amount: Decimal
    booking_mode: BookingGatewayStatus


class TravellerResponse(OrmModel):
    id: int
    full_name: str
    age: int
    gender: str | None
    email: EmailStr | None
    phone: str | None
    is_primary: bool


class StatusHistoryResponse(OrmModel):
    id: int
    old_status: BookingStatus | None
    new_status: BookingStatus
    changed_by_user_id: int | None
    note: str | None
    created_at: datetime


class BookingHotelSummary(OrmModel):
    id: int
    name: str
    slug: str
    city: str
    state: str
    country: str


class BookingRoomSummary(OrmModel):
    id: int
    name: str
    bed_type: str
    currency: str


class BookingResponse(OrmModel):
    id: int
    booking_reference: str
    user_id: int
    hotel_id: int
    room_type_id: int
    hotel: BookingHotelSummary
    room: BookingRoomSummary = Field(validation_alias="room_type")
    check_in: date
    check_out: date
    rooms: int
    adults: int
    children: int
    nights: int
    currency: str
    subtotal: Decimal
    taxes: Decimal
    platform_fee: Decimal
    discount: Decimal
    total_amount: Decimal
    hold_token: str | None
    room_snapshot: dict[str, object]
    price_snapshot: dict[str, object]
    policy_snapshot: dict[str, object]
    booking_mode: BookingGatewayStatus
    request_expires_at: datetime | None
    request_decided_at: datetime | None
    request_decision_reason: str | None
    payment_expires_at: datetime | None
    status: BookingStatus
    payment_status: PaymentStatus
    travellers: list[TravellerResponse]
    status_history: list[StatusHistoryResponse]
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int


class BookingRequestDecision(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class PaymentOrderResponse(OrmModel):
    id: int
    booking_id: int | None
    verification_hotel_id: int | None
    advertising_campaign_id: int | None
    safari_request_id: int | None
    purpose: PaymentPurpose
    provider: str
    provider_order_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    reconciliation_status: PaymentReconciliationStatus
    provider_payment_id: str | None
    failure_reason: str | None
    verified_at: datetime | None
    receipt_status: str
    reconciliation_attempts: int
    reconciliation_next_retry_at: datetime | None
    reconciliation_reason: str | None
    created_at: datetime
    checkout_key_id: str | None = None

    @model_validator(mode="after")
    def expose_public_checkout_key(self) -> Self:
        if self.provider == "RAZORPAY":
            self.checkout_key_id = settings.RAZORPAY_KEY_ID
        return self


class CheckoutConfirmation(BaseModel):
    provider_order_id: str = Field(min_length=1, max_length=100)
    provider_payment_id: str = Field(min_length=1, max_length=100)
    signature: str = Field(min_length=16, max_length=256)


class PaymentHistoryResponse(BaseModel):
    items: list[PaymentOrderResponse]
    total: int


class CustomerPaymentHistoryItem(PaymentOrderResponse):
    booking_reference: str
    hotel_name: str


class CustomerPaymentHistoryResponse(BaseModel):
    items: list[CustomerPaymentHistoryItem]
    total: int


class PaymentReceiptResponse(BaseModel):
    booking_reference: str
    payment_reference: str
    provider_order_id: str
    paid_at: datetime
    hotel_name: str
    amount: Decimal
    currency: str
    payment_status: PaymentStatus
    reconciliation_status: PaymentReconciliationStatus


class ReconciliationActionType(str, Enum):
    RETRY_CONFIRMATION = "RETRY_CONFIRMATION"
    REFUND_REQUIRED = "REFUND_REQUIRED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ReconciliationActionRequest(BaseModel):
    action: ReconciliationActionType
    reason: str = Field(min_length=5, max_length=2000)


class AdminPaymentReconciliationDetail(BaseModel):
    payment: PaymentOrderResponse
    booking_id: int
    booking_reference: str
    booking_status: BookingStatus
    customer_id: int
    customer_name: str
    hotel_id: int
    hotel_name: str
    room_type_id: int
    room_name: str
    expected_amount: Decimal
    expected_currency: str
    hold_token: str | None
    hold_status: InventoryHoldStatus | None
    hold_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentWebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    provider_order_id: str = Field(min_length=1, max_length=100)
    outcome: str = Field(pattern="^(succeeded|failed|pending)$")
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    provider_payment_id: str | None = Field(default=None, max_length=100)
    failure_reason: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def require_succeeded_reference(self) -> Self:
        if self.outcome == "succeeded" and not self.provider_payment_id:
            raise ValueError("provider_payment_id is required for a succeeded payment")
        return self


class CancellationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class HotelCausedCancellationRequest(CancellationRequest):
    pass


class ManualRefundDecisionRequest(BaseModel):
    approved_amount: Decimal = Field(ge=0)
    note: str = Field(min_length=5, max_length=2000)


class RefundResponse(OrmModel):
    id: int
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
    provider_accepted_at: datetime | None
    completed_at: datetime | None
    settlement_impact_status: SettlementImpactStatus
    created_at: datetime
    updated_at: datetime


class RefundWebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    provider_refund_id: str = Field(min_length=1, max_length=100)
    outcome: str = Field(pattern="^(pending|completed|failed|unknown)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    failure_reason: str | None = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def normalize_refund_currency(cls, value: str) -> str:
        return value.upper()


class RefundActionType(str, Enum):
    RETRY = "RETRY"
    RECONCILE = "RECONCILE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RefundActionRequest(BaseModel):
    action: RefundActionType
    reason: str = Field(min_length=5, max_length=2000)


class AdminRefundDetail(BaseModel):
    refund: RefundResponse
    subject_type: str = "BOOKING"
    verification_id: int | None = None
    safari_request_id: int | None = None
    subject_reference: str | None = None
    booking_id: int | None
    booking_reference: str | None
    booking_status: BookingStatus | None
    customer_id: int | None
    customer_name: str | None
    hotel_id: int | None
    hotel_name: str | None
    cancellation_id: int | None
    cancellation_type: CancellationType | None
    cancellation_status: CancellationStatus | None
    cancellation_reason: str | None
    approved_refund_amount: Decimal
    refunded_amount: Decimal
    payment_id: int
    captured_amount: Decimal
    payment_status: PaymentStatus


class CancellationResponse(OrmModel):
    id: int
    booking_id: int
    cancellation_type: CancellationType
    status: CancellationStatus
    reason: str
    policy_snapshot: dict[str, object]
    refundable_amount: Decimal
    refunded_amount: Decimal
    requires_manual_review: bool
    created_at: datetime
    updated_at: datetime
    refunds: list[RefundResponse]


class OperationLookupRequest(BaseModel):
    booking_id: int | None = Field(default=None, gt=0)
    booking_reference: str | None = Field(default=None, min_length=6, max_length=32)
    qr_token: str | None = Field(default=None, min_length=16, max_length=64)

    @model_validator(mode="after")
    def exactly_one_lookup_key(self) -> Self:
        if sum(value is not None for value in (self.booking_id, self.booking_reference, self.qr_token)) != 1:
            raise ValueError("Provide exactly one booking_id, booking_reference or qr_token")
        return self


class CheckInRequest(BaseModel):
    assigned_room: str = Field(min_length=1, max_length=80)


class CheckInIssueType(str, Enum):
    MISSING_OR_INVALID_ID = "MISSING_OR_INVALID_ID"
    BOOKING_MISMATCH = "BOOKING_MISMATCH"
    OPERATIONAL_VERIFICATION = "OPERATIONAL_VERIFICATION"


class CheckInIssueRequest(BaseModel):
    issue_type: CheckInIssueType
    reason: str = Field(min_length=3, max_length=2000)


class OperationBookingResponse(OrmModel):
    id: int
    booking_reference: str
    operation_qr_token: str | None
    status: BookingStatus
    check_in: date
    check_out: date
    rooms: int
    assigned_room: str | None
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    room_snapshot: dict[str, object]
    primary_guest_name: str | None = None
    status_note: str | None = None
    is_system_generated: bool = False
    no_show_reminder_sent_at: datetime | None = None
    no_show_eligible_at: datetime | None = None
    auto_checkout_eligible_at: datetime | None = None
    can_check_in: bool = False
    can_check_out: bool = False
    can_report_no_show: bool = False
    requires_financial_review: bool = False

    @classmethod
    def from_booking(cls, booking: object) -> "OperationBookingResponse":
        from app.services.hotel_operations_service import operation_metadata

        travellers = getattr(booking, "travellers", [])
        primary = next((item.full_name for item in travellers if item.is_primary), None)
        return cls.model_validate(booking, from_attributes=True).model_copy(
            update={"primary_guest_name": primary, **operation_metadata(booking)}
        )


class OperationBoardResponse(BaseModel):
    generated_at: datetime
    arrivals: list[OperationBookingResponse]
    checked_in: list[OperationBookingResponse]
    upcoming_checkouts: list[OperationBookingResponse]
    no_show_actions: list[OperationBookingResponse]
    check_in_issues: list[OperationBookingResponse]
