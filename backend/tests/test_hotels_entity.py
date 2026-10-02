import unittest
from datetime import time
from decimal import Decimal
from pydantic import ValidationError

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.models.hotel import (
    BookingGatewayStatus,
    Hotel,
    HotelStatus,
    PropertyType,
)
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.repositories import hotel_repository as repository
from app.services import admin_control_service, booking_gateway_service, hotel_service, public_hotel_service
from app.schemas.hotel import (
    HotelBookingGatewayUpdate,
    HotelCreate,
    HotelResponse,
    HotelStatusUpdate,
    HotelUpdate,
)
from app.schemas.public_hotel import PublicHotelSort


class TestHotelsEntityUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )
        self.db = self.SessionLocal()
        self.admin = User(
            full_name="Hotel Entity Admin",
            email="hotel-entity-admin@example.com",
            phone="+919876540001",
            password_hash="x",
            role=UserRole.ADMIN,
        )
        self.db.add(self.admin)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _sample_hotel_create_data(self, **overrides) -> HotelCreate:
        default_payload = {
            "name": "Sahyadri Heritage Resort",
            "slug": "sahyadri-heritage-resort",
            "description": "A serene eco-resort overlooking the Western Ghats in Mahabaleshwar.",
            "property_type": PropertyType.RESORT,
            "star_rating": Decimal("4.5"),
            "address_line1": "Tapola Road, Post Mahabaleshwar",
            "city": "Mahabaleshwar",
            "district": "Satara",
            "state": "Maharashtra",
            "country": "India",
            "postal_code": "412806",
            "latitude": Decimal("17.9237000"),
            "longitude": Decimal("73.6586000"),
            "contact_email": "reservations@sahyadriresort.com",
            "contact_phone": "+919876543210",
            "check_in_time": time(14, 0),
            "check_out_time": time(11, 0),
            "is_featured": True,
            "booking_gateway_status": BookingGatewayStatus.ACTIVE,
        }
        default_payload.update(overrides)
        return HotelCreate(**default_payload)

    def _approve(self, hotel: Hotel) -> None:
        self.db.add(
            HotelVerification(
                hotel_id=hotel.id,
                business_name=hotel.name,
                business_type=BusinessType.PROPRIETORSHIP,
                verification_status=VerificationStatus.APPROVED,
            )
        )
        self.db.commit()

    def _set_status(self, hotel: Hotel, new_status: HotelStatus) -> Hotel:
        return admin_control_service.update_hotel_status(
            self.db, self.admin, hotel.id, new_status, "Entity test governance transition"
        )

    def _set_gateway(self, hotel: Hotel, new_status: BookingGatewayStatus) -> Hotel:
        booking_gateway_service.set_override(
            self.db, hotel, self.admin, new_status, "Entity test gateway transition"
        )
        return hotel

    def test_hotel_creation_and_defaults(self) -> None:
        create_data = self._sample_hotel_create_data()
        hotel = hotel_service.create_hotel(self.db, create_data)

        self.assertIsNotNone(hotel.id)
        self.assertEqual(hotel.name, "Sahyadri Heritage Resort")
        self.assertEqual(hotel.slug, "sahyadri-heritage-resort")
        self.assertEqual(hotel.district, "Satara")
        self.assertEqual(hotel.state, "Maharashtra")
        self.assertEqual(hotel.country, "India")
        self.assertEqual(hotel.status, HotelStatus.DRAFT)
        self.assertEqual(hotel.booking_gateway_status, BookingGatewayStatus.ACTIVE)
        self.assertEqual(hotel.property_type, PropertyType.RESORT)
        self.assertEqual(hotel.star_rating, Decimal("4.5"))
        self.assertTrue(hotel.is_featured)

        # Check response serialization
        response = HotelResponse.model_validate(hotel)
        dumped = response.model_dump()
        self.assertEqual(dumped["name"], "Sahyadri Heritage Resort")
        self.assertEqual(dumped["district"], "Satara")
        self.assertEqual(dumped["booking_gateway_status"], BookingGatewayStatus.ACTIVE)

    def test_hotel_name_validation_whitespace_and_length(self) -> None:
        # Empty / Whitespace name should be rejected by validation
        with self.assertRaises(ValidationError):
            self._sample_hotel_create_data(name="   ", slug="empty-hotel")

        with self.assertRaises(ValidationError):
            self._sample_hotel_create_data(name="A", slug="too-short")

    def test_hotel_location_validation(self) -> None:
        # Latitude out of range
        with self.assertRaises(ValidationError):
            self._sample_hotel_create_data(latitude=Decimal("95.0000000"), slug="invalid-lat")

        # Longitude out of range
        with self.assertRaises(ValidationError):
            self._sample_hotel_create_data(longitude=Decimal("190.0000000"), slug="invalid-lng")

    def test_hotel_status_transitions(self) -> None:
        hotel = hotel_service.create_hotel(self.db, self._sample_hotel_create_data())
        self.assertEqual(hotel.status, HotelStatus.DRAFT)

        # Transition DRAFT -> PENDING -> ACTIVE -> INACTIVE -> SUSPENDED
        for new_status in [
            HotelStatus.PENDING,
            HotelStatus.ACTIVE,
            HotelStatus.INACTIVE,
            HotelStatus.SUSPENDED,
        ]:
            updated = self._set_status(hotel, new_status)
            self.assertEqual(updated.status, new_status)
            persisted = repository.get_hotel(self.db, hotel.id)
            self.assertEqual(persisted.status, new_status)

    def test_booking_gateway_status_transitions(self) -> None:
        hotel = hotel_service.create_hotel(self.db, self._sample_hotel_create_data())
        self.assertEqual(hotel.booking_gateway_status, BookingGatewayStatus.ACTIVE)

        # Pause gateway
        paused = self._set_gateway(hotel, BookingGatewayStatus.PAUSED)
        self.assertEqual(paused.booking_gateway_status, BookingGatewayStatus.PAUSED)

        # Reactivate gateway
        reactivated = self._set_gateway(hotel, BookingGatewayStatus.ACTIVE)
        self.assertEqual(reactivated.booking_gateway_status, BookingGatewayStatus.ACTIVE)

    def test_general_hotel_update_cannot_bypass_gateway_governance(self) -> None:
        hotel = hotel_service.create_hotel(self.db, self._sample_hotel_create_data())
        with self.assertRaises(HTTPException) as raised:
            hotel_service.update_hotel(
                self.db,
                hotel.id,
                HotelUpdate(booking_gateway_status=BookingGatewayStatus.PAUSED),
            )
        self.assertEqual(raised.exception.status_code, 422)

    def test_independence_of_hotel_status_and_booking_gateway_status(self) -> None:
        # Crucial Maharashtra Tourist Places Business Rule: Hotel Status != Booking Gateway Status
        hotel = hotel_service.create_hotel(self.db, self._sample_hotel_create_data())
        self._set_status(hotel, HotelStatus.ACTIVE)
        self.assertEqual(hotel.status, HotelStatus.ACTIVE)

        # Pausing the booking gateway must keep hotel.status as ACTIVE
        paused_hotel = self._set_gateway(hotel, BookingGatewayStatus.PAUSED)
        self.assertEqual(paused_hotel.status, HotelStatus.ACTIVE)
        self.assertEqual(paused_hotel.booking_gateway_status, BookingGatewayStatus.PAUSED)

        # Hotel is still an approved active entity, only gateway is paused
        reloaded = repository.get_hotel(self.db, hotel.id)
        self.assertEqual(reloaded.status, HotelStatus.ACTIVE)
        self.assertEqual(reloaded.booking_gateway_status, BookingGatewayStatus.PAUSED)

    def test_public_discovery_respects_both_status_and_gateway(self) -> None:
        # 1. Hotel Active + Gateway Active -> Visible in public discovery
        hotel1 = hotel_service.create_hotel(
            self.db,
            self._sample_hotel_create_data(name="Active Hotel Pune", slug="active-hotel-pune", city="Pune", district="Pune"),
        )
        self._set_status(hotel1, HotelStatus.ACTIVE)
        self._set_gateway(hotel1, BookingGatewayStatus.ACTIVE)
        self._approve(hotel1)

        # 2. Hotel Active + Gateway Paused -> Excluded from public discovery
        hotel2 = hotel_service.create_hotel(
            self.db,
            self._sample_hotel_create_data(name="Paused Gateway Hotel", slug="paused-hotel-pune", city="Pune", district="Pune"),
        )
        self._set_status(hotel2, HotelStatus.ACTIVE)
        self._set_gateway(hotel2, BookingGatewayStatus.PAUSED)

        # 3. Hotel Suspended + Gateway Active -> Excluded from public discovery
        hotel3 = hotel_service.create_hotel(
            self.db,
            self._sample_hotel_create_data(name="Suspended Hotel", slug="suspended-hotel-pune", city="Pune", district="Pune"),
        )
        self._set_status(hotel3, HotelStatus.SUSPENDED)
        self._set_gateway(hotel3, BookingGatewayStatus.ACTIVE)

        public_list = repository.list_public_hotels(self.db, city="Pune", property_type=None, star_rating=None)
        public_ids = [h.id for h in public_list]

        self.assertIn(hotel1.id, public_ids)
        self.assertNotIn(hotel2.id, public_ids)
        self.assertNotIn(hotel3.id, public_ids)

        # Also verify public search_hotels service call
        search_res = public_hotel_service.search_hotels(
            self.db,
            city="Pune",
            district=None,
            check_in=None,
            check_out=None,
            adults=1,
            children=0,
            rooms=1,
            min_price=None,
            max_price=None,
            star_rating=None,
            property_type=None,
            amenities=[],
            sort=PublicHotelSort.RECOMMENDED,
        )
        found_ids = [item.id for item in search_res.items]
        self.assertEqual(found_ids, [hotel1.id])

    def test_filter_by_district_support(self) -> None:
        hotel_ratnagiri = hotel_service.create_hotel(
            self.db,
            self._sample_hotel_create_data(
                name="Konkan Beach Resort",
                slug="konkan-beach-resort",
                city="Ganpatipule",
                district="Ratnagiri",
            ),
        )
        self._set_status(hotel_ratnagiri, HotelStatus.ACTIVE)
        self._approve(hotel_ratnagiri)

        hotel_satara = hotel_service.create_hotel(
            self.db,
            self._sample_hotel_create_data(
                name="Hillside Retreat",
                slug="hillside-retreat",
                city="Mahabaleshwar",
                district="Satara",
            ),
        )
        self._set_status(hotel_satara, HotelStatus.ACTIVE)
        self._approve(hotel_satara)

        # Filter specifically by Ratnagiri district
        ratnagiri_list = repository.list_public_hotels(
            self.db,
            city=None,
            district="Ratnagiri",
            property_type=None,
            star_rating=None,
        )
        self.assertEqual(len(ratnagiri_list), 1)
        self.assertEqual(ratnagiri_list[0].id, hotel_ratnagiri.id)
        self.assertEqual(ratnagiri_list[0].district, "Ratnagiri")


if __name__ == "__main__":
    unittest.main(verbosity=2)
