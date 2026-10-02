from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.sensitive_data import EncryptedString
from app.database import Base


class SafariRequestStatus(str, Enum):
    AVAILABILITY_REQUESTED = "AVAILABILITY_REQUESTED"
    CHECKING_AVAILABILITY = "CHECKING_AVAILABILITY"
    AWAITING_TRAVELLER_DETAILS = "AWAITING_TRAVELLER_DETAILS"
    DETAILS_SUBMITTED = "DETAILS_SUBMITTED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    BOOKING_IN_PROGRESS = "BOOKING_IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    BOOKING_FAILED = "BOOKING_FAILED"


class SafariDocumentKind(str, Enum):
    TRAVELLER = "TRAVELLER"
    CONFIRMATION = "CONFIRMATION"


class Safari(Base):
    __tablename__ = "safaris"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="RESTRICT"), index=True)
    destination_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id", ondelete="RESTRICT"), index=True)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    shifts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    zones: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    gates: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    booking_categories: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    vehicle_options: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    traveller_requirements: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    official_reference_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    official_contact_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    official_document_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    district = relationship("District")
    destination = relationship("Destination")
    notices = relationship("SafariOperationalNotice", back_populates="safari", cascade="all, delete-orphan")


class SafariRequest(Base):
    __tablename__ = "safari_requests"
    __table_args__ = (
        CheckConstraint("visitor_count > 0", name="ck_safari_request_visitors"),
        CheckConstraint("payable_amount IS NULL OR payable_amount >= 0", name="ck_safari_request_amount"),
        Index("ix_safari_request_queue", "status", "target_response_at", "created_at"),
        Index("ix_safari_request_customer_created", "customer_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    safari_id: Mapped[int] = mapped_column(ForeignKey("safaris.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_shift: Mapped[str | None] = mapped_column(String(100))
    preferred_booking_category: Mapped[str | None] = mapped_column(String(100))
    preferred_vehicle_option: Mapped[str | None] = mapped_column(String(100))
    visitor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    alternate_preference: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[SafariRequestStatus] = mapped_column(SqlEnum(SafariRequestStatus, name="safari_request_status", native_enum=False, length=40), nullable=False, default=SafariRequestStatus.AVAILABILITY_REQUESTED, server_default=SafariRequestStatus.AVAILABILITY_REQUESTED.value, index=True)
    availability_result: Mapped[str | None] = mapped_column(String(30))
    selected_alternative_id: Mapped[int | None] = mapped_column(ForeignKey("safari_alternatives.id", ondelete="SET NULL", use_alter=True, name="fk_safari_requests_selected_alternative"), index=True)
    target_response_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payable_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    price_breakdown: Mapped[dict[str, object] | None] = mapped_column(JSON)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    external_booking_reference: Mapped[str | None] = mapped_column(String(160))
    confirmed_date: Mapped[date | None] = mapped_column(Date)
    confirmed_shift: Mapped[str | None] = mapped_column(String(100))
    confirmed_zone: Mapped[str | None] = mapped_column(String(160))
    confirmed_gate: Mapped[str | None] = mapped_column(String(160))
    confirmed_booking_category: Mapped[str | None] = mapped_column(String(100))
    confirmed_vehicle_option: Mapped[str | None] = mapped_column(String(100))
    official_booking_contact: Mapped[str | None] = mapped_column(EncryptedString(length=512))
    operator_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reporting_instructions: Mapped[str | None] = mapped_column(Text)
    final_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    safari = relationship("Safari")
    customer = relationship("User", foreign_keys=[customer_id])
    alternatives = relationship("SafariAlternative", back_populates="request", foreign_keys="SafariAlternative.request_id", cascade="all, delete-orphan")
    selected_alternative = relationship("SafariAlternative", foreign_keys=[selected_alternative_id], post_update=True)
    travellers = relationship("SafariTraveller", back_populates="request", cascade="all, delete-orphan")
    documents = relationship("SafariDocument", back_populates="request", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="safari_request")


class SafariAlternative(Base):
    __tablename__ = "safari_alternatives"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("safari_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    safari_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift: Mapped[str | None] = mapped_column(String(100))
    zone: Mapped[str | None] = mapped_column(String(160))
    gate: Mapped[str | None] = mapped_column(String(160))
    booking_category: Mapped[str | None] = mapped_column(String(100))
    vehicle_option: Mapped[str | None] = mapped_column(String(100))
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request = relationship("SafariRequest", back_populates="alternatives", foreign_keys=[request_id])


class SafariOperationalNotice(Base):
    __tablename__ = "safari_operational_notices"
    __table_args__ = (Index("ix_safari_notice_public_window", "is_active", "effective_from", "effective_until"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    safari_id: Mapped[int | None] = mapped_column(ForeignKey("safaris.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO", server_default="INFO")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    safari = relationship("Safari", back_populates="notices")


class SafariTraveller(Base):
    __tablename__ = "safari_travellers"
    __table_args__ = (UniqueConstraint("request_id", "position", name="uq_safari_traveller_position"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("safari_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    details_encrypted: Mapped[str] = mapped_column(EncryptedString(length=12000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request = relationship("SafariRequest", back_populates="travellers")
    documents = relationship("SafariDocument", back_populates="traveller")


class SafariDocument(Base):
    __tablename__ = "safari_documents"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("safari_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    traveller_id: Mapped[int | None] = mapped_column(ForeignKey("safari_travellers.id", ondelete="CASCADE"), index=True)
    kind: Mapped[SafariDocumentKind] = mapped_column(SqlEnum(SafariDocumentKind, name="safari_document_kind", native_enum=False), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request = relationship("SafariRequest", back_populates="documents")
    traveller = relationship("SafariTraveller", back_populates="documents")
