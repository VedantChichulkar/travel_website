from fastapi import Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.user import User, UserRole


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_hotel_partner(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.HOTEL_PARTNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hotel partner access required",
        )
    return current_user


def require_hotel_partner_only(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.HOTEL_PARTNER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hotel partner access required")
    return current_user


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required",
        )
    return current_user


def require_advertiser_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="External advertiser access requires a Customer account",
        )
    return current_user
