from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HotelStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class BookingGatewayStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BOOKING_ON_REQUEST = "BOOKING_ON_REQUEST"
    PAUSED = "PAUSED"


class PropertyType(str, Enum):
    HOTEL = "HOTEL"
    RESORT = "RESORT"
    VILLA = "VILLA"
    APARTMENT = "APARTMENT"
    HOSTEL = "HOSTEL"
    HOMESTAY = "HOMESTAY"


class RoomTypeStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    NEEDS_CHANGES = "NEEDS_CHANGES"
    BOOKABLE = "BOOKABLE"


hotel_amenities = Table(
    "hotel_amenities",
    Base.metadata,
    Column("hotel_id", ForeignKey("hotels.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="RESTRICT"), primary_key=True),
)

room_amenities = Table(
    "room_amenities",
    Base.metadata,
    Column("room_type_id", ForeignKey("room_types.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="RESTRICT"), primary_key=True),
)


class Hotel(Base):
    __tablename__ = "hotels"
    __table_args__ = (
        CheckConstraint("star_rating >= 0 AND star_rating <= 5", name="ck_hotels_star_rating"),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_hotels_latitude"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_hotels_longitude"),
        Index("ix_hotels_location", "country", "state", "city", "district"),
        Index("ix_hotels_booking_gateway", "status", "booking_gateway_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    property_type: Mapped[PropertyType] = mapped_column(SqlEnum(PropertyType, name="property_type"), nullable=False)
    star_rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), nullable=False, default=Decimal("0.0"), server_default="0.0")
    status: Mapped[HotelStatus] = mapped_column(
        SqlEnum(HotelStatus, name="hotel_status", native_enum=False),
        nullable=False,
        default=HotelStatus.DRAFT,
        server_default=HotelStatus.DRAFT.value,
        index=True,
    )
    booking_gateway_status: Mapped[BookingGatewayStatus] = mapped_column(
        SqlEnum(BookingGatewayStatus, name="booking_gateway_status", native_enum=False),
        nullable=False,
        default=BookingGatewayStatus.ACTIVE,
        server_default=BookingGatewayStatus.ACTIVE.value,
        index=True,
    )
    partner_booking_gateway_status: Mapped[BookingGatewayStatus] = mapped_column(
        SqlEnum(BookingGatewayStatus, name="booking_gateway_status", native_enum=False),
        nullable=False, default=BookingGatewayStatus.PAUSED, server_default=BookingGatewayStatus.PAUSED.value,
    )
    gateway_override_status: Mapped[BookingGatewayStatus | None] = mapped_column(
        SqlEnum(BookingGatewayStatus, name="booking_gateway_status", native_enum=False), nullable=True
    )
    gateway_override_reason: Mapped[str | None] = mapped_column(Text)
    gateway_overridden_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    gateway_overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    profile_completion_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_profile_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="SET NULL"), nullable=True, index=True)
    destination_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id", ondelete="SET NULL"), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(16))
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    check_in_time: Mapped[time] = mapped_column(Time, nullable=False)
    check_out_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    partner: Mapped[User | None] = relationship("User", foreign_keys=[partner_id])
    verification: Mapped[HotelVerification | None] = relationship("HotelVerification", back_populates="hotel", uselist=False, cascade="all, delete-orphan")
    images: Mapped[list[HotelImage]] = relationship(back_populates="hotel", cascade="all, delete-orphan", order_by="HotelImage.display_order")
    amenities: Mapped[list[Amenity]] = relationship(secondary=hotel_amenities, back_populates="hotels")
    policy: Mapped[HotelPolicy | None] = relationship(back_populates="hotel", uselist=False, cascade="all, delete-orphan")
    room_types: Mapped[list[RoomType]] = relationship(back_populates="hotel")
    district_ref: Mapped[District | None] = relationship(back_populates="hotels", foreign_keys=[district_id])
    destination_ref: Mapped[Destination | None] = relationship(back_populates="hotels", foreign_keys=[destination_id])


class HotelImage(Base):
    __tablename__ = "hotel_images"
    __table_args__ = (CheckConstraint("display_order >= 0", name="ck_hotel_images_display_order"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(Integer)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    is_cover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    hotel: Mapped[Hotel] = relationship(back_populates="images")


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    icon: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    hotels: Mapped[list[Hotel]] = relationship(secondary=hotel_amenities, back_populates="amenities")


class HotelPolicy(Base):
    __tablename__ = "hotel_policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False, unique=True)
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    children_policy: Mapped[str | None] = mapped_column(Text)
    pet_policy: Mapped[str | None] = mapped_column(Text)
    smoking_policy: Mapped[str | None] = mapped_column(Text)
    extra_bed_policy: Mapped[str | None] = mapped_column(Text)
    additional_rules: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hotel: Mapped[Hotel] = relationship(back_populates="policy")


class RoomType(Base):
    __tablename__ = "room_types"
    __table_args__ = (
        CheckConstraint("max_adults >= 1", name="ck_room_types_max_adults"),
        CheckConstraint("max_children >= 0", name="ck_room_types_max_children"),
        CheckConstraint("max_guests >= 1", name="ck_room_types_max_guests"),
        CheckConstraint("bed_count >= 1", name="ck_room_types_bed_count"),
        CheckConstraint("room_size_sqm IS NULL OR room_size_sqm > 0", name="ck_room_types_size"),
        CheckConstraint("base_price >= 0", name="ck_room_types_base_price"),
        CheckConstraint("total_rooms >= 0", name="ck_room_types_total_rooms"),
        UniqueConstraint("hotel_id", "name", name="uq_room_types_hotel_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    max_adults: Mapped[int] = mapped_column(Integer, nullable=False)
    max_children: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    bed_type: Mapped[str] = mapped_column(String(100), nullable=False)
    bed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    room_size_sqm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR", server_default="INR")
    total_rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    status: Mapped[RoomTypeStatus] = mapped_column(SqlEnum(RoomTypeStatus, name="room_type_status", native_enum=False), nullable=False, default=RoomTypeStatus.DRAFT, server_default=RoomTypeStatus.DRAFT.value, index=True)
    extra_bed_rules: Mapped[str | None] = mapped_column(Text)
    meal_add_on_options: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    review_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hotel: Mapped[Hotel] = relationship(back_populates="room_types")
    images: Mapped[list[RoomImage]] = relationship(back_populates="room_type", cascade="all, delete-orphan", order_by="RoomImage.display_order")
    inventory: Mapped[list[RoomInventory]] = relationship(back_populates="room_type")
    inventory_holds: Mapped[list[InventoryHold]] = relationship(back_populates="room_type", cascade="all, delete-orphan")
    amenities: Mapped[list[Amenity]] = relationship(secondary=room_amenities)
    versions: Mapped[list[RoomTypeVersion]] = relationship(back_populates="room_type", cascade="all, delete-orphan")

    @property
    def is_customer_bookable(self) -> bool:
        """The authoritative customer-facing room eligibility rule."""
        return self.is_active and self.status == RoomTypeStatus.BOOKABLE


class RoomImage(Base):
    __tablename__ = "room_images"
    __table_args__ = (CheckConstraint("display_order >= 0", name="ck_room_images_display_order"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    is_cover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    room_type: Mapped[RoomType] = relationship(back_populates="images")


class RoomTypeVersion(Base):
    __tablename__ = "room_type_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    room_type: Mapped[RoomType] = relationship(back_populates="versions")


class RoomInventory(Base):
    __tablename__ = "room_inventory"
    __table_args__ = (
        UniqueConstraint("room_type_id", "inventory_date", name="uq_room_inventory_room_date"),
        CheckConstraint("total_inventory >= 0", name="ck_room_inventory_total"),
        CheckConstraint("available_inventory >= 0", name="ck_room_inventory_available"),
        CheckConstraint("blocked_inventory >= 0", name="ck_room_inventory_blocked"),
        CheckConstraint("available_inventory <= total_inventory", name="ck_room_inventory_available_total"),
        CheckConstraint("blocked_inventory <= total_inventory", name="ck_room_inventory_blocked_total"),
        CheckConstraint("available_inventory + blocked_inventory + confirmed_inventory + held_inventory <= total_inventory", name="ck_room_inventory_allocations"),
        CheckConstraint("price >= 0", name="ck_room_inventory_price"),
        Index("ix_room_inventory_room_date", "room_type_id", "inventory_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"), nullable=False)
    inventory_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_inventory: Mapped[int] = mapped_column(Integer, nullable=False)
    available_inventory: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked_inventory: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    confirmed_inventory: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    held_inventory: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    room_type: Mapped[RoomType] = relationship(back_populates="inventory")


class InventoryHoldStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"


class InventoryHold(Base):
    """A short-lived, inventory-backed reservation for a prospective booking."""

    __tablename__ = "inventory_holds"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_inventory_holds_stay_dates"),
        CheckConstraint("rooms >= 1", name="ck_inventory_holds_rooms"),
        Index("ix_inventory_holds_room_status_expiry", "room_type_id", "status", "expires_at"),
        Index("ix_inventory_holds_hotel_status", "hotel_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hold_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[InventoryHoldStatus] = mapped_column(SqlEnum(InventoryHoldStatus, name="inventory_hold_status", native_enum=False), nullable=False, default=InventoryHoldStatus.ACTIVE, server_default=InventoryHoldStatus.ACTIVE.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    hotel: Mapped[Hotel] = relationship("Hotel", foreign_keys=[hotel_id])
    room_type: Mapped[RoomType] = relationship(back_populates="inventory_holds")
