from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


discovery_story_interests = Table(
    "discovery_story_interests",
    Base.metadata,
    Column("story_id", ForeignKey("discovery_stories.id", ondelete="CASCADE"), primary_key=True),
    Column("interest_id", ForeignKey("interests.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_discovery_story_interests_interest_id", "interest_id"),
)

discovery_story_districts = Table(
    "discovery_story_districts",
    Base.metadata,
    Column("story_id", ForeignKey("discovery_stories.id", ondelete="CASCADE"), primary_key=True),
    Column("district_id", ForeignKey("districts.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_discovery_story_districts_district_id", "district_id"),
)

discovery_story_destinations = Table(
    "discovery_story_destinations",
    Base.metadata,
    Column("story_id", ForeignKey("discovery_stories.id", ondelete="CASCADE"), primary_key=True),
    Column("destination_id", ForeignKey("destinations.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_discovery_story_destinations_destination_id", "destination_id"),
)

discovery_story_places = Table(
    "discovery_story_places",
    Base.metadata,
    Column("story_id", ForeignKey("discovery_stories.id", ondelete="CASCADE"), primary_key=True),
    Column("place_id", ForeignKey("places.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_discovery_story_places_place_id", "place_id"),
)


class DiscoveryStory(Base):
    __tablename__ = "discovery_stories"
    __table_args__ = (
        UniqueConstraint("title", name="uq_discovery_stories_title"),
        UniqueConstraint("slug", name="uq_discovery_stories_slug"),
        CheckConstraint("display_order >= 0", name="ck_discovery_stories_display_order"),
        Index("ix_discovery_stories_public", "is_active", "is_featured", "display_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    interests: Mapped[list[Interest]] = relationship(
        secondary=discovery_story_interests, back_populates="discovery_stories"
    )
    districts: Mapped[list[District]] = relationship(
        secondary=discovery_story_districts, back_populates="discovery_stories"
    )
    destinations: Mapped[list[Destination]] = relationship(
        secondary=discovery_story_destinations, back_populates="discovery_stories"
    )
    related_places: Mapped[list[Place]] = relationship(
        secondary=discovery_story_places, back_populates="discovery_stories"
    )
