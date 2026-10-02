from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.models.hotel import BookingGatewayStatus, PropertyType


class PublicHotelSort(str, Enum):
    RECOMMENDED = "recommended"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    RATING = "rating"


class PublicAmenity(BaseModel):
    id: int
    name: str
    slug: str
    icon: str | None
    category: str | None


class PublicImage(BaseModel):
    id: int
    image_url: str
    alt_text: str | None
    is_cover: bool
    display_order: int


class PublicPolicy(BaseModel):
    cancellation_policy: str | None
    children_policy: str | None
    pet_policy: str | None
    smoking_policy: str | None
    extra_bed_policy: str | None
    additional_rules: str | None


class PublicHotelSummary(BaseModel):
    id: int
    name: str
    slug: str
    property_type: PropertyType
    star_rating: Decimal
    city: str
    district: str | None = None
    district_slug: str | None = None
    destination_slug: str | None = None
    state: str
    country: str
    is_featured: bool
    cover_image_url: str | None
    amenities: list[PublicAmenity]
    starting_price: Decimal | None
    currency: str | None
    is_available: bool
    booking_mode: BookingGatewayStatus
    booking_enabled: bool
    last_inventory_update: datetime | None


class PublicHotelSearchResponse(BaseModel):
    items: list[PublicHotelSummary]
    total: int


class PublicHotelDetail(PublicHotelSummary):
    description: str | None
    address_line1: str
    address_line2: str | None
    postal_code: str
    latitude: Decimal | None
    longitude: Decimal | None
    check_in_time: time
    check_out_time: time
    images: list[PublicImage]
    policy: PublicPolicy | None


class PublicNightlyPrice(BaseModel):
    inventory_date: date
    price: Decimal


class PublicRoomAvailability(BaseModel):
    id: int
    hotel_id: int
    name: str
    description: str | None
    max_adults: int
    max_children: int
    max_guests: int
    bed_type: str
    bed_count: int
    room_size_sqm: Decimal | None
    currency: str
    images: list[PublicImage]
    available_rooms: int = Field(ge=1)
    nights: int = Field(ge=1)
    price_per_night: Decimal = Field(ge=0)
    estimated_total: Decimal = Field(ge=0)
    nightly_prices: list[PublicNightlyPrice]


class PublicRoomAvailabilityResponse(BaseModel):
    hotel_id: int
    check_in: date
    check_out: date
    adults: int
    children: int
    rooms: int
    booking_mode: BookingGatewayStatus
    booking_enabled: bool
    last_inventory_update: datetime | None
    items: list[PublicRoomAvailability]
