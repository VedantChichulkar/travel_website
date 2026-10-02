from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AdvertisingPlacement(str, Enum):
    HOMEPAGE_BANNER = "HOMEPAGE_BANNER"
    DESTINATION_PROMOTION = "DESTINATION_PROMOTION"


class AdvertiserType(str, Enum):
    HOTEL = "HOTEL"
    EXTERNAL = "EXTERNAL"


class AdvertiserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class AdvertisingCampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PENDING_REVIEW = "PENDING_REVIEW"
    NEEDS_CHANGES = "NEEDS_CHANGES"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class AdvertisingEventType(str, Enum):
    IMPRESSION = "IMPRESSION"
    CLICK = "CLICK"


class AdvertiserProfile(Base):
    __tablename__ = "advertiser_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_advertiser_profiles_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_person: Mapped[str] = mapped_column(String(100), nullable=False)
    business_email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[AdvertiserStatus] = mapped_column(SqlEnum(AdvertiserStatus, name="advertiser_status", native_enum=False), nullable=False, default=AdvertiserStatus.ACTIVE, server_default=AdvertiserStatus.ACTIVE.value, index=True)
    suspended_reason: Mapped[str | None] = mapped_column(Text)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id])
    suspending_admin = relationship("User", foreign_keys=[suspended_by])
    campaigns = relationship("AdvertisingCampaign", back_populates="advertiser_profile")


class AdvertisingCampaign(Base):
    __tablename__ = "advertising_campaigns"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_ad_campaign_dates"),
        CheckConstraint("price_amount >= 0", name="ck_ad_campaign_price"),
        Index("ix_ad_campaign_public", "placement", "status", "start_at", "end_at"),
        CheckConstraint("(advertiser_type = 'HOTEL' AND hotel_id IS NOT NULL AND advertiser_profile_id IS NULL) OR (advertiser_type = 'EXTERNAL' AND hotel_id IS NULL AND advertiser_profile_id IS NOT NULL)", name="ck_ad_campaign_owner"),
        Index("ix_ad_campaign_hotel_created", "hotel_id", "created_at"),
        Index("ix_ad_campaign_external_created", "advertiser_profile_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    advertiser_type: Mapped[AdvertiserType] = mapped_column(SqlEnum(AdvertiserType, name="advertiser_type", native_enum=False), nullable=False, default=AdvertiserType.HOTEL, server_default=AdvertiserType.HOTEL.value, index=True)
    hotel_id: Mapped[int | None] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), index=True)
    advertiser_profile_id: Mapped[int | None] = mapped_column(ForeignKey("advertiser_profiles.id", ondelete="RESTRICT"), index=True)
    campaign_name: Mapped[str | None] = mapped_column(String(160))
    headline: Mapped[str | None] = mapped_column(String(120))
    short_copy: Mapped[str | None] = mapped_column(String(280))
    target_url: Mapped[str | None] = mapped_column(String(2048))
    approved_target_url: Mapped[str | None] = mapped_column(String(2048))
    placement: Mapped[AdvertisingPlacement] = mapped_column(SqlEnum(AdvertisingPlacement, name="advertising_placement", native_enum=False), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(80), nullable=False)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="RESTRICT"), index=True)
    destination_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id", ondelete="RESTRICT"), index=True)
    creative_url: Mapped[str | None] = mapped_column(String(2048))
    creative_storage_key: Mapped[str | None] = mapped_column(String(512))
    creative_content_type: Mapped[str | None] = mapped_column(String(100))
    creative_size: Mapped[int | None] = mapped_column(Integer)
    creative_width: Mapped[int | None] = mapped_column(Integer)
    creative_height: Mapped[int | None] = mapped_column(Integer)
    creative_rights_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    creative_source: Mapped[str | None] = mapped_column(String(255))
    alt_text: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[AdvertisingCampaignStatus] = mapped_column(SqlEnum(AdvertisingCampaignStatus, name="advertising_campaign_status", native_enum=False), nullable=False, default=AdvertisingCampaignStatus.DRAFT, server_default=AdvertisingCampaignStatus.DRAFT.value, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    review_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refund_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hotel = relationship("Hotel")
    advertiser_profile = relationship("AdvertiserProfile", back_populates="campaigns")
    district = relationship("District")
    destination = relationship("Destination")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    payments = relationship("Payment", back_populates="advertising_campaign")
    events = relationship("AdvertisingEvent", back_populates="campaign", cascade="all, delete-orphan")


class AdvertisingEvent(Base):
    __tablename__ = "advertising_events"
    __table_args__ = (
        UniqueConstraint("campaign_id", "event_type", "dedupe_hash", "bucket_start", name="uq_ad_event_dedupe_bucket"),
        Index("ix_ad_events_campaign_type", "campaign_id", "event_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("advertising_campaigns.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[AdvertisingEventType] = mapped_column(SqlEnum(AdvertisingEventType, name="advertising_event_type", native_enum=False), nullable=False)
    dedupe_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    campaign = relationship("AdvertisingCampaign", back_populates="events")
