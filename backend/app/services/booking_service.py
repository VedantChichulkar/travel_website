import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, BookingTraveller, PaymentStatus
from app.models.communication import NotificationEventType
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, InventoryHoldStatus
from app.models.user import User, UserRole
from app.repositories import booking_repository as repository
from app.schemas.booking import BookingCreate, BookingListResponse, BookingQuote, BookingStayRequest, InventoryHoldCreate, NightlyPrice
from app.services import audit_service, booking_gateway_service, inventory_service, notification_service


MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def quote(db: Session, data: BookingStayRequest) -> BookingQuote:
    hotel = repository.get_hotel(db, data.hotel_id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    if hotel.status != HotelStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hotel is not available for booking")
    gateway = booking_gateway_service.state(db, hotel)
    if gateway.effective_status == BookingGatewayStatus.PAUSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This hotel is not accepting new bookings")

    room = repository.get_room_type(db, data.room_type_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room type not found")
    if room.hotel_id != hotel.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Room type does not belong to the selected hotel")
    if not room.is_customer_bookable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type is not approved for booking")
    if data.adults > room.max_adults * data.rooms or data.children > room.max_children * data.rooms or data.adults + data.children > room.max_guests * data.rooms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Guest count exceeds room capacity")

    nights = (data.check_out - data.check_in).days
    stay_dates = [data.check_in + timedelta(days=index) for index in range(nights)]
    # Refresh expired holds and commitment counters before publishing a quote.
    rows = inventory_service.list_partner_inventory(db, room, stay_dates[0], stay_dates[-1])
    by_date = {row.inventory_date: row for row in rows}
    if any(day not in by_date for day in stay_dates):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory is unavailable for one or more stay dates")
    ordered = [by_date[day] for day in stay_dates]
    if any(row.is_closed or row.available_inventory < data.rooms for row in ordered):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested rooms are unavailable for one or more stay dates")

    nightly = [NightlyPrice(date=row.inventory_date, unit_price=_money(row.price), rooms=data.rooms, amount=_money(row.price * data.rooms)) for row in ordered]
    subtotal = _money(sum((item.amount for item in nightly), Decimal("0.00")))
    taxes = _money(subtotal * settings.BOOKING_TAX_RATE)
    platform_fee = _money(settings.BOOKING_PLATFORM_FEE)
    discount = Decimal("0.00")
    return BookingQuote(
        **data.model_dump(include=set(BookingStayRequest.model_fields)),
        nights=nights,
        currency=room.currency,
        nightly_prices=nightly,
        subtotal=subtotal,
        taxes=taxes,
        platform_fee=platform_fee,
        discount=discount,
        total_amount=_money(subtotal + taxes + platform_fee - discount),
        booking_mode=gateway.effective_status,
    )


def _new_reference(db: Session) -> str:
    for _ in range(20):
        reference = f"TRV-HOT-{date.today().year}-{secrets.randbelow(1_000_000):06d}"
        if not repository.reference_exists(db, reference):
            return reference
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not allocate a booking reference")


def _same_request(booking: Booking, data: BookingCreate) -> bool:
    return all(
        (
            booking.hotel_id == data.hotel_id,
            booking.room_type_id == data.room_type_id,
            booking.check_in == data.check_in,
            booking.check_out == data.check_out,
            booking.rooms == data.rooms,
            booking.adults == data.adults,
            booking.children == data.children,
        )
    )


def create_inventory_hold(db: Session, current_user: User, data: InventoryHoldCreate):
    """Reserve inventory briefly before a future booking flow consumes it."""
    if current_user.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customer accounts can create booking holds")
    hotel = repository.get_hotel(db, data.hotel_id)
    room = repository.get_room_type(db, data.room_type_id)
    if hotel is None or room is None or room.hotel_id != data.hotel_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel or room type not found")
    if hotel.status != HotelStatus.ACTIVE or not room.is_customer_bookable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type is not approved for booking")
    gateway = booking_gateway_service.state(db, hotel)
    if gateway.effective_status == BookingGatewayStatus.PAUSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This hotel is not accepting new bookings")
    if data.adults > room.max_adults * data.rooms or data.children > room.max_children * data.rooms or data.adults + data.children > room.max_guests * data.rooms:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Guest count exceeds room capacity")
    return inventory_service.create_hold(
        db,
        room=room,
        user_id=current_user.id,
        check_in=data.check_in,
        check_out=data.check_out,
        rooms=data.rooms,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.INVENTORY_HOLD_MINUTES),
    )


def create_booking(db: Session, current_user: User, data: BookingCreate) -> Booking:
    if current_user.role not in (UserRole.CUSTOMER, UserRole.USER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only customer accounts can create bookings")
    if data.idempotency_key:
        existing = repository.get_by_idempotency_key(db, current_user.id, data.idempotency_key)
        if existing:
            if not _same_request(existing, data):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was already used for a different booking")
            return existing

    pricing = quote(db, data)
    hotel = repository.get_hotel(db, data.hotel_id)
    room = repository.get_room_type(db, data.room_type_id)
    if hotel is None or room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel or room type not found")
    if not room.is_customer_bookable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type is not approved for booking")
    # Keep the hold active through checkout.  It is converted to a confirmed
    # commitment only after the gateway verifies payment.
    hold = inventory_service.validate_hold(db, hold_token=data.hold_token, user_id=current_user.id, room=room, check_in=data.check_in, check_out=data.check_out, rooms=data.rooms)
    booking_status = BookingStatus.PAYMENT_PENDING if pricing.booking_mode == BookingGatewayStatus.ACTIVE else BookingStatus.PENDING
    now = datetime.now(timezone.utc)
    request_expires_at = now + timedelta(hours=settings.BOOKING_REQUEST_TTL_HOURS) if booking_status == BookingStatus.PENDING else None
    if request_expires_at is not None:
        hold = inventory_service.extend_hold(
            db,
            hold_token=hold.hold_token,
            user_id=current_user.id,
            room=room,
            check_in=data.check_in,
            check_out=data.check_out,
            rooms=data.rooms,
            expires_at=request_expires_at,
        )
    room_snapshot = {"name": room.name, "description": room.description, "bed_type": room.bed_type, "bed_count": room.bed_count, "max_adults": room.max_adults, "max_children": room.max_children, "max_guests": room.max_guests}
    price_snapshot = {"currency": pricing.currency, "nightly_prices": [item.model_dump(mode="json") for item in pricing.nightly_prices], "subtotal": str(pricing.subtotal), "taxes": str(pricing.taxes), "platform_fee": str(pricing.platform_fee), "discount": str(pricing.discount), "total_amount": str(pricing.total_amount)}
    policy = hotel.policy
    policy_snapshot = {"cancellation_policy": policy.cancellation_policy if policy else None, "children_policy": policy.children_policy if policy else None, "pet_policy": policy.pet_policy if policy else None, "smoking_policy": policy.smoking_policy if policy else None, "extra_bed_policy": policy.extra_bed_policy if policy else None, "additional_rules": policy.additional_rules if policy else None}
    booking = Booking(
        booking_reference=_new_reference(db), idempotency_key=data.idempotency_key, user_id=current_user.id,
        hotel_id=data.hotel_id, room_type_id=data.room_type_id, check_in=data.check_in, check_out=data.check_out,
        rooms=data.rooms, adults=data.adults, children=data.children, nights=pricing.nights, currency=pricing.currency,
        subtotal=pricing.subtotal, taxes=pricing.taxes, platform_fee=pricing.platform_fee, discount=pricing.discount,
        total_amount=pricing.total_amount, hold_token=hold.hold_token, room_snapshot=room_snapshot, price_snapshot=price_snapshot, policy_snapshot=policy_snapshot,
        booking_mode=pricing.booking_mode, request_expires_at=request_expires_at, status=booking_status, payment_status=PaymentStatus.NOT_STARTED,
    )
    booking.travellers = [BookingTraveller(**traveller.model_dump()) for traveller in data.travellers]
    note = "Booking request created; awaiting hotel review" if booking_status == BookingStatus.PENDING else "Booking created; awaiting payment"
    booking.status_history = [BookingStatusHistory(old_status=None, new_status=booking_status, changed_by_user_id=current_user.id, note=note)]
    db.add(booking)
    try:
        db.flush()
        if booking_status == BookingStatus.PENDING and hotel.partner_id:
            notification_service.create(
                db,
                recipient_user_id=hotel.partner_id,
                event_type=NotificationEventType.BOOKING_REQUEST_CREATED,
                dedupe_key=f"booking-request-created:{booking.id}",
                title="New booking request",
                body=f"Booking request {booking.booking_reference} is awaiting your decision.",
                data={"booking_id": booking.id, "booking_reference": booking.booking_reference, "hotel_id": booking.hotel_id},
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if data.idempotency_key:
            existing = repository.get_by_idempotency_key(db, current_user.id, data.idempotency_key)
            if existing and _same_request(existing, data):
                return existing
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was already used for a different booking") from exc
        raise
    return repository.get_booking(db, booking.id)  # type: ignore[return-value]


def get_booking(db: Session, current_user: User, booking_id: int) -> Booking:
    booking = repository.get_booking(db, booking_id)
    if booking is None or (current_user.role != UserRole.ADMIN and booking.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def list_my_bookings(db: Session, current_user: User) -> BookingListResponse:
    items = repository.list_user_bookings(db, current_user.id)
    return BookingListResponse(items=items, total=len(items))


def list_all_bookings(db: Session) -> BookingListResponse:
    items = repository.list_bookings(db)
    return BookingListResponse(items=items, total=len(items))


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _locked_partner_request(db: Session, partner: User, booking_id: int) -> Booking:
    booking = db.scalar(
        select(Booking)
        .join(Hotel, Hotel.id == Booking.hotel_id)
        .where(Booking.id == booking_id, Hotel.partner_id == partner.id, Booking.booking_mode == BookingGatewayStatus.BOOKING_ON_REQUEST)
        .with_for_update()
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking request not found")
    return booking


def _expire_request(db: Session, booking: Booking, *, now: datetime, note: str) -> None:
    if booking.hold_token:
        inventory_service.release_hold(db, hold_token=booking.hold_token, final_status=InventoryHoldStatus.EXPIRED)
    old_status = booking.status
    booking.status = BookingStatus.REQUEST_EXPIRED
    booking.request_decision_reason = note
    if booking.request_decided_at is None:
        booking.request_decided_at = now
    booking.status_history.append(BookingStatusHistory(old_status=old_status, new_status=booking.status, changed_by_user_id=None, note=note))
    notification_service.create(
        db,
        recipient_user_id=booking.user_id,
        event_type=NotificationEventType.BOOKING_REQUEST_EXPIRED,
        dedupe_key=f"booking-request-expired:{booking.id}",
        title="Booking request expired",
        body=f"Booking request {booking.booking_reference} expired and its room capacity was released.",
        data={"booking_id": booking.id, "booking_reference": booking.booking_reference, "hotel_id": booking.hotel_id},
    )


def list_partner_requests(db: Session, partner: User) -> BookingListResponse:
    items = list(db.scalars(
        select(Booking)
        .join(Hotel, Hotel.id == Booking.hotel_id)
        .where(Hotel.partner_id == partner.id, Booking.booking_mode == BookingGatewayStatus.BOOKING_ON_REQUEST)
        .options(*repository.BOOKING_LOADS)
        .order_by(Booking.created_at.desc())
    ))
    return BookingListResponse(items=items, total=len(items))


def list_partner_bookings(db: Session, partner: User) -> BookingListResponse:
    """List the authenticated hotel's complete booking history without crossing tenants."""
    items = list(db.scalars(
        select(Booking)
        .join(Hotel, Hotel.id == Booking.hotel_id)
        .where(Hotel.partner_id == partner.id)
        .options(*repository.BOOKING_LOADS)
        .order_by(Booking.created_at.desc())
    ))
    return BookingListResponse(items=items, total=len(items))


def accept_request(db: Session, partner: User, booking_id: int) -> Booking:
    booking = _locked_partner_request(db, partner, booking_id)
    now = datetime.now(timezone.utc)
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking request is no longer actionable")
    if (_aware(booking.request_expires_at) or now) <= now:
        _expire_request(db, booking, now=now, note="Hotel response deadline expired")
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking request has expired")
    room = repository.get_room_type(db, booking.room_type_id)
    if room is None or not room.is_customer_bookable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room type is no longer approved for booking")
    payment_expires_at = now + timedelta(minutes=settings.PAYMENT_ORDER_TTL_MINUTES)
    if not booking.hold_token:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking request has no reserved inventory")
    inventory_service.extend_hold(
        db,
        hold_token=booking.hold_token,
        user_id=booking.user_id,
        room=room,
        check_in=booking.check_in,
        check_out=booking.check_out,
        rooms=booking.rooms,
        expires_at=payment_expires_at,
    )
    old_status = booking.status
    booking.status = BookingStatus.PAYMENT_PENDING
    booking.request_decided_at = now
    booking.request_decision_reason = "Accepted by hotel"
    booking.payment_expires_at = payment_expires_at
    booking.status_history.append(BookingStatusHistory(old_status=old_status, new_status=booking.status, changed_by_user_id=partner.id, note="Hotel accepted booking request; customer payment required"))
    audit_service.record(db, actor=partner, action="BOOKING_REQUEST_ACCEPTED", target_type="BOOKING", target_id=booking.id, reason="Hotel accepted booking request", previous_value={"status": old_status.value}, new_value={"status": booking.status.value, "payment_expires_at": payment_expires_at.isoformat()})
    notification_service.create(db, recipient_user_id=booking.user_id, event_type=NotificationEventType.BOOKING_REQUEST_ACCEPTED, dedupe_key=f"booking-request-accepted:{booking.id}", title="Booking request accepted", body=f"The hotel accepted {booking.booking_reference}.", data={"booking_id": booking.id, "booking_reference": booking.booking_reference, "hotel_id": booking.hotel_id})
    notification_service.create(db, recipient_user_id=booking.user_id, event_type=NotificationEventType.PAYMENT_REQUIRED, dedupe_key=f"booking-request-payment:{booking.id}", title="Payment required", body=f"Complete payment for {booking.booking_reference} before the payment window expires.", data={"booking_id": booking.id, "booking_reference": booking.booking_reference, "hotel_id": booking.hotel_id})
    db.commit()
    return repository.get_booking(db, booking.id)  # type: ignore[return-value]


def reject_request(db: Session, partner: User, booking_id: int, reason: str) -> Booking:
    booking = _locked_partner_request(db, partner, booking_id)
    now = datetime.now(timezone.utc)
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking request is no longer actionable")
    if (_aware(booking.request_expires_at) or now) <= now:
        _expire_request(db, booking, now=now, note="Hotel response deadline expired")
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking request has expired")
    if booking.hold_token:
        inventory_service.release_hold(db, hold_token=booking.hold_token, final_status=InventoryHoldStatus.CANCELLED)
    old_status = booking.status
    booking.status = BookingStatus.REQUEST_REJECTED
    booking.request_decided_at = now
    booking.request_decision_reason = reason.strip()
    booking.status_history.append(BookingStatusHistory(old_status=old_status, new_status=booking.status, changed_by_user_id=partner.id, note=f"Hotel rejected booking request: {reason.strip()}"))
    audit_service.record(db, actor=partner, action="BOOKING_REQUEST_REJECTED", target_type="BOOKING", target_id=booking.id, reason=reason, previous_value={"status": old_status.value}, new_value={"status": booking.status.value})
    notification_service.create(db, recipient_user_id=booking.user_id, event_type=NotificationEventType.BOOKING_REQUEST_REJECTED, dedupe_key=f"booking-request-rejected:{booking.id}", title="Booking request declined", body=f"The hotel declined {booking.booking_reference}: {reason.strip()}", data={"booking_id": booking.id, "booking_reference": booking.booking_reference, "hotel_id": booking.hotel_id})
    db.commit()
    return repository.get_booking(db, booking.id)  # type: ignore[return-value]


def expire_booking_requests(db: Session, *, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    items = list(db.scalars(
        select(Booking)
        .where(
            Booking.booking_mode == BookingGatewayStatus.BOOKING_ON_REQUEST,
            or_(
                (Booking.status == BookingStatus.PENDING) & (Booking.request_expires_at <= current),
                (Booking.status == BookingStatus.PAYMENT_PENDING) & (Booking.payment_expires_at <= current),
            ),
        )
        .options(selectinload(Booking.payments), selectinload(Booking.status_history))
        .with_for_update()
    ))
    changed = 0
    for booking in items:
        if any(payment.status == PaymentStatus.PAID for payment in booking.payments):
            continue
        note = "Hotel response deadline expired" if booking.status == BookingStatus.PENDING else "Customer payment window expired"
        _expire_request(db, booking, now=current, note=note)
        changed += 1
    return changed
