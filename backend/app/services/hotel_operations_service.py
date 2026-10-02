"""Tenant-scoped front-desk operations for confirmed hotel bookings."""

import secrets
import logging
from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import Booking, BookingStatus, BookingStatusHistory
from app.models.hotel import Hotel
from app.models.user import User
from app.repositories import hotel_repository
from app.services import cancellation_service, inventory_service
from app.services import notification_service
from app.models.communication import NotificationEventType


logger = logging.getLogger(__name__)


OPERATION_LOADS = (
    selectinload(Booking.travellers),
    selectinload(Booking.room_type),
    selectinload(Booking.hotel),
    selectinload(Booking.status_history),
    selectinload(Booking.cancellation),
)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _scheduled(day: date, hotel_time: time | None) -> datetime:
    return datetime.combine(day, hotel_time or time.min, tzinfo=timezone.utc)


def _hotel(db: Session, user: User) -> Hotel:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return hotel


def _base_query(hotel_id: int) -> Select[tuple[Booking]]:
    return select(Booking).where(Booking.hotel_id == hotel_id).options(*OPERATION_LOADS)


def _operations_booking(
    db: Session,
    hotel: Hotel,
    booking_id: int | None = None,
    booking_reference: str | None = None,
    qr_token: str | None = None,
) -> Booking:
    query = _base_query(hotel.id)
    if booking_id is not None:
        query = query.where(Booking.id == booking_id)
    elif booking_reference is not None:
        query = query.where(Booking.booking_reference == booking_reference.strip().upper())
    else:
        query = query.where(Booking.operation_qr_token == qr_token)
    booking = db.scalar(query.with_for_update())
    if booking is None:
        # Tenant-safe 404 does not reveal whether another hotel owns the booking.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def _append(
    booking: Booking,
    old: BookingStatus,
    new: BookingStatus,
    user_id: int | None,
    note: str,
) -> None:
    booking.status = new
    booking.status_history.append(
        BookingStatusHistory(
            old_status=old,
            new_status=new,
            changed_by_user_id=user_id,
            note=note,
        )
    )


def _reminder_history(booking: Booking) -> BookingStatusHistory | None:
    return next(
        (
            item
            for item in reversed(booking.status_history)
            if item.note and item.note.startswith("No-show reminder due:")
        ),
        None,
    )


def operation_metadata(booking: Booking, now: datetime | None = None) -> dict[str, object]:
    """Derive UI-safe operational metadata from the status audit trail."""
    current = now or datetime.now(timezone.utc)
    hotel = booking.hotel
    history = booking.status_history[-1] if booking.status_history else None
    reminder = _reminder_history(booking)
    scheduled_arrival = _scheduled(booking.check_in, hotel.check_in_time if hotel else None)
    scheduled_checkout = _scheduled(booking.check_out, hotel.check_out_time if hotel else None)
    no_show_eligible_at = scheduled_arrival + timedelta(hours=settings.NO_SHOW_FALLBACK_HOURS)
    if reminder is not None and reminder.created_at:
        no_show_eligible_at = max(
            no_show_eligible_at,
            _utc(reminder.created_at) + timedelta(minutes=settings.NO_SHOW_REMINDER_OPPORTUNITY_MINUTES),
        )
    return {
        "status_note": history.note if history else None,
        "is_system_generated": bool(
            history
            and history.changed_by_user_id is None
            and booking.status in (BookingStatus.CHECKED_OUT, BookingStatus.NO_SHOW)
        ),
        "no_show_reminder_sent_at": reminder.created_at if reminder else None,
        "no_show_eligible_at": no_show_eligible_at,
        "auto_checkout_eligible_at": scheduled_checkout + timedelta(hours=settings.AUTO_CHECKOUT_GRACE_HOURS),
        "can_check_in": booking.status == BookingStatus.CONFIRMED,
        "can_check_out": booking.status == BookingStatus.CHECKED_IN,
        "can_report_no_show": booking.status == BookingStatus.CONFIRMED and current >= scheduled_arrival,
        "requires_financial_review": bool(booking.cancellation and booking.cancellation.requires_manual_review),
    }


def lookup(
    db: Session,
    user: User,
    *,
    booking_id: int | None = None,
    booking_reference: str | None = None,
    qr_token: str | None = None,
) -> Booking:
    if sum(value is not None for value in (booking_id, booking_reference, qr_token)) != 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide exactly one booking ID, booking reference, or QR token",
        )
    hotel = _hotel(db, user)
    booking = _operations_booking(db, hotel, booking_id, booking_reference, qr_token)
    if booking.operation_qr_token is None and booking.status == BookingStatus.CONFIRMED:
        booking.operation_qr_token = secrets.token_urlsafe(24)
        db.commit()
        db.refresh(booking)
    return booking


def list_board(db: Session, user: User, today: date | None = None) -> dict[str, list[Booking]]:
    hotel = _hotel(db, user)
    operational_day = today or datetime.now(timezone.utc).date()
    bookings = list(
        db.scalars(
            _base_query(hotel.id)
            .where(
                or_(
                    Booking.status.in_((BookingStatus.CONFIRMED, BookingStatus.CHECK_IN_ISSUE)),
                    Booking.status == BookingStatus.CHECKED_IN,
                )
            )
            .order_by(Booking.check_in, Booking.booking_reference)
        )
    )
    arrivals = [
        booking
        for booking in bookings
        if booking.check_in == operational_day
        and booking.status in (BookingStatus.CONFIRMED, BookingStatus.CHECK_IN_ISSUE, BookingStatus.CHECKED_IN)
    ]
    checked_in = sorted(
        (booking for booking in bookings if booking.status == BookingStatus.CHECKED_IN),
        key=lambda booking: (booking.check_out, booking.booking_reference),
    )
    no_show_actions = [
        booking
        for booking in bookings
        if booking.status == BookingStatus.CONFIRMED and booking.check_in <= operational_day
    ]
    issues = [booking for booking in bookings if booking.status == BookingStatus.CHECK_IN_ISSUE]
    return {
        "arrivals": arrivals,
        "checked_in": checked_in,
        "upcoming_checkouts": checked_in,
        "no_show_actions": no_show_actions,
        "check_in_issues": issues,
    }


def check_in(
    db: Session,
    user: User,
    booking_id: int,
    assigned_room: str,
    *,
    now: datetime | None = None,
) -> Booking:
    hotel = _hotel(db, user)
    booking = _operations_booking(db, hotel, booking_id)
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only confirmed bookings can be checked in")
    booking.assigned_room = assigned_room.strip()
    booking.checked_in_at = now or datetime.now(timezone.utc)
    _append(
        booking,
        BookingStatus.CONFIRMED,
        BookingStatus.CHECKED_IN,
        user.id,
        f"Hotel check-in; room assigned: {booking.assigned_room}",
    )
    notification_service.for_booking(db, booking, event_type=NotificationEventType.CHECK_IN, event_key=str(booking.id), title="Guest checked in", body=f"Check-in was recorded for booking {booking.booking_reference}.")
    db.commit()
    db.refresh(booking)
    return booking


def check_out(db: Session, user: User, booking_id: int, *, now: datetime | None = None) -> Booking:
    hotel = _hotel(db, user)
    booking = _operations_booking(db, hotel, booking_id)
    if booking.status != BookingStatus.CHECKED_IN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only checked-in bookings can be checked out")
    booking.checked_out_at = now or datetime.now(timezone.utc)
    _append(booking, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT, user.id, "Hotel check-out")
    notification_service.for_booking(db, booking, event_type=NotificationEventType.CHECK_OUT, event_key=str(booking.id), title="Guest checked out", body=f"Check-out was recorded for booking {booking.booking_reference}.")
    db.commit()
    db.refresh(booking)
    return booking


def report_issue(db: Session, user: User, booking_id: int, issue_type: str, reason: str) -> Booking:
    hotel = _hotel(db, user)
    booking = _operations_booking(db, hotel, booking_id)
    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only confirmed bookings can be sent for check-in review")
    _append(
        booking,
        BookingStatus.CONFIRMED,
        BookingStatus.CHECK_IN_ISSUE,
        user.id,
        f"Check-in issue / support review [{issue_type}]: {reason.strip()}",
    )
    notification_service.for_booking(db, booking, event_type=NotificationEventType.HOTEL_OPERATIONAL_ISSUE, event_key=f"{booking.id}:{len(booking.status_history)}", title="Check-in issue needs attention", body=f"Maharashtra Tourist Places support is reviewing an issue for booking {booking.booking_reference}.")
    db.commit()
    db.refresh(booking)
    return booking


def _no_show_note(booking: Booking) -> str:
    terms = str(booking.policy_snapshot.get("cancellation_policy") or "").lower()
    if "no-show" in terms or "no show" in terms:
        return "No-show recorded using the booking-time policy snapshot"
    return "No-show recorded; booking-time policy requires support review for financial action"


def _apply_no_show(
    db: Session,
    booking: Booking,
    *,
    actor_user_id: int | None,
    system_generated: bool,
) -> None:
    _append(
        booking,
        BookingStatus.CONFIRMED,
        BookingStatus.NO_SHOW,
        actor_user_id,
        ("System-generated no-show fallback: " if system_generated else "Hotel-reported no-show: ")
        + _no_show_note(booking),
    )
    cancellation_service.record_no_show_implication(
        db,
        booking,
        decided_by_user_id=actor_user_id,
        system_generated=system_generated,
    )
    inventory_service.release_confirmed_inventory(
        db,
        room=booking.room_type,
        check_in=booking.check_in,
        check_out=booking.check_out,
        rooms=booking.rooms,
    )
    notification_service.for_booking(db, booking, event_type=NotificationEventType.NO_SHOW, event_key=str(booking.id), title="No-show recorded", body=f"A no-show was recorded for booking {booking.booking_reference}.")


def report_no_show(
    db: Session,
    user: User,
    booking_id: int,
    *,
    now: datetime | None = None,
) -> Booking:
    hotel = _hotel(db, user)
    booking = _operations_booking(db, hotel, booking_id)
    current = now or datetime.now(timezone.utc)
    earliest = _scheduled(booking.check_in, hotel.check_in_time)
    if booking.status != BookingStatus.CONFIRMED or current < earliest:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an unarrived confirmed booking on or after its scheduled check-in can be marked no-show",
        )
    _apply_no_show(db, booking, actor_user_id=user.id, system_generated=False)
    db.commit()
    db.refresh(booking)
    return booking


def _run_due_fallbacks(db: Session, query: Select[tuple[Booking]], current: datetime) -> list[Booking]:
    changed: list[Booking] = []
    bookings = list(db.scalars(query.options(*OPERATION_LOADS).with_for_update()))
    for booking in bookings:
        hotel = booking.hotel
        if booking.status == BookingStatus.CHECKED_IN:
            checkout_at = _scheduled(booking.check_out, hotel.check_out_time)
            if current >= checkout_at - timedelta(hours=2):
                notification_service.for_booking(db, booking, event_type=NotificationEventType.CHECK_OUT_REMINDER, event_key=str(booking.id), title="Check-out reminder", body=f"Check-out is approaching for booking {booking.booking_reference}.")
            due = _scheduled(booking.check_out, hotel.check_out_time) + timedelta(hours=settings.AUTO_CHECKOUT_GRACE_HOURS)
            if current >= due:
                booking.checked_out_at = current
                _append(
                    booking,
                    BookingStatus.CHECKED_IN,
                    BookingStatus.CHECKED_OUT,
                    None,
                    "Auto-closed by Maharashtra Tourist Places after the configured checkout grace period",
                )
                notification_service.for_booking(db, booking, event_type=NotificationEventType.CHECK_OUT, event_key=str(booking.id), title="Stay checked out", body=f"Booking {booking.booking_reference} was automatically checked out after the configured grace period.")
                changed.append(booking)
            continue

        reminder = _reminder_history(booking)
        scheduled_arrival = _scheduled(booking.check_in, hotel.check_in_time)
        reminder_due = scheduled_arrival + timedelta(hours=settings.NO_SHOW_REMINDER_HOURS)
        if reminder is None and current >= reminder_due:
            _append(
                booking,
                BookingStatus.CONFIRMED,
                BookingStatus.CONFIRMED,
                None,
                "No-show reminder due: hotel action requested before automatic fallback",
            )
            notification_service.for_booking(db, booking, event_type=NotificationEventType.CHECK_IN_REMINDER, event_key=str(booking.id), title="Check-in action required", body=f"Booking {booking.booking_reference} still needs an arrival update.")
            changed.append(booking)
            continue

        if reminder is None:
            continue
        automatic_due = max(
            scheduled_arrival + timedelta(hours=settings.NO_SHOW_FALLBACK_HOURS),
            _utc(reminder.created_at) + timedelta(minutes=settings.NO_SHOW_REMINDER_OPPORTUNITY_MINUTES),
        )
        if current >= automatic_due:
            try:
                inventory_service.validate_confirmed_inventory_release(
                    db,
                    room=booking.room_type,
                    check_in=booking.check_in,
                    check_out=booking.check_out,
                    rooms=booking.rooms,
                )
            except HTTPException as exc:
                _append(
                    booking,
                    BookingStatus.CONFIRMED,
                    BookingStatus.CHECK_IN_ISSUE,
                    None,
                    "Automatic no-show paused: inventory ledger requires support review",
                )
                notification_service.for_booking(
                    db,
                    booking,
                    event_type=NotificationEventType.HOTEL_OPERATIONAL_ISSUE,
                    event_key=f"no-show-inventory:{booking.id}",
                    title="Arrival update needs support review",
                    body=f"Booking {booking.booking_reference} needs a Maharashtra Tourist Places operational review.",
                )
                logger.error(
                    "Automatic no-show paused for booking_id=%s because inventory could not be released: %s",
                    booking.id,
                    exc.detail,
                )
                changed.append(booking)
                continue
            _apply_no_show(db, booking, actor_user_id=None, system_generated=True)
            changed.append(booking)
    db.commit()
    return changed


def run_fallbacks(db: Session, user: User, now: datetime | None = None) -> list[Booking]:
    """Run due actions for one hotel; history distinguishes reminders and system actions."""
    hotel = _hotel(db, user)
    query = _base_query(hotel.id).where(Booking.status.in_((BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)))
    return _run_due_fallbacks(db, query, now or datetime.now(timezone.utc))


def run_all_fallbacks(db: Session, now: datetime | None = None) -> list[Booking]:
    """Scheduler entry point covering every hotel with idempotent status transitions."""
    query = select(Booking).where(Booking.status.in_((BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN)))
    return _run_due_fallbacks(db, query, now or datetime.now(timezone.utc))
