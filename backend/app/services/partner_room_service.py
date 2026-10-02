from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.hotel import Amenity, RoomImage, RoomType, RoomTypeStatus, RoomTypeVersion
from app.models.user import User
from app.repositories import hotel_repository
from app.schemas.hotel import (
    AmenityResponse,
    PartnerRoomTypeCreate,
    PartnerRoomTypeResponse,
    PartnerRoomTypeUpdate,
    RoomImageCreate,
    RoomImageResponse,
    RoomTypeReviewRequest,
)
from app.services import audit_service, media_storage


def _hotel_for_partner(db: Session, user: User):
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return hotel


def _response(room: RoomType) -> PartnerRoomTypeResponse:
    return PartnerRoomTypeResponse.model_validate(room)


def _amenities(db: Session, ids: list[int]) -> list[Amenity]:
    amenities = [hotel_repository.get_amenity_by_id(db, item) for item in ids]
    if any(item is None or not item.is_active for item in amenities):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="One or more room amenities are unavailable")
    return [item for item in amenities if item is not None]


def _room_for_partner(db: Session, user: User, room_id: int) -> RoomType:
    hotel = _hotel_for_partner(db, user)
    room = hotel_repository.get_room_type(db, hotel.id, room_id, detailed=True)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    return room


def get_owned_room(db: Session, user: User, room_id: int) -> RoomType:
    """Return a room only when it belongs to the authenticated hotel tenant."""
    return _room_for_partner(db, user, room_id)


def list_partner_rooms(db: Session, user: User) -> list[PartnerRoomTypeResponse]:
    hotel = _hotel_for_partner(db, user)
    return [_response(room) for room in hotel_repository.list_room_types(db, hotel.id)]


def list_admin_review_queue(db: Session, room_status: RoomTypeStatus | None = None) -> list[PartnerRoomTypeResponse]:
    query = select(RoomType).order_by(RoomType.updated_at.desc())
    if room_status is not None:
        query = query.where(RoomType.status == room_status)
    else:
        query = query.where(RoomType.status.in_((RoomTypeStatus.PENDING, RoomTypeStatus.APPROVED, RoomTypeStatus.NEEDS_CHANGES)))
    return [_response(room) for room in db.scalars(query)]


def get_partner_room(db: Session, user: User, room_id: int) -> PartnerRoomTypeResponse:
    return _response(_room_for_partner(db, user, room_id))


def create_partner_room(db: Session, user: User, data: PartnerRoomTypeCreate) -> PartnerRoomTypeResponse:
    hotel = _hotel_for_partner(db, user)
    if hotel_repository.get_room_type_by_name(db, hotel.id, data.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A room type with this name already exists")
    values = data.model_dump(exclude={"amenity_ids", "meal_add_on_options"})
    values["meal_add_on_options"] = [item.model_dump(mode="json") for item in data.meal_add_on_options]
    room = RoomType(hotel_id=hotel.id, status=RoomTypeStatus.DRAFT, **values)
    room.amenities = _amenities(db, data.amenity_ids)
    db.add(room)
    db.commit()
    return get_partner_room(db, user, room.id)


def _snapshot(room: RoomType, reason: str) -> RoomTypeVersion:
    payload = {
        "name": room.name,
        "description": room.description,
        "max_adults": room.max_adults,
        "max_children": room.max_children,
        "max_guests": room.max_guests,
        "bed_type": room.bed_type,
        "bed_count": room.bed_count,
        "base_price": str(room.base_price),
        "currency": room.currency,
        "total_rooms": room.total_rooms,
        "extra_bed_rules": room.extra_bed_rules,
        "meal_add_on_options": room.meal_add_on_options,
        "amenity_ids": [item.id for item in room.amenities],
        "images": [{"image_url": img.image_url, "alt_text": img.alt_text, "is_cover": img.is_cover} for img in room.images],
    }
    return RoomTypeVersion(room_type_id=room.id, version=room.version, snapshot=payload, reason=reason)


def _has_confirmed_bookings(db: Session, room_id: int) -> bool:
    return (
        db.scalar(
            select(Booking.id)
            .where(Booking.room_type_id == room_id, Booking.status == BookingStatus.CONFIRMED)
            .limit(1)
        )
        is not None
    )


def update_partner_room(db: Session, user: User, room_id: int, data: PartnerRoomTypeUpdate) -> PartnerRoomTypeResponse:
    room = _room_for_partner(db, user, room_id)
    if _has_confirmed_bookings(db, room.id):
        db.add(_snapshot(room, "partner_edit_after_confirmed_booking"))
        room.version += 1
    values = data.model_dump(exclude={"amenity_ids", "meal_add_on_options"})
    for field, value in values.items():
        setattr(room, field, value)
    room.meal_add_on_options = [item.model_dump(mode="json") for item in data.meal_add_on_options]
    room.amenities = _amenities(db, data.amenity_ids)
    # Any partner edit returns the room to draft/validation; partner cannot self-approve or make bookable.
    room.status = RoomTypeStatus.DRAFT
    room.review_notes = None
    room.reviewed_by = None
    room.reviewed_at = None
    db.commit()
    return get_partner_room(db, user, room.id)


def delete_partner_room(db: Session, user: User, room_id: int) -> None:
    room = _room_for_partner(db, user, room_id)
    if _has_confirmed_bookings(db, room.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a room type that has confirmed bookings",
        )
    db.delete(room)
    db.commit()


def submit_partner_room(db: Session, user: User, room_id: int) -> PartnerRoomTypeResponse:
    room = _room_for_partner(db, user, room_id)
    if not room.description or not room.description.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Add a room description before submitting for validation",
        )
    if not room.images:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Add at least one room image before submitting for validation",
        )
    room.status = RoomTypeStatus.PENDING
    room.review_notes = None
    db.commit()
    return get_partner_room(db, user, room.id)


def add_partner_room_image(db: Session, user: User, room_id: int, data: RoomImageCreate) -> RoomImageResponse:
    room = _room_for_partner(db, user, room_id)
    if data.is_cover:
        for existing in room.images:
            existing.is_cover = False
    elif not room.images:
        data.is_cover = True
    image = RoomImage(room_type_id=room.id, **data.model_dump())
    db.add(image)
    db.commit()
    db.refresh(image)
    return RoomImageResponse.model_validate(image)


async def upload_partner_room_image(
    db: Session,
    user: User,
    room_id: int,
    file: UploadFile,
    *,
    alt_text: str | None = None,
    is_cover: bool = False,
) -> RoomImageResponse:
    room = _room_for_partner(db, user, room_id)
    public_url, storage_key, content_type, file_size = await media_storage.store_hotel_image(room.hotel_id, file)
    if is_cover:
        for existing in room.images:
            existing.is_cover = False
    elif not any(img.is_cover for img in room.images):
        is_cover = True

    image = RoomImage(
        room_type_id=room.id,
        image_url=public_url,
        alt_text=alt_text.strip() if alt_text else None,
        is_cover=is_cover,
        display_order=len(room.images),
    )
    try:
        db.add(image)
        db.commit()
        db.refresh(image)
    except Exception:
        db.rollback()
        media_storage.delete_stored_file(storage_key)
        raise
    return RoomImageResponse.model_validate(image)


def set_partner_room_cover_image(db: Session, user: User, room_id: int, image_id: int) -> RoomImageResponse:
    room = _room_for_partner(db, user, room_id)
    target = hotel_repository.get_room_image(db, room.id, image_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room image not found")
    for img in room.images:
        img.is_cover = (img.id == target.id)
    db.commit()
    db.refresh(target)
    return RoomImageResponse.model_validate(target)


def delete_partner_room_image(db: Session, user: User, room_id: int, image_id: int) -> None:
    room = _room_for_partner(db, user, room_id)
    image = hotel_repository.get_room_image(db, room.id, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room image not found")
    db.delete(image)
    db.commit()


def review_room(db: Session, admin: User, room_id: int, data: RoomTypeReviewRequest) -> PartnerRoomTypeResponse:
    room = db.get(RoomType, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    if data.action == RoomTypeStatus.BOOKABLE and room.status != RoomTypeStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Only an approved room type can become bookable")
    previous_status = room.status
    room.status = data.action
    room.review_notes = data.review_notes
    room.reviewed_by = admin.id
    room.reviewed_at = datetime.now(timezone.utc)
    audit_service.record(
        db,
        actor=admin,
        action="ROOM_TYPE_REVIEWED",
        target_type="ROOM_TYPE",
        target_id=room.id,
        reason=data.review_notes or f"Room review moved to {data.action.value}",
        previous_value={"status": previous_status.value},
        new_value={"status": room.status.value, "hotel_id": room.hotel_id, "version": room.version},
    )
    db.commit()
    db.refresh(room)
    return _response(room)
