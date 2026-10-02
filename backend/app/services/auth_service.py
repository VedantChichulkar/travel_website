from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_phone,
    update_last_login,
)
from app.schemas.user import UserCreate
from app.core.config import settings
from app.services import auth_security_service


def register_user(db: Session, data: UserCreate) -> User:
    normalized_email = str(data.email).strip().lower()
    if get_user_by_email(db, normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )
    if get_user_by_phone(db, data.phone):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone is already registered",
        )

    try:
        user = create_user(
            db,
            full_name=data.full_name,
            email=normalized_email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=data.role,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_email_verified=False,
            is_phone_verified=False,
        )
        auth_security_service.request_email_verification(db, user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or phone is already registered",
        ) from exc


def _portal_access_error(user: User, portal: UserRole) -> HTTPException:
    actual_role = UserRole.CUSTOMER if user.role == UserRole.USER else user.role
    portal_names = {
        UserRole.CUSTOMER: "Customer",
        UserRole.HOTEL_PARTNER: "Hotel Partner",
        UserRole.ADMIN: "Admin",
    }
    portal_paths = {
        UserRole.CUSTOMER: "/login",
        UserRole.HOTEL_PARTNER: "/partner/login",
        UserRole.ADMIN: "/admin/login",
    }
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "WRONG_PORTAL",
            "account_role": actual_role.value,
            "portal_path": portal_paths[actual_role],
            "message": (
                f"This account belongs to the {portal_names[actual_role]} portal. "
                f"Please use the {portal_names[actual_role]} login."
            ),
        },
    )


def authenticate_user(
    db: Session,
    email: str,
    password: str,
    portal: UserRole | None = None,
) -> User:
    normalized_email = email.strip().lower()
    user = get_user_by_email(db, normalized_email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive or suspended",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification is required before sign in",
        )

    if portal is not None:
        requested_portal = UserRole.CUSTOMER if portal == UserRole.USER else portal
        actual_portal = UserRole.CUSTOMER if user.role == UserRole.USER else user.role
        if requested_portal != actual_portal:
            raise _portal_access_error(user, requested_portal)

    update_last_login(db, user)
    return user
