import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.hotel import BookingGatewayStatus, HotelStatus, PropertyType, RoomTypeStatus


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def validate_slug(value: str) -> str:
    normalized = value.strip().lower()
    if not SLUG_PATTERN.fullmatch(normalized):
        raise ValueError("slug must contain lowercase letters, numbers, and single hyphens only")
    return normalized


def validate_url(value: str) -> str:
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("image_url must be a valid HTTP or HTTPS URL")
    return normalized


class HotelBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    property_type: PropertyType
    star_rating: Decimal = Field(default=Decimal("0.0"), ge=0, le=5, decimal_places=1)
    address_line1: str = Field(min_length=2, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str = Field(default="Maharashtra", min_length=2, max_length=100)
    country: str = Field(default="India", min_length=2, max_length=100)
    postal_code: str = Field(min_length=2, max_length=20)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=7)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=7)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    check_in_time: time
    check_out_time: time
    is_featured: bool = False
    booking_gateway_status: BookingGatewayStatus = Field(default=BookingGatewayStatus.ACTIVE)

    @field_validator("name", "address_line1", "city", "state", "country")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("field must contain at least 2 characters")
        return normalized

    @field_validator("district")
    @classmethod
    def normalize_district(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized if normalized else None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return validate_slug(value)

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"[\s()-]", "", value)
        if not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("contact_phone must use E.164 format")
        return normalized


class HotelCreate(HotelBase):
    pass


class HotelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    slug: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    property_type: PropertyType | None = None
    star_rating: Decimal | None = Field(default=None, ge=0, le=5, decimal_places=1)
    address_line1: str | None = Field(default=None, min_length=2, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    postal_code: str | None = Field(default=None, min_length=2, max_length=20)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=7)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=7)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    check_in_time: time | None = None
    check_out_time: time | None = None
    is_featured: bool | None = None
    booking_gateway_status: BookingGatewayStatus | None = None

    @field_validator("name", "address_line1", "city", "state", "country")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("field must contain at least 2 characters")
        return normalized

    @field_validator("district")
    @classmethod
    def normalize_district(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized if normalized else None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        return validate_slug(value) if value is not None else None

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"[\s()-]", "", value)
        if not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("contact_phone must use E.164 format")
        return normalized


class HotelStatusUpdate(BaseModel):
    status: HotelStatus
    reason: str = Field(min_length=5, max_length=1000)


class HotelBookingGatewayUpdate(BaseModel):
    booking_gateway_status: BookingGatewayStatus
    reason: str | None = Field(default=None, max_length=2000)


class BookingGatewayOverrideUpdate(BaseModel):
    booking_gateway_status: BookingGatewayStatus
    reason: str = Field(min_length=5, max_length=2000)


class BookingGatewayStateResponse(BaseModel):
    hotel_id: int
    partner_requested_status: BookingGatewayStatus
    effective_status: BookingGatewayStatus
    override_status: BookingGatewayStatus | None
    override_reason: str | None
    overridden_at: datetime | None
    inventory_last_updated_at: datetime | None
    inventory_is_fresh: bool
    inventory_freshness_reason: str | None
    verified: bool


class HotelImageCreate(BaseModel):
    image_url: str = Field(max_length=2048)
    alt_text: str | None = Field(default=None, max_length=255)
    is_cover: bool = False
    display_order: int = Field(default=0, ge=0)

    @field_validator("image_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        return validate_url(value)


class HotelImageResponse(OrmModel):
    id: int
    hotel_id: int
    image_url: str
    storage_key: str | None
    content_type: str | None
    file_size: int | None
    alt_text: str | None
    is_cover: bool
    display_order: int
    created_at: datetime


class HotelImageOrderUpdate(BaseModel):
    image_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("image_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if any(item < 1 for item in value) or len(set(value)) != len(value):
            raise ValueError("image_ids must contain unique positive IDs")
        return value


class PartnerHotelProfileUpdate(BaseModel):
    """Fields a hotel partner may manage on their own property."""
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=10000)
    property_type: PropertyType | None = None
    address_line1: str | None = Field(default=None, min_length=2, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    postal_code: str | None = Field(default=None, min_length=2, max_length=20)
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    check_in_time: time | None = None
    check_out_time: time | None = None

    @field_validator("state")
    @classmethod
    def validate_maharashtra(cls, value: str | None) -> str | None:
        if value is not None and value.strip().casefold() != "maharashtra":
            raise ValueError("Hotel partner properties must be located in Maharashtra")
        return "Maharashtra" if value is not None else None

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"[\s()-]", "", value)
        if not PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("contact_phone must use E.164 format")
        return normalized


class AmenityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120)
    icon: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return validate_slug(value)


class AmenityResponse(OrmModel):
    id: int
    name: str
    slug: str
    icon: str | None
    category: str | None
    is_active: bool


class AmenityAssignment(BaseModel):
    amenity_ids: list[int] = Field(default_factory=list, max_length=200)

    @field_validator("amenity_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if any(item < 1 for item in value):
            raise ValueError("amenity IDs must be positive")
        return list(dict.fromkeys(value))


class HotelPolicyBase(BaseModel):
    cancellation_policy: str | None = Field(default=None, max_length=5000)
    children_policy: str | None = Field(default=None, max_length=5000)
    pet_policy: str | None = Field(default=None, max_length=5000)
    smoking_policy: str | None = Field(default=None, max_length=5000)
    extra_bed_policy: str | None = Field(default=None, max_length=5000)
    additional_rules: str | None = Field(default=None, max_length=5000)


class HotelPolicyCreate(HotelPolicyBase):
    pass


class HotelPolicyUpdate(HotelPolicyBase):
    pass


class HotelPolicyResponse(HotelPolicyBase, OrmModel):
    id: int
    hotel_id: int
    created_at: datetime
    updated_at: datetime


class RoomTypeBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    max_adults: int = Field(default=2, ge=1)
    max_children: int = Field(default=0, ge=0)
    max_guests: int = Field(default=2, ge=1)
    bed_type: str = Field(min_length=2, max_length=100)
    bed_count: int = Field(default=1, ge=1)
    room_size_sqm: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    base_price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    total_rooms: int = Field(ge=0)
    is_active: bool = True

    @field_validator("name", "bed_type")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("currency must be a three-letter code")
        return normalized

    @model_validator(mode="after")
    def validate_capacity(self) -> Self:
        if self.max_guests > self.max_adults + self.max_children:
            raise ValueError("max_guests cannot exceed max_adults plus max_children")
        return self


class RoomTypeCreate(RoomTypeBase):
    pass


class RoomTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    max_adults: int | None = Field(default=None, ge=1)
    max_children: int | None = Field(default=None, ge=0)
    max_guests: int | None = Field(default=None, ge=1)
    bed_type: str | None = Field(default=None, min_length=2, max_length=100)
    bed_count: int | None = Field(default=None, ge=1)
    room_size_sqm: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    base_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    total_rooms: int | None = Field(default=None, ge=0)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("currency must be a three-letter code")
        return normalized


class RoomStatusUpdate(BaseModel):
    is_active: bool


class RoomImageCreate(BaseModel):
    image_url: str = Field(max_length=2048)
    alt_text: str | None = Field(default=None, max_length=255)
    is_cover: bool = False
    display_order: int = Field(default=0, ge=0)

    @field_validator("image_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        return validate_url(value)


class RoomImageResponse(OrmModel):
    id: int
    room_type_id: int
    image_url: str
    alt_text: str | None
    is_cover: bool
    display_order: int
    created_at: datetime


class RoomTypeResponse(OrmModel):
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
    base_price: Decimal
    currency: str
    total_rooms: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[RoomImageResponse] = Field(default_factory=list)


class MealAddOnOption(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class PartnerRoomTypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=10000)
    max_adults: int = Field(ge=1, le=20)
    max_children: int = Field(default=0, ge=0, le=20)
    max_guests: int = Field(ge=1, le=20)
    bed_type: str = Field(min_length=2, max_length=100)
    bed_count: int = Field(default=1, ge=1, le=10)
    room_size_sqm: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    base_price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    total_rooms: int = Field(default=0, ge=0)
    extra_bed_rules: str | None = Field(default=None, max_length=5000)
    meal_add_on_options: list[MealAddOnOption] = Field(default_factory=list, max_length=20)
    amenity_ids: list[int] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_capacity(self) -> Self:
        if self.max_guests > self.max_adults + self.max_children:
            raise ValueError("max_guests cannot exceed max_adults plus max_children")
        return self


class PartnerRoomTypeUpdate(PartnerRoomTypeCreate):
    pass


class RoomTypeReviewRequest(BaseModel):
    action: RoomTypeStatus
    review_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("action")
    @classmethod
    def admin_actions_only(cls, value: RoomTypeStatus) -> RoomTypeStatus:
        if value not in {RoomTypeStatus.APPROVED, RoomTypeStatus.NEEDS_CHANGES, RoomTypeStatus.BOOKABLE}:
            raise ValueError("Review action must be APPROVED, NEEDS_CHANGES, or BOOKABLE")
        return value


class PartnerRoomTypeResponse(RoomTypeResponse):
    status: RoomTypeStatus
    extra_bed_rules: str | None
    meal_add_on_options: list[MealAddOnOption] = Field(default_factory=list)
    review_notes: str | None
    reviewed_at: datetime | None
    version: int
    amenities: list[AmenityResponse] = Field(default_factory=list)


class RoomInventoryCreate(BaseModel):
    inventory_date: date
    total_inventory: int = Field(ge=0)
    # Accepted only as a legacy compatibility hint. The inventory service
    # always derives the persisted value from capacity and commitments.
    available_inventory: int | None = Field(default=None, ge=0)
    blocked_inventory: int = Field(default=0, ge=0)
    price: Decimal = Field(ge=0, decimal_places=2)
    is_closed: bool = False

    @model_validator(mode="after")
    def validate_allocations(self) -> Self:
        if self.available_inventory is not None and self.available_inventory + self.blocked_inventory > self.total_inventory:
            raise ValueError("available plus blocked inventory cannot exceed total inventory")
        return self


class RoomInventoryUpdate(BaseModel):
    total_inventory: int | None = Field(default=None, ge=0)
    available_inventory: int | None = Field(default=None, ge=0)
    blocked_inventory: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    is_closed: bool | None = None

    @model_validator(mode="after")
    def validate_present_allocations(self) -> Self:
        if (
            self.total_inventory is not None
            and self.available_inventory is not None
            and self.blocked_inventory is not None
            and self.available_inventory + self.blocked_inventory > self.total_inventory
        ):
            raise ValueError("available plus blocked inventory cannot exceed total inventory")
        return self


class RoomInventoryResponse(OrmModel):
    id: int
    room_type_id: int
    inventory_date: date
    total_inventory: int
    available_inventory: int
    blocked_inventory: int
    confirmed_inventory: int
    held_inventory: int
    price: Decimal
    is_closed: bool
    created_at: datetime
    updated_at: datetime


class PartnerInventoryRangeUpdate(BaseModel):
    """Apply the same operational settings to each future date in an inclusive range."""

    start_date: date
    end_date: date
    total_inventory: int | None = Field(default=None, ge=0)
    blocked_inventory: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    is_closed: bool | None = None

    @model_validator(mode="after")
    def validate_range_and_changes(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        if all(value is None for value in (self.total_inventory, self.blocked_inventory, self.price, self.is_closed)):
            raise ValueError("provide at least one inventory setting")
        return self


class PartnerInventoryRangeResponse(OrmModel):
    items: list[RoomInventoryResponse]
    last_inventory_update: datetime | None


class HotelResponse(OrmModel):
    id: int
    name: str
    slug: str
    description: str | None
    property_type: PropertyType
    star_rating: Decimal
    status: HotelStatus
    booking_gateway_status: BookingGatewayStatus
    profile_completion_percent: int
    is_profile_complete: bool
    address_line1: str
    address_line2: str | None
    city: str
    district: str | None
    state: str
    country: str
    postal_code: str
    latitude: Decimal | None
    longitude: Decimal | None
    contact_email: EmailStr | None
    contact_phone: str | None
    check_in_time: time
    check_out_time: time
    is_featured: bool
    partner_id: int | None = None
    created_at: datetime
    updated_at: datetime


class HotelDetailResponse(HotelResponse):
    images: list[HotelImageResponse] = Field(default_factory=list)
    amenities: list[AmenityResponse] = Field(default_factory=list)
    policy: HotelPolicyResponse | None = None
    room_types: list[RoomTypeResponse] = Field(default_factory=list)


class PartnerHotelProfileResponse(HotelResponse):
    images: list[HotelImageResponse] = Field(default_factory=list)
    amenities: list[AmenityResponse] = Field(default_factory=list)
    verification_status: str | None = None
