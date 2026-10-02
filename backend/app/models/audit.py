from datetime import datetime

from sqlalchemy import DateTime, Index, JSON, String, Text, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    """Append-only governance record containing only deliberately selected values."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_target", "target_type", "target_id", "created_at"),
        Index("ix_audit_logs_actor_created", "actor_user_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Deliberately not a foreign key: an audit actor identifier must survive
    # account retention/deletion workflows without blocking them or being erased.
    actor_user_id: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_value: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


@event.listens_for(AuditLog, "before_update")
def reject_audit_update(*_args) -> None:
    raise ValueError("Audit history is immutable")


@event.listens_for(AuditLog, "before_delete")
def reject_audit_delete(*_args) -> None:
    raise ValueError("Audit history is immutable")
