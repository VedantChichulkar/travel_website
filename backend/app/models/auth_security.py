from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountTokenPurpose(str, Enum):
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user_active", "user_id", "revoked_at", "expires_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")


class AccountActionToken(Base):
    __tablename__ = "account_action_tokens"
    __table_args__ = (Index("ix_account_action_tokens_user_purpose", "user_id", "purpose", "used_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose: Mapped[AccountTokenPurpose] = mapped_column(SqlEnum(AccountTokenPurpose, name="account_token_purpose", native_enum=False), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User")


class AuthRateLimitBucket(Base):
    __tablename__ = "auth_rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint("scope", "key_hash", name="uq_auth_rate_limit_scope_key"),
        Index("ix_auth_rate_limit_window", "window_started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(40), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
