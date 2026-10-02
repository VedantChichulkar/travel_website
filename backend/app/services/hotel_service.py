from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.hotel import (
    Amenity,
    Hotel,
    HotelImage,
    HotelStatus,
    HotelPolicy,
    RoomImage,
    RoomType,
)
from app.repositories import hotel_repository as repository
from app.schemas.hotel import (
    AmenityAssignment,
    AmenityCreate,
    HotelCreate,
    HotelImageCreate,
    HotelPolicyCreate,
    HotelPolicyUpdate,
    HotelUpdate,
    RoomImageCreate,
    RoomTypeCreate,
    RoomTypeUpdate,
)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


def _commit(db: Session, conflict_detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_detail) from exc


def _set_values(instance: object, values: dict[str, object]) -> None:
    for field, value in values.items():
        setattr(instance, field, value)


def create_hotel(db: Session, data: HotelCreate) -> Hotel:
    if repository.get_hotel_by_slug(db, data.slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel slug already exists")
    hotel = Hotel(**data.model_dump())
    repository.add(db, hotel)
    _commit(db, "Hotel slug already exists")
    db.refresh(hotel)
    return hotel


def list_hotels(db: Session, *, offset: int, limit: int, search: str | None = None, hotel_status: HotelStatus | None = None) -> list[Hotel]:
    return repository.list_hotels(db, offset=offset, limit=limit, search=search, hotel_status=hotel_status)


def get_hotel(db: Session, hotel_id: int, *, detailed: bool = True) -> Hotel:
    hotel = repository.get_hotel(db, hotel_id, detailed=detailed)
    if hotel is None:
        raise _not_found("Hotel")
    return hotel


def update_hotel(db: Session, hotel_id: int, data: HotelUpdate) -> Hotel:
    hotel = get_hotel(db, hotel_id, detailed=False)
    changes = data.model_dump(exclude_unset=True)
    if "booking_gateway_status" in changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Use the booking gateway governance endpoint to change booking mode",
        )
    required = {"name", "slug", "property_type", "star_rating", "address_line1", "city", "state", "country", "postal_code", "check_in_time", "check_out_time", "is_featured"}
    if any(changes.get(field) is None for field in required if field in changes):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Required hotel fields cannot be null")
    new_slug = changes.get("slug")
    if isinstance(new_slug, str):
        existing = repository.get_hotel_by_slug(db, new_slug)
        if existing and existing.id != hotel.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel slug already exists")
    _set_values(hotel, changes)
    _commit(db, "Hotel slug already exists")
    db.refresh(hotel)
    return hotel


def add_hotel_image(db: Session, hotel_id: int, data: HotelImageCreate) -> HotelImage:
    hotel = get_hotel(db, hotel_id, detailed=True)
    if data.is_cover:
        for image in hotel.images:
            image.is_cover = False
    image = HotelImage(hotel_id=hotel_id, **data.model_dump())
    repository.add(db, image)
    db.commit()
    db.refresh(image)
    return image


def delete_hotel_image(db: Session, hotel_id: int, image_id: int) -> None:
    get_hotel(db, hotel_id, detailed=False)
    image = repository.get_hotel_image(db, hotel_id, image_id)
    if image is None:
        raise _not_found("Hotel image")
    db.delete(image)
    db.commit()


def create_amenity(db: Session, data: AmenityCreate) -> Amenity:
    if repository.get_amenity_by_slug(db, data.slug) or repository.get_amenity_by_name(db, data.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Amenity name or slug already exists")
    amenity = Amenity(**data.model_dump())
    repository.add(db, amenity)
    _commit(db, "Amenity name or slug already exists")
    db.refresh(amenity)
    return amenity


def list_amenities(db: Session, *, active_only: bool) -> list[Amenity]:
    return repository.list_amenities(db, active_only=active_only)


def assign_amenities(db: Session, hotel_id: int, data: AmenityAssignment) -> list[Amenity]:
    hotel = get_hotel(db, hotel_id, detailed=True)
    amenities = repository.get_amenities_by_ids(db, data.amenity_ids)
    if len(amenities) != len(data.amenity_ids):
        found = {amenity.id for amenity in amenities}
        missing = [amenity_id for amenity_id in data.amenity_ids if amenity_id not in found]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Amenities not found: {missing}")
    hotel.amenities = amenities
    db.commit()
    return amenities


def create_policy(db: Session, hotel_id: int, data: HotelPolicyCreate) -> HotelPolicy:
    get_hotel(db, hotel_id, detailed=False)
    if repository.get_policy(db, hotel_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel policy already exists")
    policy = HotelPolicy(hotel_id=hotel_id, **data.model_dump())
    repository.add(db, policy)
    _commit(db, "Hotel policy already exists")
    db.refresh(policy)
    return policy


def get_policy(db: Session, hotel_id: int) -> HotelPolicy:
    get_hotel(db, hotel_id, detailed=False)
    policy = repository.get_policy(db, hotel_id)
    if policy is None:
        raise _not_found("Hotel policy")
    return policy


def update_policy(db: Session, hotel_id: int, data: HotelPolicyUpdate) -> HotelPolicy:
    policy = get_policy(db, hotel_id)
    _set_values(policy, data.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(policy)
    return policy


def _validate_room_capacity(room: RoomType) -> None:
    if room.max_guests > room.max_adults + room.max_children:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="max_guests cannot exceed max_adults plus max_children",
        )


def create_room_type(db: Session, hotel_id: int, data: RoomTypeCreate) -> RoomType:
    get_hotel(db, hotel_id, detailed=False)
    if repository.get_room_type_by_name(db, hotel_id, data.name):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type name already exists for this hotel")
    room = RoomType(hotel_id=hotel_id, **data.model_dump())
    repository.add(db, room)
    _commit(db, "Room type name already exists for this hotel")
    db.refresh(room)
    return repository.get_room_type(db, room.id) or room


def get_room_type(db: Session, room_type_id: int) -> RoomType:
    room = repository.get_room_type(db, room_type_id)
    if room is None:
        raise _not_found("Room type")
    return room


def list_room_types(db: Session, hotel_id: int) -> list[RoomType]:
    get_hotel(db, hotel_id, detailed=False)
    return repository.list_room_types(db, hotel_id)


def update_room_type(db: Session, room_type_id: int, data: RoomTypeUpdate) -> RoomType:
    room = get_room_type(db, room_type_id)
    changes = data.model_dump(exclude_unset=True)
    required = {"name", "max_adults", "max_children", "max_guests", "bed_type", "bed_count", "base_price", "currency", "total_rooms"}
    if any(changes.get(field) is None for field in required if field in changes):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Required room fields cannot be null")
    if isinstance(changes.get("name"), str):
        existing = repository.get_room_type_by_name(db, room.hotel_id, str(changes["name"]))
        if existing and existing.id != room.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type name already exists for this hotel")
    _set_values(room, changes)
    _validate_room_capacity(room)
    _commit(db, "Room type name already exists for this hotel")
    return repository.get_room_type(db, room.id) or room


def update_room_status(db: Session, room_type_id: int, is_active: bool) -> RoomType:
    room = get_room_type(db, room_type_id)
    room.is_active = is_active
    db.commit()
    db.refresh(room)
    return room


def add_room_image(db: Session, room_type_id: int, data: RoomImageCreate) -> RoomImage:
    room = get_room_type(db, room_type_id)
    if data.is_cover:
        for image in room.images:
            image.is_cover = False
    image = RoomImage(room_type_id=room_type_id, **data.model_dump())
    repository.add(db, image)
    db.commit()
    db.refresh(image)
    return image


def delete_room_image(db: Session, room_type_id: int, image_id: int) -> None:
    get_room_type(db, room_type_id)
    image = repository.get_room_image(db, room_type_id, image_id)
    if image is None:
        raise _not_found("Room image")
    db.delete(image)
    db.commit()
