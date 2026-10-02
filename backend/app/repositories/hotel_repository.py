from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.hotel import (
    Amenity,
    BookingGatewayStatus,
    Hotel,
    HotelImage,
    HotelPolicy,
    RoomImage,
    RoomInventory,
    RoomType,
    HotelStatus,
    PropertyType,
)
from app.models.hotel_verification import HotelVerification, VerificationStatus
if TYPE_CHECKING:
    from app.services.destination_service import HotelLocationFilter


def add(db: Session, instance: object) -> None:
    db.add(instance)


def get_hotel_by_slug(db: Session, slug: str) -> Hotel | None:
    return db.scalar(select(Hotel).where(Hotel.slug == slug))


def get_hotel_by_partner_id(db: Session, partner_id: int) -> Hotel | None:
    return db.scalar(
        select(Hotel).where(Hotel.partner_id == partner_id).options(
            selectinload(Hotel.images), selectinload(Hotel.amenities)
        )
    )


def get_hotel(db: Session, hotel_id: int, *, detailed: bool = False) -> Hotel | None:
    statement = select(Hotel).where(Hotel.id == hotel_id)
    if detailed:
        statement = statement.options(
            selectinload(Hotel.images),
            selectinload(Hotel.amenities),
            selectinload(Hotel.policy),
            selectinload(Hotel.room_types).selectinload(RoomType.images),
        )
    return db.scalar(statement)


def list_hotels(db: Session, *, offset: int, limit: int, search: str | None = None, hotel_status: HotelStatus | None = None) -> list[Hotel]:
    statement = select(Hotel)
    if search:
        term = f"%{search.strip().lower()}%"
        statement = statement.where(or_(func.lower(Hotel.name).like(term), func.lower(Hotel.slug).like(term), func.lower(Hotel.city).like(term)))
    if hotel_status:
        statement = statement.where(Hotel.status == hotel_status)
    return list(db.scalars(statement.order_by(Hotel.id.desc()).offset(offset).limit(limit)))


def list_public_hotels(
    db: Session,
    *,
    city: str | None,
    district: str | None = None,
    location_filter: HotelLocationFilter | None = None,
    property_type: PropertyType | None,
    star_rating: int | None,
) -> list[Hotel]:
    statement = (
        select(Hotel)
        .join(HotelVerification, HotelVerification.hotel_id == Hotel.id)
        .where(
            Hotel.status == HotelStatus.ACTIVE,
            HotelVerification.verification_status == VerificationStatus.APPROVED,
        )
        .options(
            selectinload(Hotel.images),
            selectinload(Hotel.amenities),
            selectinload(Hotel.room_types).selectinload(RoomType.images),
            selectinload(Hotel.district_ref),
            selectinload(Hotel.destination_ref),
        )
    )
    if city:
        statement = statement.where(Hotel.city.ilike(f"%{city.strip()}%"))
    if district:
        statement = statement.where(Hotel.district.ilike(f"%{district.strip()}%"))
    if location_filter is not None:
        clauses = []
        if location_filter.destination_ids:
            clauses.append(Hotel.destination_id.in_(location_filter.destination_ids))
        if location_filter.destination_names:
            clauses.append(
                (Hotel.destination_id.is_(None))
                & func.lower(func.trim(Hotel.city)).in_(location_filter.destination_names)
            )
        if not location_filter.destination_ids:
            if location_filter.district_ids:
                clauses.append(Hotel.district_id.in_(location_filter.district_ids))
            if location_filter.district_names:
                clauses.extend(
                    [
                        func.lower(func.trim(Hotel.district)).in_(location_filter.district_names),
                        (Hotel.district_id.is_(None))
                        & func.lower(func.trim(Hotel.city)).in_(location_filter.district_names),
                    ]
                )
        statement = statement.where(or_(*clauses) if clauses else false())
    if property_type:
        statement = statement.where(Hotel.property_type == property_type)
    if star_rating is not None:
        statement = statement.where(Hotel.star_rating >= star_rating)
    return list(db.scalars(statement.order_by(Hotel.is_featured.desc(), Hotel.name)))


def get_public_hotel(db: Session, hotel_ref: int | str) -> Hotel | None:
    identity = Hotel.id == int(hotel_ref) if isinstance(hotel_ref, int) or str(hotel_ref).isdigit() else Hotel.slug == str(hotel_ref).strip().lower()
    return db.scalar(
        select(Hotel)
        .join(HotelVerification, HotelVerification.hotel_id == Hotel.id)
        .where(
            identity,
            Hotel.status == HotelStatus.ACTIVE,
            HotelVerification.verification_status == VerificationStatus.APPROVED,
        )
        .options(
            selectinload(Hotel.images),
            selectinload(Hotel.amenities),
            selectinload(Hotel.policy),
            selectinload(Hotel.room_types).selectinload(RoomType.images),
            selectinload(Hotel.district_ref),
            selectinload(Hotel.destination_ref),
        )
    )


def get_hotel_image(db: Session, hotel_id: int, image_id: int) -> HotelImage | None:
    return db.scalar(
        select(HotelImage).where(HotelImage.id == image_id, HotelImage.hotel_id == hotel_id)
    )


def get_amenity_by_slug(db: Session, slug: str) -> Amenity | None:
    return db.scalar(select(Amenity).where(Amenity.slug == slug))


def get_amenity_by_name(db: Session, name: str) -> Amenity | None:
    return db.scalar(select(Amenity).where(Amenity.name == name))


def get_amenity_by_id(db: Session, amenity_id: int) -> Amenity | None:
    return db.get(Amenity, amenity_id)


def get_amenities_by_ids(db: Session, amenity_ids: list[int]) -> list[Amenity]:
    if not amenity_ids:
        return []
    return list(db.scalars(select(Amenity).where(Amenity.id.in_(amenity_ids)).order_by(Amenity.id)))


def list_amenities(db: Session, *, active_only: bool = False) -> list[Amenity]:
    statement = select(Amenity).order_by(Amenity.category, Amenity.name)
    if active_only:
        statement = statement.where(Amenity.is_active.is_(True))
    return list(db.scalars(statement))


def get_room_type(db: Session, hotel_id_or_room_type_id: int, room_type_id: int | None = None, *, detailed: bool = False) -> RoomType | None:
    """Load globally for admin calls or hotel-scoped for partner calls."""
    resolved_room_id = room_type_id if room_type_id is not None else hotel_id_or_room_type_id
    statement = select(RoomType).where(RoomType.id == resolved_room_id)
    if room_type_id is not None:
        statement = statement.where(RoomType.hotel_id == hotel_id_or_room_type_id)
    if detailed:
        statement = statement.options(selectinload(RoomType.images), selectinload(RoomType.inventory), selectinload(RoomType.amenities))
    return db.scalar(statement)


def get_room_type_by_name(db: Session, hotel_id: int, name: str) -> RoomType | None:
    return db.scalar(select(RoomType).where(RoomType.hotel_id == hotel_id, RoomType.name == name))


def list_room_types(db: Session, hotel_id: int, *, active_only: bool = False) -> list[RoomType]:
    statement = (
        select(RoomType)
        .where(RoomType.hotel_id == hotel_id)
        .options(selectinload(RoomType.images), selectinload(RoomType.amenities))
        .order_by(RoomType.id)
    )
    if active_only:
        statement = statement.where(RoomType.is_active.is_(True))
    return list(db.scalars(statement))


def get_room_image(db: Session, room_type_id: int, image_id: int) -> RoomImage | None:
    return db.scalar(
        select(RoomImage).where(RoomImage.id == image_id, RoomImage.room_type_id == room_type_id)
    )


def get_policy(db: Session, hotel_id: int) -> HotelPolicy | None:
    return db.scalar(select(HotelPolicy).where(HotelPolicy.hotel_id == hotel_id))


def get_inventory(db: Session, inventory_id: int) -> RoomInventory | None:
    return db.get(RoomInventory, inventory_id)


def get_inventory_by_date(db: Session, room_type_id: int, inventory_date: date) -> RoomInventory | None:
    return get_inventory_item(db, room_type_id, inventory_date)


def get_inventory_item(db: Session, room_type_id: int, inventory_date: date) -> RoomInventory | None:
    return db.scalar(
        select(RoomInventory).where(
            RoomInventory.room_type_id == room_type_id,
            RoomInventory.inventory_date == inventory_date,
        )
    )


def list_inventory(
    db: Session,
    room_type_id: int,
    *,
    start_date: date | None,
    end_date: date | None,
) -> list[RoomInventory]:
    statement = select(RoomInventory).where(RoomInventory.room_type_id == room_type_id)
    if start_date is not None:
        statement = statement.where(RoomInventory.inventory_date >= start_date)
    if end_date is not None:
        statement = statement.where(RoomInventory.inventory_date <= end_date)
    return list(db.scalars(statement.order_by(RoomInventory.inventory_date)))


def delete(db: Session, instance: object) -> None:
    db.delete(instance)
