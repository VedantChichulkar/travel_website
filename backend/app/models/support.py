from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.sensitive_data import EncryptedString, EncryptedText
from app.database import Base


class SupportEnquiryType(str, Enum):
    BOOKING_HELP = "BOOKING_HELP"
    SAFARI_HELP = "SAFARI_HELP"
    CANCELLATION_REFUND = "CANCELLATION_REFUND"
    HOTEL_PARTNER = "HOTEL_PARTNER"
    GENERAL = "GENERAL"


class SupportEnquiry(Base):
    __tablename__ = "support_enquiries"
    __table_args__ = (
        Index("ix_support_enquiries_queue", "status", "created_at"),
        Index("ix_support_enquiries_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    enquiry_type: Mapped[SupportEnquiryType] = mapped_column(
        SqlEnum(SupportEnquiryType, name="support_enquiry_type", native_enum=False, length=32), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(EncryptedString(length=512), nullable=False)
    email: Mapped[str] = mapped_column(EncryptedString(length=768), nullable=False)
    mobile: Mapped[str] = mapped_column(EncryptedString(length=256), nullable=False)
    message: Mapped[str] = mapped_column(EncryptedText(), nullable=False)
    customer_reference: Mapped[str | None] = mapped_column(EncryptedString(length=512))
    property_name: Mapped[str | None] = mapped_column(EncryptedString(length=512))
    location: Mapped[str | None] = mapped_column(EncryptedString(length=512))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"), index=True)
    safari_request_id: Mapped[int | None] = mapped_column(ForeignKey("safari_requests.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="RECEIVED", server_default="RECEIVED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
