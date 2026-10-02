from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DestinationFAQ(Base):
    __tablename__ = "destination_faqs"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="ck_destination_faqs_display_order"),
        Index("ix_destination_faqs_public", "destination_id", "is_active", "display_order"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    destination: Mapped[Destination] = relationship(back_populates="faqs")


class PlaceFAQ(Base):
    __tablename__ = "place_faqs"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="ck_place_faqs_display_order"),
        Index("ix_place_faqs_public", "place_id", "is_active", "display_order"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    place: Mapped[Place] = relationship(back_populates="faqs")


class DestinationMedia(Base):
    __tablename__ = "destination_media"
    __table_args__ = (
        UniqueConstraint("media_asset_id", name="uq_destination_media_asset"),
        CheckConstraint("role IN ('HERO','GALLERY')", name="ck_destination_media_role"),
        CheckConstraint("display_order >= 0", name="ck_destination_media_display_order"),
        Index("ix_destination_media_order", "destination_id", "role", "display_order"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("public_media_assets.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="GALLERY", server_default="GALLERY")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    destination: Mapped[Destination] = relationship(back_populates="media_items")
    asset: Mapped[PublicMediaAsset] = relationship()


class PlaceMedia(Base):
    __tablename__ = "place_media"
    __table_args__ = (
        UniqueConstraint("media_asset_id", name="uq_place_media_asset"),
        CheckConstraint("role IN ('HERO','GALLERY')", name="ck_place_media_role"),
        CheckConstraint("display_order >= 0", name="ck_place_media_display_order"),
        Index("ix_place_media_order", "place_id", "role", "display_order"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False)
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("public_media_assets.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="GALLERY", server_default="GALLERY")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    place: Mapped[Place] = relationship(back_populates="media_items")
    asset: Mapped[PublicMediaAsset] = relationship()
