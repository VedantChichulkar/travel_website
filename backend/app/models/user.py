from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    HOTEL_PARTNER = "HOTEL_PARTNER"
    ADMIN = "ADMIN"
    USER = "USER"  # Backward-compatibility alias for CUSTOMER


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", native_enum=False),
        default=UserRole.CUSTOMER,
        server_default=UserRole.CUSTOMER.value,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SqlEnum(UserStatus, name="user_status", native_enum=False),
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="1",
        nullable=False,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    is_phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
