from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PublicMediaAsset(Base):
    """Rights-aware public discovery media; deliberately separate from private documents."""

    __tablename__ = "public_media_assets"
    __table_args__ = (
        Index("ix_public_media_assets_status_created", "status", "created_at"),
        Index("ix_public_media_assets_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    public_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    alt_text: Mapped[str] = mapped_column(String(300), nullable=False)
    specificity: Mapped[str] = mapped_column(String(16), nullable=False)
    creator_owner: Mapped[str] = mapped_column(String(200), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    usage_basis: Mapped[str] = mapped_column(String(200), nullable=False)
    attribution_text: Mapped[str | None] = mapped_column(String(500))
    rights_verified_at: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    replaced_by_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("public_media_assets.id", ondelete="SET NULL"), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
