from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.scalar(select(User).where(User.phone == phone.strip()))


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    phone: str,
    password_hash: str,
    role: UserRole = UserRole.CUSTOMER,
    status: UserStatus = UserStatus.ACTIVE,
    is_active: bool = True,
    is_email_verified: bool = False,
    is_phone_verified: bool = False,
) -> User:
    user = User(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        password_hash=password_hash,
        role=role,
        status=status,
        is_active=is_active,
        is_email_verified=is_email_verified,
        is_phone_verified=is_phone_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_last_login(db: Session, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
