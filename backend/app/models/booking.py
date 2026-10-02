from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.hotel import BookingGatewayStatus

if TYPE_CHECKING:
    from app.models.hotel import Hotel, RoomType
    from app.models.user import User


class BookingStatus(str, Enum):
    PENDING = "PENDING"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    CANCELLED = "CANCELLED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"
    CHECK_IN_ISSUE = "CHECK_IN_ISSUE"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"
    NO_SHOW = "NO_SHOW"
    REQUEST_REJECTED = "REQUEST_REJECTED"
    REQUEST_EXPIRED = "REQUEST_EXPIRED"


class PaymentStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"


class PaymentPurpose(str, Enum):
    BOOKING = "BOOKING"
    VERIFICATION_FEE = "VERIFICATION_FEE"
    ADVERTISING_CAMPAIGN = "ADVERTISING_CAMPAIGN"
    SAFARI_BOOKING = "SAFARI_BOOKING"


class PaymentReconciliationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    REFUND_REQUIRED = "REFUND_REQUIRED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    RESOLVED = "RESOLVED"


class CancellationType(str, Enum):
    CUSTOMER = "CUSTOMER"
    HOTEL_CAUSED = "HOTEL_CAUSED"
    NO_SHOW = "NO_SHOW"
    PAYMENT_RECONCILIATION = "PAYMENT_RECONCILIATION"


class CancellationStatus(str, Enum):
    REQUESTED = "REQUESTED"
    REFUND_PENDING = "REFUND_PENDING"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class RefundStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRY_REQUIRED = "RETRY_REQUIRED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class SettlementImpactStatus(str, Enum):
    PENDING = "PENDING"
    RECORDED = "RECORDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_bookings_user_idempotency_key"),
        CheckConstraint("check_out > check_in", name="ck_bookings_stay_dates"),
        CheckConstraint("rooms >= 1", name="ck_bookings_rooms"),
        CheckConstraint("adults >= 1 AND children >= 0", name="ck_bookings_guests"),
        CheckConstraint("nights >= 1", name="ck_bookings_nights"),
        CheckConstraint("subtotal >= 0 AND taxes >= 0 AND platform_fee >= 0 AND discount >= 0 AND total_amount >= 0", name="ck_bookings_amounts"),
        Index("ix_bookings_user_created", "user_id", "created_at"),
        Index("ix_bookings_request_queue", "booking_mode", "status", "request_expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    adults: Mapped[int] = mapped_column(Integer, nullable=False)
    children: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    nights: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxes: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    hold_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    room_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    price_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    policy_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    booking_mode: Mapped[BookingGatewayStatus] = mapped_column(
        SqlEnum(BookingGatewayStatus, name="booking_gateway_status", native_enum=False),
        nullable=False,
        default=BookingGatewayStatus.ACTIVE,
        server_default=BookingGatewayStatus.ACTIVE.value,
    )
    request_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    request_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_decision_reason: Mapped[str | None] = mapped_column(Text)
    payment_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[BookingStatus] = mapped_column(SqlEnum(BookingStatus, name="booking_status"), nullable=False, default=BookingStatus.PAYMENT_PENDING, server_default=BookingStatus.PAYMENT_PENDING.value, index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(SqlEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.NOT_STARTED, server_default=PaymentStatus.NOT_STARTED.value, index=True)
    operation_qr_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    assigned_room: Mapped[str | None] = mapped_column(String(80))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    hotel: Mapped[Hotel] = relationship("Hotel", foreign_keys=[hotel_id])
    room_type: Mapped[RoomType] = relationship("RoomType", foreign_keys=[room_type_id])
    travellers: Mapped[list[BookingTraveller]] = relationship(back_populates="booking", cascade="all, delete-orphan", order_by="BookingTraveller.id")
    status_history: Mapped[list[BookingStatusHistory]] = relationship(back_populates="booking", cascade="all, delete-orphan", order_by="BookingStatusHistory.id")
    payments: Mapped[list[Payment]] = relationship(back_populates="booking", cascade="all, delete-orphan", order_by="Payment.id")
    cancellation: Mapped[Cancellation | None] = relationship(back_populates="booking", cascade="all, delete-orphan", uselist=False)


class Payment(Base):
    """A server-created payment attempt; provider card/UPI credentials are never stored."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount"),
        UniqueConstraint("provider", "provider_order_id", name="uq_payments_provider_order"),
        UniqueConstraint("provider", "provider_payment_id", name="uq_payments_provider_payment"),
        Index("ix_payments_booking_created", "booking_id", "created_at"),
        Index("ix_payments_verification_hotel_created", "verification_hotel_id", "created_at"),
        Index("ix_payments_ad_campaign_created", "advertising_campaign_id", "created_at"),
        Index("ix_payments_safari_request_created", "safari_request_id", "created_at"),
        CheckConstraint(
            "(purpose = 'BOOKING' AND booking_id IS NOT NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR "
            "(purpose = 'VERIFICATION_FEE' AND booking_id IS NULL AND verification_hotel_id IS NOT NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR "
            "(purpose = 'ADVERTISING_CAMPAIGN' AND booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NOT NULL AND safari_request_id IS NULL) OR "
            "(purpose = 'SAFARI_BOOKING' AND booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NOT NULL)",
            name="ck_payments_single_subject",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True, index=True)
    verification_hotel_id: Mapped[int | None] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=True, index=True)
    advertising_campaign_id: Mapped[int | None] = mapped_column(ForeignKey("advertising_campaigns.id", ondelete="RESTRICT"), nullable=True, index=True)
    safari_request_id: Mapped[int | None] = mapped_column(ForeignKey("safari_requests.id", ondelete="RESTRICT"), nullable=True, index=True)
    purpose: Mapped[PaymentPurpose] = mapped_column(SqlEnum(PaymentPurpose, name="payment_purpose", native_enum=False, length=32), nullable=False, default=PaymentPurpose.BOOKING, server_default=PaymentPurpose.BOOKING.value, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SqlEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.PENDING, server_default=PaymentStatus.PENDING.value, index=True)
    reconciliation_status: Mapped[PaymentReconciliationStatus] = mapped_column(SqlEnum(PaymentReconciliationStatus, name="payment_reconciliation_status", native_enum=False), nullable=False, default=PaymentReconciliationStatus.NOT_REQUIRED, server_default=PaymentReconciliationStatus.NOT_REQUIRED.value, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receipt_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_REQUESTED", server_default="NOT_REQUESTED")
    receipt_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciliation_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reconciliation_next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    reconciliation_last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciliation_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reconciliation_resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reconciliation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    booking: Mapped[Booking | None] = relationship(back_populates="payments")
    verification_hotel: Mapped[Hotel | None] = relationship("Hotel", foreign_keys=[verification_hotel_id])
    advertising_campaign = relationship("AdvertisingCampaign", back_populates="payments")
    safari_request = relationship("SafariRequest", back_populates="payments")
    reconciliation_admin: Mapped[User | None] = relationship("User", foreign_keys=[reconciliation_resolved_by])


class PaymentWebhookEvent(Base):
    """Deduplication ledger for verified gateway callbacks."""

    __tablename__ = "payment_webhook_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), index=True)
    refund_id: Mapped[int | None] = mapped_column(ForeignKey("refunds.id", ondelete="SET NULL"), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_payment_webhook_provider_event"),)


class Cancellation(Base):
    """Immutable cancellation decision based on the policy captured on its booking."""

    __tablename__ = "cancellations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    cancellation_type: Mapped[CancellationType] = mapped_column(SqlEnum(CancellationType, name="cancellation_type", native_enum=False), nullable=False)
    status: Mapped[CancellationStatus] = mapped_column(SqlEnum(CancellationStatus, name="cancellation_status", native_enum=False), nullable=False, default=CancellationStatus.REQUESTED, server_default=CancellationStatus.REQUESTED.value, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    refundable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), server_default="0.00")
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    booking: Mapped[Booking] = relationship(back_populates="cancellation")
    refunds: Mapped[list[Refund]] = relationship(back_populates="cancellation", cascade="all, delete-orphan", order_by="Refund.id")
    decided_by: Mapped[User | None] = relationship("User", foreign_keys=[decided_by_user_id])


class Refund(Base):
    """Separate, append-only financial execution record for a cancellation."""

    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_refunds_amount"),
        Index("ix_refunds_cancellation_status", "cancellation_id", "status"),
        Index("ix_refunds_verification_status", "verification_id", "status"),
        Index("ix_refunds_safari_status", "safari_request_id", "status"),
        UniqueConstraint("provider", "idempotency_key", name="uq_refunds_provider_idempotency"),
        CheckConstraint(
            "(cancellation_id IS NOT NULL AND verification_id IS NULL AND safari_request_id IS NULL) OR "
            "(cancellation_id IS NULL AND verification_id IS NOT NULL AND safari_request_id IS NULL) OR "
            "(cancellation_id IS NULL AND verification_id IS NULL AND safari_request_id IS NOT NULL)",
            name="ck_refunds_single_reason",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cancellation_id: Mapped[int | None] = mapped_column(ForeignKey("cancellations.id", ondelete="CASCADE"), nullable=True, index=True)
    verification_id: Mapped[int | None] = mapped_column(ForeignKey("hotel_verifications.id", ondelete="CASCADE"), nullable=True, index=True)
    safari_request_id: Mapped[int | None] = mapped_column(ForeignKey("safari_requests.id", ondelete="CASCADE"), nullable=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="VAYORA_GATEWAY", server_default="VAYORA_GATEWAY")
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, default=lambda: f"refund-{uuid.uuid4().hex}")
    status: Mapped[RefundStatus] = mapped_column(SqlEnum(RefundStatus, name="refund_status", native_enum=False), nullable=False, default=RefundStatus.PENDING, server_default=RefundStatus.PENDING.value, index=True)
    provider_refund_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    provider_status: Mapped[str | None] = mapped_column(String(40))
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    reconciliation_reason: Mapped[str | None] = mapped_column(Text)
    execution_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settlement_impact_status: Mapped[SettlementImpactStatus] = mapped_column(SqlEnum(SettlementImpactStatus, name="settlement_impact_status", native_enum=False), nullable=False, default=SettlementImpactStatus.PENDING, server_default=SettlementImpactStatus.PENDING.value)
    executed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    cancellation: Mapped[Cancellation | None] = relationship(back_populates="refunds")
    verification = relationship("HotelVerification", foreign_keys=[verification_id])
    safari_request = relationship("SafariRequest", foreign_keys=[safari_request_id])
    payment: Mapped[Payment] = relationship("Payment", foreign_keys=[payment_id])
    executed_by: Mapped[User | None] = relationship("User", foreign_keys=[executed_by_user_id])


class BookingTraveller(Base):
    __tablename__ = "booking_travellers"
    __table_args__ = (CheckConstraint("age >= 0 AND age <= 120", name="ck_booking_travellers_age"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(16))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="travellers")


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status: Mapped[BookingStatus | None] = mapped_column(SqlEnum(BookingStatus, name="booking_status"))
    new_status: Mapped[BookingStatus] = mapped_column(SqlEnum(BookingStatus, name="booking_status"), nullable=False)
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="status_history")
    changed_by: Mapped[User | None] = relationship("User", foreign_keys=[changed_by_user_id])
