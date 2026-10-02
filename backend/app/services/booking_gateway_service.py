"""Policy layer for the hotel booking gateway; it does not create bookings."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, RoomInventory, RoomType
from app.models.hotel_verification import VerificationStatus
from app.models.user import User
from app.repositories import hotel_verification_repository
from app.schemas.hotel import BookingGatewayStateResponse
from app.services import audit_service


def _last_inventory_update(db: Session, hotel_id: int) -> datetime | None:
    return db.scalar(
        select(func.max(RoomInventory.updated_at))
        .join(RoomType, RoomInventory.room_type_id == RoomType.id)
        .where(RoomType.hotel_id == hotel_id)
    )


def _verified(db: Session, hotel: Hotel) -> bool:
    verification = hotel_verification_repository.get_verification_by_hotel_id(db, hotel.id)
    return hotel.status == HotelStatus.ACTIVE and verification is not None and verification.verification_status == VerificationStatus.APPROVED


def state(db: Session, hotel: Hotel) -> BookingGatewayStateResponse:
    last_updated = _last_inventory_update(db, hotel.id)
    now = datetime.now(timezone.utc)
    if last_updated is not None and last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    fresh = last_updated is not None and last_updated >= now - timedelta(hours=settings.INVENTORY_FRESHNESS_HOURS)
    requested = hotel.partner_booking_gateway_status
    effective = hotel.gateway_override_status or requested
    reason = None
    # Even a Maharashtra Tourist Places override cannot make an unverified or stale property
    # instantly bookable. Overrides can always make availability stricter.
    if effective == BookingGatewayStatus.ACTIVE and not _verified(db, hotel):
        effective = BookingGatewayStatus.PAUSED
        reason = "Only verified active hotels can enable instant booking."
    elif effective == BookingGatewayStatus.ACTIVE and not fresh:
        effective = BookingGatewayStatus.BOOKING_ON_REQUEST
        reason = "Inventory is missing or stale; instant booking is temporarily disabled."
    return BookingGatewayStateResponse(
        hotel_id=hotel.id, partner_requested_status=requested, effective_status=effective,
        override_status=hotel.gateway_override_status, override_reason=hotel.gateway_override_reason,
        overridden_at=hotel.gateway_overridden_at, inventory_last_updated_at=last_updated,
        inventory_is_fresh=fresh, inventory_freshness_reason=reason, verified=_verified(db, hotel),
    )


def effective_status(db: Session, hotel: Hotel) -> BookingGatewayStatus:
    """Authoritative booking mode for every customer-facing decision."""
    return state(db, hotel).effective_status


def update_partner(db: Session, hotel: Hotel, requested: BookingGatewayStatus) -> BookingGatewayStateResponse:
    if hotel.gateway_override_status is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Maharashtra Tourist Places has overridden this hotel's booking gateway")
    if requested == BookingGatewayStatus.ACTIVE and not _verified(db, hotel):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Only verified active hotels can enable instant booking")
    hotel.partner_booking_gateway_status = requested
    # Keep the pre-policy column as a compatibility projection only. Callers
    # must use effective_status()/state() for booking decisions.
    hotel.booking_gateway_status = requested
    db.commit()
    db.refresh(hotel)
    return state(db, hotel)


def set_override(db: Session, hotel: Hotel, admin: User, forced: BookingGatewayStatus, reason: str) -> BookingGatewayStateResponse:
    previous = {"override_status": hotel.gateway_override_status.value if hotel.gateway_override_status else None, "effective_status": effective_status(db, hotel).value}
    hotel.gateway_override_status = forced
    hotel.gateway_override_reason = reason.strip()
    hotel.gateway_overridden_by = admin.id
    hotel.gateway_overridden_at = datetime.now(timezone.utc)
    hotel.booking_gateway_status = forced
    new_effective = effective_status(db, hotel)
    audit_service.record(db, actor=admin, action="BOOKING_GATEWAY_OVERRIDDEN", target_type="HOTEL", target_id=hotel.id, reason=reason, previous_value=previous, new_value={"override_status": forced.value, "effective_status": new_effective.value})
    db.commit()
    db.refresh(hotel)
    return state(db, hotel)


def clear_override(db: Session, hotel: Hotel, admin: User | None = None, reason: str | None = None) -> BookingGatewayStateResponse:
    previous = {"override_status": hotel.gateway_override_status.value if hotel.gateway_override_status else None, "effective_status": effective_status(db, hotel).value}
    hotel.gateway_override_status = None
    hotel.gateway_override_reason = None
    hotel.gateway_overridden_by = None
    hotel.gateway_overridden_at = None
    hotel.booking_gateway_status = hotel.partner_booking_gateway_status
    new_effective = effective_status(db, hotel)
    if admin is not None:
        audit_service.record(db, actor=admin, action="BOOKING_GATEWAY_OVERRIDE_CLEARED", target_type="HOTEL", target_id=hotel.id, reason=reason or "Override cleared", previous_value=previous, new_value={"override_status": None, "effective_status": new_effective.value})
    db.commit()
    db.refresh(hotel)
    return state(db, hotel)
