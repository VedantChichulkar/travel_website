from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PrivateDocumentDeletionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class PrivateDocumentDeletionJob(Base):
    __tablename__ = "private_document_deletion_jobs"
    __table_args__ = (Index("ix_private_document_deletion_due", "status", "next_retry_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[PrivateDocumentDeletionStatus] = mapped_column(
        SqlEnum(PrivateDocumentDeletionStatus, name="private_document_deletion_status", native_enum=False),
        nullable=False, default=PrivateDocumentDeletionStatus.PENDING, server_default=PrivateDocumentDeletionStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
