from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class District(Base):
    __tablename__ = "districts"
    __table_args__ = (
        UniqueConstraint("name", name="uq_districts_name"),
        UniqueConstraint("slug", name="uq_districts_slug"),
        Index("ix_districts_public", "is_active", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False)
    division: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    short_description: Mapped[str | None] = mapped_column(Text)
    hero_image_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    destinations: Mapped[list[Destination]] = relationship(back_populates="district", cascade="all, delete-orphan")
    hotels: Mapped[list[Hotel]] = relationship(back_populates="district_ref", foreign_keys="Hotel.district_id")
    places: Mapped[list[Place]] = relationship(back_populates="district")
    discovery_stories: Mapped[list[DiscoveryStory]] = relationship(
        secondary="discovery_story_districts", back_populates="districts"
    )


class Destination(Base):
    __tablename__ = "destinations"
    __table_args__ = (
        UniqueConstraint("district_id", "name", name="uq_destinations_district_name"),
        UniqueConstraint("district_id", "slug", name="uq_destinations_district_slug"),
        Index("ix_destinations_public", "district_id", "is_active", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    short_summary: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    image_alt: Mapped[str | None] = mapped_column(String(300))
    media_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_media_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_source: Mapped[str] = mapped_column(String(16), nullable=False, default="CURATED", server_default="CURATED")
    admin_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    district: Mapped[District] = relationship(back_populates="destinations")
    hotels: Mapped[list[Hotel]] = relationship(back_populates="destination_ref", foreign_keys="Hotel.destination_id")
    places: Mapped[list[Place]] = relationship(back_populates="destination")
    discovery_stories: Mapped[list[DiscoveryStory]] = relationship(
        secondary="discovery_story_destinations", back_populates="destinations"
    )
    media_asset: Mapped[PublicMediaAsset | None] = relationship(foreign_keys=[media_asset_id])
    faqs: Mapped[list[DestinationFAQ]] = relationship(
        back_populates="destination", cascade="all, delete-orphan", order_by="(DestinationFAQ.display_order, DestinationFAQ.id)"
    )
    media_items: Mapped[list[DestinationMedia]] = relationship(
        back_populates="destination", cascade="all, delete-orphan", order_by="(DestinationMedia.display_order, DestinationMedia.id)"
    )
