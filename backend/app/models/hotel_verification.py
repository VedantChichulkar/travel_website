from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.core.sensitive_data import EncryptedString


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ADDITIONAL_INFO_REQUIRED = "ADDITIONAL_INFO_REQUIRED"
    NEEDS_CHANGES = "NEEDS_CHANGES"


class BusinessType(str, Enum):
    PROPRIETORSHIP = "PROPRIETORSHIP"
    PARTNERSHIP = "PARTNERSHIP"
    PRIVATE_LIMITED = "PRIVATE_LIMITED"
    PUBLIC_LIMITED = "PUBLIC_LIMITED"
    LLP = "LLP"
    OTHER = "OTHER"


class HotelVerification(Base):
    __tablename__ = "hotel_verifications"
    __table_args__ = (
        Index("ix_hotel_verifications_status", "verification_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(
        ForeignKey("hotels.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        SqlEnum(BusinessType, name="business_type", native_enum=False),
        nullable=False,
        default=BusinessType.PROPRIETORSHIP,
        server_default=BusinessType.PROPRIETORSHIP.value,
    )
    gstin: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    pan: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_beneficiary_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    document_proof_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Legacy public URLs are retained only for migration/audit and are never
    # serialized. New documents use the private storage fields below.
    document_proof_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    document_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_size: Mapped[int | None] = mapped_column(nullable=True)
    document_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    document_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        SqlEnum(VerificationStatus, name="verification_status", native_enum=False),
        nullable=False,
        default=VerificationStatus.PENDING,
        server_default=VerificationStatus.PENDING.value,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    hotel = relationship("Hotel", back_populates="verification")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    @property
    def document_available(self) -> bool:
        return bool(self.document_storage_key)
