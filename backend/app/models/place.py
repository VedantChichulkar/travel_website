from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpiritualTradition(str, Enum):
    HINDU = "HINDU"
    BUDDHIST = "BUDDHIST"
    JAIN = "JAIN"
    SIKH = "SIKH"
    ISLAMIC = "ISLAMIC"
    CHRISTIAN = "CHRISTIAN"
    OTHER = "OTHER"
    MULTI_TRADITION = "MULTI_TRADITION"


place_interests = Table(
    "place_interests",
    Base.metadata,
    Column("place_id", ForeignKey("places.id", ondelete="CASCADE"), primary_key=True),
    Column("interest_id", ForeignKey("interests.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_place_interests_interest_id", "interest_id"),
)


class Interest(Base):
    __tablename__ = "interests"
    __table_args__ = (
        UniqueConstraint("name", name="uq_interests_name"),
        UniqueConstraint("slug", name="uq_interests_slug"),
        CheckConstraint("display_order >= 0", name="ck_interests_display_order"),
        Index("ix_interests_public", "is_active", "display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    places: Mapped[list[Place]] = relationship(secondary=place_interests, back_populates="interests")
    discovery_stories: Mapped[list[DiscoveryStory]] = relationship(
        secondary="discovery_story_interests", back_populates="interests"
    )


class Place(Base):
    __tablename__ = "places"
    __table_args__ = (
        UniqueConstraint("district_id", "name", name="uq_places_district_name"),
        UniqueConstraint("district_id", "slug", name="uq_places_district_slug"),
        CheckConstraint("display_order >= 0", name="ck_places_display_order"),
        CheckConstraint(
            "spiritual_tradition IS NULL OR spiritual_tradition IN "
            "('HINDU','BUDDHIST','JAIN','SIKH','ISLAMIC','CHRISTIAN','OTHER','MULTI_TRADITION')",
            name="ck_places_spiritual_tradition",
        ),
        Index("ix_places_public", "district_id", "is_active", "is_featured", "display_order"),
        Index("ix_places_destination_public", "destination_id", "is_active", "display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    destination_id: Mapped[int | None] = mapped_column(
        ForeignKey("destinations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(500))
    opening_hours: Mapped[str | None] = mapped_column(Text)
    entry_fee_info: Mapped[str | None] = mapped_column(Text)
    recommended_visit_duration: Mapped[str | None] = mapped_column(String(120))
    best_time_to_visit: Mapped[str | None] = mapped_column(String(300))
    getting_there: Mapped[str | None] = mapped_column(Text)
    nearest_railway_station: Mapped[str | None] = mapped_column(String(300))
    nearest_airport: Mapped[str | None] = mapped_column(String(300))
    visitor_info_source: Mapped[str | None] = mapped_column(String(500))
    visitor_info_source_url: Mapped[str | None] = mapped_column(String(2048))
    visitor_info_verified_at: Mapped[date | None] = mapped_column(Date)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    image_alt: Mapped[str | None] = mapped_column(String(300))
    media_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_media_assets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    spiritual_tradition: Mapped[SpiritualTradition | None] = mapped_column(
        SqlEnum(SpiritualTradition, name="spiritual_tradition", native_enum=False, length=32),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_source: Mapped[str] = mapped_column(String(16), nullable=False, default="CURATED", server_default="CURATED")
    admin_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    district: Mapped[District] = relationship(back_populates="places")
    destination: Mapped[Destination | None] = relationship(back_populates="places")
    interests: Mapped[list[Interest]] = relationship(secondary=place_interests, back_populates="places")
    discovery_stories: Mapped[list[DiscoveryStory]] = relationship(
        secondary="discovery_story_places", back_populates="related_places"
    )
    media_asset: Mapped[PublicMediaAsset | None] = relationship(foreign_keys=[media_asset_id])
    faqs: Mapped[list[PlaceFAQ]] = relationship(
        back_populates="place", cascade="all, delete-orphan", order_by="(PlaceFAQ.display_order, PlaceFAQ.id)"
    )
    media_items: Mapped[list[PlaceMedia]] = relationship(
        back_populates="place", cascade="all, delete-orphan", order_by="(PlaceMedia.display_order, PlaceMedia.id)"
    )
