import unittest
import uuid
from datetime import date, time
from decimal import Decimal

from sqlalchemy import delete

from app.database import SessionLocal
from app.models.hotel import (
    Amenity,
    Hotel,
    HotelPolicy,
    HotelStatus,
    BookingGatewayStatus,
    PropertyType,
    RoomInventory,
    RoomType,
    RoomTypeStatus,
    hotel_amenities,
)
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from tests.test_auth_integration import request_json


class PublicHotelIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        cls.city = f"Public Test City {suffix}"
        cls.active_slug = f"public-active-{suffix}"
        cls.draft_slug = f"public-draft-{suffix}"
        cls.amenity_slug = f"public-amenity-{suffix}"
        with SessionLocal() as db:
            amenity = Amenity(
                name=f"Public Amenity {suffix}",
                slug=cls.amenity_slug,
                category="Test",
                is_active=True,
            )
            active = Hotel(
                name="Public Active Hotel",
                slug=cls.active_slug,
                description="Customer-safe active hotel.",
                property_type=PropertyType.RESORT,
                star_rating=Decimal("4.5"),
                status=HotelStatus.ACTIVE,
                address_line1="1 Public Avenue",
                city=cls.city,
                state="Goa",
                country="India",
                postal_code="403001",
                check_in_time=time(14, 0),
                check_out_time=time(11, 0),
                is_featured=True,
                partner_booking_gateway_status=BookingGatewayStatus.ACTIVE,
                amenities=[amenity],
            )
            draft = Hotel(
                name="Public Draft Hotel",
                slug=cls.draft_slug,
                property_type=PropertyType.HOTEL,
                star_rating=Decimal("5.0"),
                status=HotelStatus.DRAFT,
                address_line1="2 Private Avenue",
                city=cls.city,
                state="Goa",
                country="India",
                postal_code="403002",
                check_in_time=time(14, 0),
                check_out_time=time(11, 0),
            )
            request_hotel = Hotel(name="Public Request Hotel", slug=f"public-request-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4.0"), status=HotelStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.BOOKING_ON_REQUEST, address_line1="3 Request Avenue", city=cls.city, state="Goa", country="India", postal_code="403003", check_in_time=time(14), check_out_time=time(11))
            paused_hotel = Hotel(name="Public Paused Hotel", slug=f"public-paused-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4.0"), status=HotelStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.PAUSED, address_line1="4 Paused Avenue", city=cls.city, state="Goa", country="India", postal_code="403004", check_in_time=time(14), check_out_time=time(11))
            unverified_hotel = Hotel(name="Private Unverified Hotel", slug=f"private-unverified-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("5.0"), status=HotelStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="5 Private Avenue", city=cls.city, state="Goa", country="India", postal_code="403005", check_in_time=time(14), check_out_time=time(11))
            db.add_all([active, draft, request_hotel, paused_hotel, unverified_hotel])
            db.flush()
            db.add(HotelVerification(hotel_id=active.id, business_name=active.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED))
            db.add_all([HotelVerification(hotel_id=request_hotel.id, business_name=request_hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED), HotelVerification(hotel_id=paused_hotel.id, business_name=paused_hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED)])
            cls.active_id = active.id
            cls.draft_id = draft.id
            cls.request_id, cls.paused_id, cls.unverified_id = request_hotel.id, paused_hotel.id, unverified_hotel.id
            active.policy = HotelPolicy(cancellation_policy="Free cancellation until 24 hours before arrival.")
            room = RoomType(
                hotel_id=active.id,
                name="Public Deluxe",
                description="Available public room.",
                max_adults=2,
                max_children=1,
                max_guests=3,
                bed_type="King",
                bed_count=1,
                room_size_sqm=Decimal("32.00"),
                base_price=Decimal("4500.00"),
                currency="INR",
                total_rooms=5,
                is_active=True,
                status=RoomTypeStatus.BOOKABLE,
            )
            db.add(room)
            db.flush()
            cls.room_id = room.id
            db.add_all(
                [
                    RoomInventory(
                        room_type_id=room.id,
                        inventory_date=date(2026, 12, 20),
                        total_inventory=5,
                        available_inventory=4,
                        blocked_inventory=1,
                        price=Decimal("5000.00"),
                        is_closed=False,
                    ),
                    RoomInventory(
                        room_type_id=room.id,
                        inventory_date=date(2026, 12, 21),
                        total_inventory=5,
                        available_inventory=3,
                        blocked_inventory=1,
                        price=Decimal("6000.00"),
                        is_closed=False,
                    ),
                ]
            )
            db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            db.execute(delete(RoomInventory).where(RoomInventory.room_type_id == cls.room_id))
            db.execute(delete(RoomType).where(RoomType.id == cls.room_id))
            db.execute(delete(HotelPolicy).where(HotelPolicy.hotel_id == cls.active_id))
            db.execute(delete(HotelVerification).where(HotelVerification.hotel_id.in_([cls.active_id, cls.request_id, cls.paused_id])))
            db.execute(delete(hotel_amenities).where(hotel_amenities.c.hotel_id == cls.active_id))
            db.execute(delete(Hotel).where(Hotel.id.in_([cls.active_id, cls.draft_id, cls.request_id, cls.paused_id, cls.unverified_id])))
            db.execute(delete(Amenity).where(Amenity.slug == cls.amenity_slug))
            db.commit()

    def test_public_search_detail_and_availability(self) -> None:
        code, visibility = request_json("GET", f"/hotels?city={self.city.replace(' ', '%20')}")
        self.assertEqual(code, 200, visibility)
        modes = {item["id"]: item["booking_mode"] for item in visibility["items"]}
        self.assertEqual(modes[self.active_id], "ACTIVE")
        self.assertEqual(modes[self.request_id], "BOOKING_ON_REQUEST")
        self.assertEqual(modes[self.paused_id], "PAUSED")
        self.assertNotIn(self.unverified_id, modes)
        query = (
            f"?city={self.city.replace(' ', '%20')}"
            "&check_in=2026-12-20&check_out=2026-12-22"
            "&adults=2&children=1&rooms=1"
        )
        code, search = request_json("GET", f"/hotels{query}")
        self.assertEqual(code, 200, search)
        self.assertEqual(search["total"], 2)  # Paused hotels remain discoverable but not bookable.
        self.assertEqual(search["items"][0]["id"], self.active_id)
        self.assertEqual(search["items"][0]["starting_price"], "5500.00")
        self.assertNotIn("status", search["items"][0])

        code, filtered = request_json("GET", f"/hotels{query}&amenities={self.amenity_slug}&max_price=5500")
        self.assertEqual(code, 200, filtered)
        self.assertEqual(filtered["total"], 1)
        code, filtered = request_json("GET", f"/hotels{query}&max_price=5499")
        self.assertEqual(code, 200, filtered)
        self.assertEqual(filtered["total"], 0)

        code, detail = request_json("GET", f"/hotels/{self.active_id}")
        self.assertEqual(code, 200, detail)
        self.assertEqual(detail["policy"]["cancellation_policy"], "Free cancellation until 24 hours before arrival.")
        self.assertNotIn("created_at", detail)
        code, slug_detail = request_json("GET", f"/hotels/{self.active_slug}")
        self.assertEqual(code, 200, slug_detail)
        self.assertEqual(slug_detail["id"], self.active_id)
        code, body = request_json("GET", f"/hotels/{self.draft_id}")
        self.assertEqual(code, 404, body)

        code, availability = request_json(
            "GET",
            f"/hotels/{self.active_id}/rooms?check_in=2026-12-20&check_out=2026-12-22&adults=2&children=1&rooms=1",
        )
        self.assertEqual(code, 200, availability)
        self.assertEqual(len(availability["items"]), 1)
        room = availability["items"][0]
        self.assertEqual(room["id"], self.room_id)
        self.assertEqual(room["available_rooms"], 3)
        code, slug_availability = request_json(
            "GET",
            f"/hotels/{self.active_slug}/rooms?check_in=2026-12-20&check_out=2026-12-22&adults=2&children=1&rooms=1",
        )
        self.assertEqual(code, 200, slug_availability)
        self.assertEqual(slug_availability["hotel_id"], self.active_id)
        self.assertEqual(room["price_per_night"], "5500.00")
        self.assertEqual(room["estimated_total"], "11000.00")

        code, unavailable = request_json(
            "GET",
            f"/hotels/{self.active_id}/rooms?check_in=2026-12-20&check_out=2026-12-23&adults=2&children=1&rooms=1",
        )
        self.assertEqual(code, 200, unavailable)
        self.assertEqual(unavailable["items"], [])
        code, invalid = request_json(
            "GET",
            f"/hotels/{self.active_id}/rooms?check_in=2026-12-22&check_out=2026-12-20",
        )
        self.assertEqual(code, 422, invalid)

    def test_non_bookable_room_lifecycle_states_are_not_publicly_sellable(self) -> None:
        query = (
            f"?city={self.city.replace(' ', '%20')}"
            "&check_in=2026-12-20&check_out=2026-12-22"
            "&adults=2&children=1&rooms=1"
        )
        try:
            for room_status in (
                RoomTypeStatus.DRAFT,
                RoomTypeStatus.PENDING,
                RoomTypeStatus.APPROVED,
                RoomTypeStatus.NEEDS_CHANGES,
            ):
                with self.subTest(room_status=room_status.value), SessionLocal() as db:
                    room = db.get(RoomType, self.room_id)
                    room.status = room_status
                    db.commit()
                code, search = request_json("GET", f"/hotels{query}")
                self.assertEqual(code, 200, search)
                self.assertNotIn(self.active_id, {item["id"] for item in search["items"]})
                code, availability = request_json(
                    "GET",
                    f"/hotels/{self.active_id}/rooms?check_in=2026-12-20&check_out=2026-12-22&adults=2&children=1&rooms=1",
                )
                self.assertEqual(code, 200, availability)
                self.assertEqual(availability["items"], [])
                code, detail = request_json("GET", f"/hotels/{self.active_id}")
                self.assertEqual(code, 200, detail)
                self.assertIsNone(detail["starting_price"])
        finally:
            with SessionLocal() as db:
                room = db.get(RoomType, self.room_id)
                room.status = RoomTypeStatus.BOOKABLE
                db.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
