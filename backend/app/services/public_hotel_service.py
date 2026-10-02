from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.hotel import BookingGatewayStatus, Hotel, PropertyType, RoomType
from app.repositories import hotel_repository as repository
from app.services import booking_gateway_service, destination_service, inventory_service
from app.schemas.public_hotel import (
    PublicAmenity,
    PublicHotelDetail,
    PublicHotelSearchResponse,
    PublicHotelSort,
    PublicHotelSummary,
    PublicImage,
    PublicNightlyPrice,
    PublicPolicy,
    PublicRoomAvailability,
    PublicRoomAvailabilityResponse,
)


MONEY = Decimal("0.01")


def _validate_dates(check_in: date | None, check_out: date | None) -> None:
    if (check_in is None) != (check_out is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="check_in and check_out must be provided together",
        )
    if check_in and check_out and check_out <= check_in:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="check_out must be after check_in",
        )


def _public_amenities(hotel: Hotel) -> list[PublicAmenity]:
    return [
        PublicAmenity(
            id=item.id,
            name=item.name,
            slug=item.slug,
            icon=item.icon,
            category=item.category,
        )
        for item in hotel.amenities
        if item.is_active
    ]


def _public_images(images: list[object]) -> list[PublicImage]:
    return [
        PublicImage(
            id=image.id,
            image_url=image.image_url,
            alt_text=image.alt_text,
            is_cover=image.is_cover,
            display_order=image.display_order,
        )
        for image in images
    ]


def _cover_image(hotel: Hotel) -> str | None:
    if not hotel.images:
        return None
    cover = next((image for image in hotel.images if image.is_cover), hotel.images[0])
    return cover.image_url


def _room_availability(
    db: Session,
    room: RoomType,
    *,
    check_in: date,
    check_out: date,
    adults: int,
    children: int,
    rooms: int,
) -> PublicRoomAvailability | None:
    if not room.is_customer_bookable:
        return None
    if adults > room.max_adults * rooms or children > room.max_children * rooms:
        return None
    if adults + children > room.max_guests * rooms:
        return None

    nights = (check_out - check_in).days
    last_night = check_out - timedelta(days=1)
    inventory = inventory_service.list_partner_inventory(db, room, check_in, last_night)
    by_date = {item.inventory_date: item for item in inventory}
    stay_dates = [check_in + timedelta(days=index) for index in range(nights)]
    if any(stay_date not in by_date for stay_date in stay_dates):
        return None

    rows = [by_date[stay_date] for stay_date in stay_dates]
    if any(row.is_closed or row.available_inventory < rooms for row in rows):
        return None

    available_rooms = min(row.available_inventory for row in rows)
    stay_price = sum((row.price for row in rows), start=Decimal("0.00"))
    average_price = (stay_price / nights).quantize(MONEY, rounding=ROUND_HALF_UP)
    return PublicRoomAvailability(
        id=room.id,
        hotel_id=room.hotel_id,
        name=room.name,
        description=room.description,
        max_adults=room.max_adults,
        max_children=room.max_children,
        max_guests=room.max_guests,
        bed_type=room.bed_type,
        bed_count=room.bed_count,
        room_size_sqm=room.room_size_sqm,
        currency=room.currency,
        images=_public_images(room.images),
        available_rooms=available_rooms,
        nights=nights,
        price_per_night=average_price,
        estimated_total=(stay_price * rooms).quantize(MONEY, rounding=ROUND_HALF_UP),
        nightly_prices=[
            PublicNightlyPrice(inventory_date=row.inventory_date, price=row.price)
            for row in rows
        ],
    )


def _summary(
    hotel: Hotel,
    *,
    starting_price: Decimal | None,
    currency: str | None,
    is_available: bool,
    booking_mode: BookingGatewayStatus,
    last_inventory_update,
) -> PublicHotelSummary:
    return PublicHotelSummary(
        id=hotel.id,
        name=hotel.name,
        slug=hotel.slug,
        property_type=hotel.property_type,
        star_rating=hotel.star_rating,
        city=hotel.city,
        district=hotel.district,
        district_slug=hotel.district_ref.slug if hotel.district_ref else None,
        destination_slug=hotel.destination_ref.slug if hotel.destination_ref else None,
        state=hotel.state,
        country=hotel.country,
        is_featured=hotel.is_featured,
        cover_image_url=_cover_image(hotel),
        amenities=_public_amenities(hotel),
        starting_price=starting_price,
        currency=currency,
        is_available=is_available,
        booking_mode=booking_mode,
        booking_enabled=booking_mode == BookingGatewayStatus.ACTIVE,
        last_inventory_update=last_inventory_update,
    )


def search_hotels(
    db: Session,
    *,
    city: str | None,
    district: str | None = None,
    destination: str | None = None,
    check_in: date | None,
    check_out: date | None,
    adults: int,
    children: int,
    rooms: int,
    min_price: Decimal | None,
    max_price: Decimal | None,
    star_rating: int | None,
    property_type: PropertyType | None,
    amenities: list[str],
    sort: PublicHotelSort,
) -> PublicHotelSearchResponse:
    _validate_dates(check_in, check_out)
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_price cannot exceed max_price",
        )

    required_amenities = {slug.strip().lower() for slug in amenities if slug.strip()}
    results: list[PublicHotelSummary] = []
    location_filter = destination_service.resolve_hotel_location(db, destination) if destination else None
    for hotel in repository.list_public_hotels(
        db,
        city=city,
        district=district,
        location_filter=location_filter,
        property_type=property_type,
        star_rating=star_rating,
    ):
        gateway = booking_gateway_service.state(db, hotel)
        hotel_amenities = {item.slug.lower() for item in hotel.amenities if item.is_active}
        if not required_amenities.issubset(hotel_amenities):
            continue

        if check_in and check_out and gateway.effective_status != BookingGatewayStatus.PAUSED:
            available_rooms = [
                available
                for room in hotel.room_types
                if (
                    available := _room_availability(
                        db,
                        room,
                        check_in=check_in,
                        check_out=check_out,
                        adults=adults,
                        children=children,
                        rooms=rooms,
                    )
                )
                is not None
            ]
            if not available_rooms:
                continue
            cheapest = min(available_rooms, key=lambda item: item.price_per_night)
            starting_price = cheapest.price_per_night
            currency = cheapest.currency
            is_available = True
        else:
            active_rooms = [room for room in hotel.room_types if room.is_customer_bookable]
            if active_rooms:
                cheapest_room = min(active_rooms, key=lambda item: item.base_price)
                starting_price = cheapest_room.base_price
                currency = cheapest_room.currency
                is_available = True
            else:
                starting_price = None
                currency = None
                is_available = False

        if gateway.effective_status == BookingGatewayStatus.PAUSED:
            is_available = False

        if min_price is not None and (starting_price is None or starting_price < min_price):
            continue
        if max_price is not None and (starting_price is None or starting_price > max_price):
            continue
        results.append(
            _summary(
                hotel,
                starting_price=starting_price,
                currency=currency,
                is_available=is_available,
                booking_mode=gateway.effective_status,
                last_inventory_update=gateway.inventory_last_updated_at,
            )
        )

    if sort == PublicHotelSort.PRICE_ASC:
        results.sort(key=lambda hotel: hotel.starting_price or Decimal("Infinity"))
    elif sort == PublicHotelSort.PRICE_DESC:
        results.sort(key=lambda hotel: hotel.starting_price or Decimal("-1"), reverse=True)
    elif sort == PublicHotelSort.RATING:
        results.sort(key=lambda hotel: hotel.star_rating, reverse=True)
    else:
        results.sort(key=lambda hotel: (not hotel.is_featured, -hotel.star_rating, hotel.name))
    return PublicHotelSearchResponse(items=results, total=len(results))


def resolve_hotel(db: Session, hotel_ref: int | str) -> Hotel:
    hotel = repository.get_public_hotel(db, hotel_ref)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel not found")
    return hotel


def get_hotel(db: Session, hotel_ref: int | str) -> PublicHotelDetail:
    hotel = resolve_hotel(db, hotel_ref)
    active_rooms = [room for room in hotel.room_types if room.is_customer_bookable]
    cheapest = min(active_rooms, key=lambda room: room.base_price) if active_rooms else None
    gateway = booking_gateway_service.state(db, hotel)
    summary = _summary(
        hotel,
        starting_price=cheapest.base_price if cheapest else None,
        currency=cheapest.currency if cheapest else None,
        is_available=bool(cheapest) and gateway.effective_status != BookingGatewayStatus.PAUSED,
        booking_mode=gateway.effective_status,
        last_inventory_update=gateway.inventory_last_updated_at,
    )
    return PublicHotelDetail(
        **summary.model_dump(),
        description=hotel.description,
        address_line1=hotel.address_line1,
        address_line2=hotel.address_line2,
        postal_code=hotel.postal_code,
        latitude=hotel.latitude,
        longitude=hotel.longitude,
        check_in_time=hotel.check_in_time,
        check_out_time=hotel.check_out_time,
        images=_public_images(hotel.images),
        policy=(
            PublicPolicy(
                cancellation_policy=hotel.policy.cancellation_policy,
                children_policy=hotel.policy.children_policy,
                pet_policy=hotel.policy.pet_policy,
                smoking_policy=hotel.policy.smoking_policy,
                extra_bed_policy=hotel.policy.extra_bed_policy,
                additional_rules=hotel.policy.additional_rules,
            )
            if hotel.policy
            else None
        ),
    )


def get_rooms(
    db: Session,
    hotel_ref: int | str,
    *,
    check_in: date,
    check_out: date,
    adults: int,
    children: int,
    rooms: int,
) -> PublicRoomAvailabilityResponse:
    _validate_dates(check_in, check_out)
    hotel = resolve_hotel(db, hotel_ref)
    gateway = booking_gateway_service.state(db, hotel)
    available = [
        result
        for room in hotel.room_types
        if (
            result := _room_availability(
                db,
                room,
                check_in=check_in,
                check_out=check_out,
                adults=adults,
                children=children,
                rooms=rooms,
            )
        )
        is not None
    ]
    available.sort(key=lambda room: room.price_per_night)
    return PublicRoomAvailabilityResponse(
        hotel_id=hotel.id,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        rooms=rooms,
        booking_mode=gateway.effective_status,
        booking_enabled=gateway.effective_status == BookingGatewayStatus.ACTIVE,
        last_inventory_update=gateway.inventory_last_updated_at,
        items=available,
    )
