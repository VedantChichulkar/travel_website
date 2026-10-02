"""Transactional room-inventory operations shared by partner and booking flows.

All mutations lock the affected date rows in ascending order.  This makes a
multi-night hold and a partner update serialize on the same capacity records.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.hotel import InventoryHold, InventoryHoldStatus, RoomInventory, RoomType
from app.models.user import User
from app.schemas.hotel import PartnerInventoryRangeUpdate, RoomInventoryCreate, RoomInventoryUpdate
from app.services import audit_service


def _dates(check_in: date, check_out: date) -> list[date]:
    return [date.fromordinal(day) for day in range(check_in.toordinal(), check_out.toordinal())]


def _locked_rows(db: Session, room_type_id: int, dates: list[date]) -> list[RoomInventory]:
    rows = list(db.scalars(
        select(RoomInventory)
        .where(RoomInventory.room_type_id == room_type_id, RoomInventory.inventory_date.in_(dates))
        .order_by(RoomInventory.inventory_date)
        .with_for_update()
    ))
    if len(rows) != len(dates):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory is unavailable for one or more stay dates")
    return rows


def _confirmed_by_date(db: Session, room_type_id: int, dates: list[date]) -> dict[date, int]:
    bookings = list(db.scalars(select(Booking).where(
        Booking.room_type_id == room_type_id,
        Booking.status == BookingStatus.CONFIRMED,
        Booking.check_in <= dates[-1],
        Booking.check_out > dates[0],
    )))
    return {day: sum(booking.rooms for booking in bookings if booking.check_in <= day < booking.check_out) for day in dates}


def expire_holds(db: Session, *, room_type_id: int | None = None, now: datetime | None = None) -> int:
    """Expire due holds.  Call within the caller transaction before capacity checks."""
    current = now or datetime.now(timezone.utc)
    query = select(InventoryHold).where(InventoryHold.status == InventoryHoldStatus.ACTIVE, InventoryHold.expires_at <= current)
    if room_type_id is not None:
        query = query.where(InventoryHold.room_type_id == room_type_id)
    holds = list(db.scalars(query.with_for_update()))
    for hold in holds:
        rows = _locked_rows(db, hold.room_type_id, _dates(hold.check_in, hold.check_out))
        for row in rows:
            row.held_inventory -= hold.rooms
            row.available_inventory += hold.rooms
        hold.status = InventoryHoldStatus.EXPIRED
    return len(holds)


def _reconcile_rows(db: Session, room_type_id: int, rows: list[RoomInventory]) -> None:
    dates = [row.inventory_date for row in rows]
    confirmed = _confirmed_by_date(db, room_type_id, dates)
    active_holds = list(db.scalars(select(InventoryHold).where(
        InventoryHold.room_type_id == room_type_id,
        InventoryHold.status == InventoryHoldStatus.ACTIVE,
        InventoryHold.check_in <= dates[-1],
        InventoryHold.check_out > dates[0],
    )))
    for row in rows:
        # Rows created before commitment counters may already have a lower
        # available value. Preserve that allocation until the partner explicitly
        # rewrites the date through the inventory API.
        implicit_allocation = max(
            0,
            row.total_inventory - row.blocked_inventory - row.available_inventory - row.confirmed_inventory - row.held_inventory,
        )
        held = sum(hold.rooms for hold in active_holds if hold.check_in <= row.inventory_date < hold.check_out)
        row.confirmed_inventory = confirmed[row.inventory_date]
        row.held_inventory = held
        row.available_inventory = row.total_inventory - row.blocked_inventory - implicit_allocation - row.confirmed_inventory - row.held_inventory
        if row.available_inventory < 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory is below existing confirmed or held commitments")


def _apply_capacity_settings(
    rows: list[RoomInventory],
    *,
    room_total: int,
    total_inventory: int | None,
    blocked_inventory: int | None,
    price: Decimal | None,
    is_closed: bool | None,
) -> None:
    """Apply capacity settings after rows and commitment counters are locked."""
    for row in rows:
        if total_inventory is not None:
            if total_inventory > room_total:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="total_inventory cannot exceed room type total_rooms")
            row.total_inventory = total_inventory
        if blocked_inventory is not None:
            row.blocked_inventory = blocked_inventory
        if price is not None:
            row.price = price
        if is_closed is not None:
            row.is_closed = is_closed
        committed = row.blocked_inventory + row.confirmed_inventory + row.held_inventory
        if committed > row.total_inventory:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory cannot drop below confirmed bookings, active holds, and blocked rooms")
        row.available_inventory = row.total_inventory - committed


def _snapshot(row: RoomInventory) -> dict[str, object]:
    return {
        "inventory_date": row.inventory_date.isoformat(),
        "total_inventory": row.total_inventory,
        "available_inventory": row.available_inventory,
        "blocked_inventory": row.blocked_inventory,
        "confirmed_inventory": row.confirmed_inventory,
        "held_inventory": row.held_inventory,
        "price": str(row.price),
        "is_closed": row.is_closed,
    }


def update_partner_range(db: Session, room: RoomType, data: PartnerInventoryRangeUpdate) -> list[RoomInventory]:
    if data.start_date < date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Inventory can only be managed for today and future dates")
    days = _dates(data.start_date, data.end_date + timedelta(days=1))
    # Create missing future rows first. The unique room/date key remains the final
    # arbiter if concurrent first-time setup is attempted.
    existing = {item.inventory_date: item for item in db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == room.id, RoomInventory.inventory_date.in_(days)))}
    for day in days:
        if day not in existing:
            db.add(RoomInventory(room_type_id=room.id, inventory_date=day, total_inventory=room.total_rooms, available_inventory=room.total_rooms, blocked_inventory=0, confirmed_inventory=0, held_inventory=0, price=room.base_price, is_closed=False))
    db.flush()
    expire_holds(db, room_type_id=room.id)
    rows = _locked_rows(db, room.id, days)
    _reconcile_rows(db, room.id, rows)
    _apply_capacity_settings(
        rows,
        room_total=room.total_rooms,
        total_inventory=data.total_inventory,
        blocked_inventory=data.blocked_inventory,
        price=data.price,
        is_closed=data.is_closed,
    )
    db.commit()
    return rows


def list_inventory(
    db: Session,
    room: RoomType,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[RoomInventory]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_date cannot be after end_date")
    expire_holds(db, room_type_id=room.id)
    query = select(RoomInventory).where(RoomInventory.room_type_id == room.id)
    if start_date:
        query = query.where(RoomInventory.inventory_date >= start_date)
    if end_date:
        query = query.where(RoomInventory.inventory_date <= end_date)
    rows = list(db.scalars(query.order_by(RoomInventory.inventory_date).with_for_update()))
    if rows:
        _reconcile_rows(db, room.id, rows)
    db.commit()
    return rows


def create_admin_inventory(db: Session, room: RoomType, data: RoomInventoryCreate, admin: User) -> RoomInventory:
    """Compatibility implementation for the legacy single-date admin route."""
    if db.scalar(select(RoomInventory.id).where(RoomInventory.room_type_id == room.id, RoomInventory.inventory_date == data.inventory_date)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory already exists for this date")
    blocked = data.blocked_inventory
    if data.available_inventory is not None:
        # Old callers represented some unavailable capacity outside the blocked
        # counter. Fold that capacity into the explicit protected counter.
        blocked = data.total_inventory - data.available_inventory
    row = RoomInventory(
        room_type_id=room.id,
        inventory_date=data.inventory_date,
        total_inventory=data.total_inventory,
        available_inventory=data.total_inventory - blocked,
        blocked_inventory=blocked,
        confirmed_inventory=0,
        held_inventory=0,
        price=data.price,
        is_closed=data.is_closed,
    )
    db.add(row)
    db.flush()
    locked = _locked_rows(db, room.id, [data.inventory_date])
    _reconcile_rows(db, room.id, locked)
    _apply_capacity_settings(
        locked,
        room_total=room.total_rooms,
        total_inventory=data.total_inventory,
        blocked_inventory=blocked,
        price=data.price,
        is_closed=data.is_closed,
    )
    audit_service.record(db, actor=admin, action="ROOM_INVENTORY_CREATED", target_type="ROOM_INVENTORY", target_id=row.id, reason="Administrative inventory creation", new_value=_snapshot(row))
    db.commit()
    db.refresh(row)
    return row


def update_admin_inventory(db: Session, inventory_id: int, data: RoomInventoryUpdate, admin: User) -> RoomInventory:
    row = db.get(RoomInventory, inventory_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room inventory not found")
    room = db.get(RoomType, row.room_type_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    expire_holds(db, room_type_id=room.id)
    row = _locked_rows(db, room.id, [row.inventory_date])[0]
    _reconcile_rows(db, room.id, [row])
    before = _snapshot(row)
    target_total = data.total_inventory if data.total_inventory is not None else row.total_inventory
    blocked = data.blocked_inventory
    if data.available_inventory is not None:
        inferred = target_total - row.confirmed_inventory - row.held_inventory - data.available_inventory
        if inferred < 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Available inventory conflicts with held or confirmed commitments")
        if blocked is not None and blocked != inferred:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="available_inventory must match capacity after blocked and committed inventory")
        blocked = inferred
    _apply_capacity_settings(
        [row],
        room_total=room.total_rooms,
        total_inventory=data.total_inventory,
        blocked_inventory=blocked,
        price=data.price,
        is_closed=data.is_closed,
    )
    audit_service.record(db, actor=admin, action="ROOM_INVENTORY_UPDATED", target_type="ROOM_INVENTORY", target_id=row.id, reason="Administrative inventory update", previous_value=before, new_value=_snapshot(row))
    db.commit()
    db.refresh(row)
    return row


def list_partner_inventory(db: Session, room: RoomType, start_date: date, end_date: date) -> list[RoomInventory]:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="end_date cannot be before start_date")
    expire_holds(db, room_type_id=room.id)
    rows = list(db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == room.id, RoomInventory.inventory_date >= start_date, RoomInventory.inventory_date <= end_date).order_by(RoomInventory.inventory_date)))
    if rows:
        rows = _locked_rows(db, room.id, [row.inventory_date for row in rows])
        _reconcile_rows(db, room.id, rows)
    db.commit()
    return rows


def create_hold(db: Session, *, room: RoomType, user_id: int | None, check_in: date, check_out: date, rooms: int, expires_at: datetime) -> InventoryHold:
    if check_in < date.today() or check_out <= check_in or expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid hold dates or expiry")
    days = _dates(check_in, check_out)
    expire_holds(db, room_type_id=room.id)
    rows = _locked_rows(db, room.id, days)
    _reconcile_rows(db, room.id, rows)
    if any(row.is_closed or row.available_inventory < rooms for row in rows):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested rooms are unavailable for one or more stay dates")
    hold = InventoryHold(hold_token=uuid4().hex, hotel_id=room.hotel_id, room_type_id=room.id, user_id=user_id, check_in=check_in, check_out=check_out, rooms=rooms, expires_at=expires_at)
    for row in rows:
        row.held_inventory += rooms
        row.available_inventory -= rooms
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold


def validate_hold(db: Session, *, hold_token: str, user_id: int, room: RoomType, check_in: date, check_out: date, rooms: int) -> InventoryHold:
    """Lock and validate a hold without releasing its protected capacity."""
    hold = db.scalar(select(InventoryHold).where(InventoryHold.hold_token == hold_token).with_for_update())
    if hold is None or hold.user_id != user_id or hold.room_type_id != room.id or hold.hotel_id != room.hotel_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking hold not found")
    if hold.status != InventoryHoldStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking hold is no longer active")
    if hold.check_in != check_in or hold.check_out != check_out or hold.rooms != rooms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Booking details do not match the reserved hold")
    now = datetime.now(timezone.utc)
    expires_at = hold.expires_at if hold.expires_at.tzinfo else hold.expires_at.replace(tzinfo=timezone.utc)
    rows = _locked_rows(db, room.id, _dates(check_in, check_out))
    if expires_at <= now:
        for row in rows:
            row.held_inventory -= hold.rooms
            row.available_inventory += hold.rooms
        hold.status = InventoryHoldStatus.EXPIRED
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking hold has expired; please check availability again")
    return hold


def extend_hold(
    db: Session,
    *,
    hold_token: str,
    user_id: int,
    room: RoomType,
    check_in: date,
    check_out: date,
    rooms: int,
    expires_at: datetime,
) -> InventoryHold:
    """Extend an existing protected hold without changing capacity counters."""
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Hold expiry must be in the future")
    hold = validate_hold(db, hold_token=hold_token, user_id=user_id, room=room, check_in=check_in, check_out=check_out, rooms=rooms)
    hold.expires_at = expires_at
    return hold


def release_hold(
    db: Session,
    *,
    hold_token: str,
    final_status: InventoryHoldStatus,
) -> InventoryHold | None:
    """Idempotently release held capacity through the shared row-locking path."""
    if final_status not in (InventoryHoldStatus.CANCELLED, InventoryHoldStatus.EXPIRED):
        raise ValueError("A released hold must become CANCELLED or EXPIRED")
    hold = db.scalar(select(InventoryHold).where(InventoryHold.hold_token == hold_token).with_for_update())
    if hold is None or hold.status != InventoryHoldStatus.ACTIVE:
        return hold
    rows = _locked_rows(db, hold.room_type_id, _dates(hold.check_in, hold.check_out))
    for row in rows:
        if row.held_inventory < hold.rooms:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Held inventory cannot be released safely")
        row.held_inventory -= hold.rooms
        row.available_inventory += hold.rooms
    hold.status = final_status
    return hold


def finalize_hold_as_confirmed(db: Session, *, hold_token: str, user_id: int, room: RoomType, check_in: date, check_out: date, rooms: int) -> InventoryHold:
    """Convert a still-valid hold into a confirmed commitment under row locks."""
    hold = validate_hold(db, hold_token=hold_token, user_id=user_id, room=room, check_in=check_in, check_out=check_out, rooms=rooms)
    rows = _locked_rows(db, room.id, _dates(check_in, check_out))
    for row in rows:
        row.held_inventory -= hold.rooms
        row.confirmed_inventory += hold.rooms
    hold.status = InventoryHoldStatus.CONVERTED
    return hold


def validate_confirmed_inventory_release(db: Session, *, room: RoomType, check_in: date, check_out: date, rooms: int) -> None:
    """Lock and verify that every committed room-night can be released safely."""
    rows = _locked_rows(db, room.id, _dates(check_in, check_out))
    for row in rows:
        if row.confirmed_inventory < rooms:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmed inventory cannot be restored safely")


def release_confirmed_inventory(db: Session, *, room: RoomType, check_in: date, check_out: date, rooms: int) -> None:
    """Return a cancelled confirmed booking's capacity under the same date locks."""
    validate_confirmed_inventory_release(db, room=room, check_in=check_in, check_out=check_out, rooms=rooms)
    rows = _locked_rows(db, room.id, _dates(check_in, check_out))
    for row in rows:
        row.confirmed_inventory -= rooms
        row.available_inventory += rooms


def claim_hold(db: Session, *, hold_token: str, user_id: int, room: RoomType, check_in: date, check_out: date, rooms: int) -> InventoryHold:
    """Compatibility alias for finalizing a hold into a confirmed booking."""
    return finalize_hold_as_confirmed(db, hold_token=hold_token, user_id=user_id, room=room, check_in=check_in, check_out=check_out, rooms=rooms)
