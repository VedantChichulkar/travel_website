from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.booking import Booking
from app.models.hotel import Hotel, RoomInventory, RoomType


BOOKING_LOADS = (
    selectinload(Booking.travellers),
    selectinload(Booking.status_history),
    selectinload(Booking.hotel),
    selectinload(Booking.room_type),
)


def get_hotel(db: Session, hotel_id: int) -> Hotel | None:
    return db.get(Hotel, hotel_id)


def get_room_type(db: Session, room_type_id: int) -> RoomType | None:
    return db.get(RoomType, room_type_id)


def list_inventory(db: Session, room_type_id: int, start: date, end: date) -> list[RoomInventory]:
    return list(db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == room_type_id, RoomInventory.inventory_date >= start, RoomInventory.inventory_date <= end).order_by(RoomInventory.inventory_date)))


def get_booking(db: Session, booking_id: int) -> Booking | None:
    return db.scalar(select(Booking).where(Booking.id == booking_id).options(*BOOKING_LOADS))


def get_by_idempotency_key(db: Session, user_id: int, key: str) -> Booking | None:
    return db.scalar(select(Booking).where(Booking.user_id == user_id, Booking.idempotency_key == key).options(*BOOKING_LOADS))


def reference_exists(db: Session, reference: str) -> bool:
    return db.scalar(select(Booking.id).where(Booking.booking_reference == reference).limit(1)) is not None


def list_user_bookings(db: Session, user_id: int) -> list[Booking]:
    return list(db.scalars(select(Booking).where(Booking.user_id == user_id).options(*BOOKING_LOADS).order_by(Booking.created_at.desc())))


def list_bookings(db: Session) -> list[Booking]:
    return list(db.scalars(select(Booking).options(*BOOKING_LOADS).order_by(Booking.created_at.desc())))
