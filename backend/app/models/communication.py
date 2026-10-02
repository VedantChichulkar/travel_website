from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.core.sensitive_data import EncryptedString


class ConversationStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ConversationKind(str, Enum):
    PRE_BOOKING = "PRE_BOOKING"
    BOOKING = "BOOKING"
    OPERATIONAL = "OPERATIONAL"
    DISPUTE = "DISPUTE"


class NotificationEventType(str, Enum):
    BOOKING_REQUEST_CREATED = "BOOKING_REQUEST_CREATED"
    BOOKING_REQUEST_ACCEPTED = "BOOKING_REQUEST_ACCEPTED"
    BOOKING_REQUEST_REJECTED = "BOOKING_REQUEST_REJECTED"
    BOOKING_REQUEST_EXPIRED = "BOOKING_REQUEST_EXPIRED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    CANCELLATION = "CANCELLATION"
    REFUND_INITIATED = "REFUND_INITIATED"
    REFUND_PROCESSING = "REFUND_PROCESSING"
    REFUND_COMPLETED = "REFUND_COMPLETED"
    REFUND_FAILED = "REFUND_FAILED"
    REFUND_REQUIRES_REVIEW = "REFUND_REQUIRES_REVIEW"
    CHECK_IN_REMINDER = "CHECK_IN_REMINDER"
    CHECK_OUT_REMINDER = "CHECK_OUT_REMINDER"
    NO_SHOW = "NO_SHOW"
    HOTEL_OPERATIONAL_ISSUE = "HOTEL_OPERATIONAL_ISSUE"
    DISPUTE = "DISPUTE"
    SETTLEMENT_UPDATE = "SETTLEMENT_UPDATE"
    PAYOUT_INITIATED = "PAYOUT_INITIATED"
    PAYOUT_COMPLETED = "PAYOUT_COMPLETED"
    PAYOUT_FAILED = "PAYOUT_FAILED"
    PAYOUT_REQUIRES_REVIEW = "PAYOUT_REQUIRES_REVIEW"
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"
    PAYMENT_RECONCILIATION = "PAYMENT_RECONCILIATION"
    VERIFICATION_PAYMENT_SUCCESS = "VERIFICATION_PAYMENT_SUCCESS"
    VERIFICATION_CHANGES_REQUESTED = "VERIFICATION_CHANGES_REQUESTED"
    VERIFICATION_APPROVED = "VERIFICATION_APPROVED"
    VERIFICATION_REJECTED = "VERIFICATION_REJECTED"
    ADVERTISING_PAYMENT_SUCCESS = "ADVERTISING_PAYMENT_SUCCESS"
    ADVERTISING_CHANGES_REQUESTED = "ADVERTISING_CHANGES_REQUESTED"
    ADVERTISING_APPROVED = "ADVERTISING_APPROVED"
    ADVERTISING_REJECTED = "ADVERTISING_REJECTED"
    ADVERTISING_PAUSED = "ADVERTISING_PAUSED"
    SAFARI_REQUEST_RECEIVED = "SAFARI_REQUEST_RECEIVED"
    SAFARI_AVAILABILITY_UPDATE = "SAFARI_AVAILABILITY_UPDATE"
    SAFARI_DETAILS_REQUIRED = "SAFARI_DETAILS_REQUIRED"
    SAFARI_PAYMENT_REQUIRED = "SAFARI_PAYMENT_REQUIRED"
    SAFARI_PAYMENT_RECEIVED = "SAFARI_PAYMENT_RECEIVED"
    SAFARI_BOOKING_CONFIRMED = "SAFARI_BOOKING_CONFIRMED"
    SAFARI_BOOKING_FAILED = "SAFARI_BOOKING_FAILED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    REVIEW_RECEIVED = "REVIEW_RECEIVED"
    REVIEW_CHALLENGED = "REVIEW_CHALLENGED"
    SUPPORT_ENQUIRY_RECEIVED = "SUPPORT_ENQUIRY_RECEIVED"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class NotificationJobStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_customer_updated", "customer_id", "updated_at"),
        Index("ix_conversations_hotel_updated", "hotel_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[ConversationKind] = mapped_column(SqlEnum(ConversationKind, name="conversation_kind", native_enum=False), nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(SqlEnum(ConversationStatus, name="conversation_status", native_enum=False), nullable=False, default=ConversationStatus.OPEN, server_default=ConversationStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    read_states: Mapped[list[ConversationReadState]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ConversationReadState(Base):
    __tablename__ = "conversation_read_states"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_conversation_read_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="read_states")


class ConversationAdminAccess(Base):
    __tablename__ = "conversation_admin_access"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("recipient_user_id", "dedupe_key", name="uq_notifications_recipient_dedupe"),
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[NotificationEventType] = mapped_column(SqlEnum(NotificationEventType, name="notification_event_type", native_enum=False, length=32), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    jobs: Mapped[list[NotificationJob]] = relationship(back_populates="notification", cascade="all, delete-orphan", order_by="NotificationJob.id")


class NotificationJob(Base):
    __tablename__ = "notification_jobs"
    __table_args__ = (
        UniqueConstraint("notification_id", "channel", name="uq_notification_jobs_channel"),
        UniqueConstraint("idempotency_key", name="uq_notification_jobs_idempotency"),
        Index("ix_notification_jobs_status_retry", "status", "next_retry_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[NotificationChannel] = mapped_column(SqlEnum(NotificationChannel, name="notification_channel", native_enum=False), nullable=False)
    status: Mapped[NotificationJobStatus] = mapped_column(SqlEnum(NotificationJobStatus, name="notification_job_status", native_enum=False), nullable=False, default=NotificationJobStatus.PROVIDER_UNAVAILABLE, server_default=NotificationJobStatus.PROVIDER_UNAVAILABLE.value)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    delivery_body: Mapped[str | None] = mapped_column(EncryptedString(length=4096), nullable=True)
    delivery_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    notification: Mapped[Notification] = relationship(back_populates="jobs")
