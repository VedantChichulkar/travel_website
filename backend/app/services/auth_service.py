from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_phone,
)
from app.schemas.user import UserCreate


def register_user(db: Session, data: UserCreate) -> User:
    if get_user_by_email(db, str(data.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    if get_user_by_phone(db, data.phone):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone is already registered")

    try:
        return create_user(
            db,
            full_name=data.full_name,
            email=str(data.email),
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=UserRole.USER,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or phone is already registered",
        ) from exc


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
