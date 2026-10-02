import unittest
import uuid

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.hotel import (
    Amenity,
    Hotel,
    HotelImage,
    HotelPolicy,
    RoomImage,
    RoomInventory,
    RoomType,
    hotel_amenities,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user
from tests.test_auth_integration import request_json


class HotelManagementIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        digits = str(uuid.uuid4().int)[-9:]
        cls.password = "StrongPass123"
        cls.admin_email = f"hotel-admin-{suffix}@example.com"
        cls.user_email = f"hotel-user-{suffix}@example.com"
        cls.admin_phone = f"+916{digits}"
        cls.user_phone = f"+915{digits}"
        cls.hotel_slug = f"integration-hotel-{suffix}"
        cls.amenity_slugs = [f"test-wifi-{suffix}", f"test-parking-{suffix}"]

        with SessionLocal() as db:
            db.execute(delete(User).where(User.email.in_([cls.admin_email, cls.user_email])))
            db.commit()
            create_user(
                db,
                full_name="Hotel Test Admin",
                email=cls.admin_email,
                phone=cls.admin_phone,
                password_hash=hash_password(cls.password),
                role=UserRole.ADMIN,
            )
            create_user(
                db,
                full_name="Hotel Test User",
                email=cls.user_email,
                phone=cls.user_phone,
                password_hash=hash_password(cls.password),
                role=UserRole.USER,
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            hotel_id = db.scalar(select(Hotel.id).where(Hotel.slug == cls.hotel_slug))
            if hotel_id is not None:
                room_ids = list(db.scalars(select(RoomType.id).where(RoomType.hotel_id == hotel_id)))
                if room_ids:
                    db.execute(delete(RoomInventory).where(RoomInventory.room_type_id.in_(room_ids)))
                    db.execute(delete(RoomImage).where(RoomImage.room_type_id.in_(room_ids)))
                    db.execute(delete(RoomType).where(RoomType.id.in_(room_ids)))
                db.execute(delete(HotelPolicy).where(HotelPolicy.hotel_id == hotel_id))
                db.execute(delete(HotelImage).where(HotelImage.hotel_id == hotel_id))
                db.execute(delete(hotel_amenities).where(hotel_amenities.c.hotel_id == hotel_id))
                db.execute(delete(Hotel).where(Hotel.id == hotel_id))
            db.execute(delete(Amenity).where(Amenity.slug.in_(cls.amenity_slugs)))
            db.execute(delete(User).where(User.email.in_([cls.admin_email, cls.user_email])))
            db.commit()

    def test_hotel_management_flow(self) -> None:
        status_code, admin_login = request_json(
            "POST",
            "/auth/login",
            {"email": self.admin_email, "password": self.password},
        )
        self.assertEqual(status_code, 200, admin_login)
        admin_token = str(admin_login["access_token"])

        status_code, user_login = request_json(
            "POST",
            "/auth/login",
            {"email": self.user_email, "password": self.password},
        )
        self.assertEqual(status_code, 200, user_login)
        user_token = str(user_login["access_token"])

        hotel_payload = {
            "name": "Integration Grand Hotel",
            "slug": self.hotel_slug,
            "description": "Temporary hotel used for API verification.",
            "property_type": "HOTEL",
            "star_rating": "4.5",
            "address_line1": "100 Test Avenue",
            "address_line2": None,
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "postal_code": "400001",
            "latitude": "18.9388",
            "longitude": "72.8354",
            "contact_email": "hotel-contact@example.com",
            "contact_phone": "+919123456789",
            "check_in_time": "14:00:00",
            "check_out_time": "11:00:00",
            "is_featured": False,
        }

        status_code, body = request_json("POST", "/admin/hotels", hotel_payload, user_token)
        self.assertEqual(status_code, 403, body)

        status_code, hotel = request_json("POST", "/admin/hotels", hotel_payload, admin_token)
        self.assertEqual(status_code, 201, hotel)
        hotel_id = int(hotel["id"])
        self.assertEqual(hotel["status"], "DRAFT")

        status_code, detail = request_json("GET", f"/admin/hotels/{hotel_id}", token=admin_token)
        self.assertEqual(status_code, 200, detail)
        self.assertEqual(detail["slug"], self.hotel_slug)

        status_code, updated = request_json(
            "PATCH",
            f"/admin/hotels/{hotel_id}",
            {"description": "Updated integration hotel description.", "is_featured": True},
            admin_token,
        )
        self.assertEqual(status_code, 200, updated)
        self.assertTrue(updated["is_featured"])

        status_code, active_hotel = request_json(
            "PATCH",
            f"/admin/hotels/{hotel_id}/status",
            {"status": "ACTIVE", "reason": "Activate verified integration hotel"},
            admin_token,
        )
        self.assertEqual(status_code, 200, active_hotel)
        self.assertEqual(active_hotel["status"], "ACTIVE")

        status_code, image = request_json(
            "POST",
            f"/admin/hotels/{hotel_id}/images",
            {"image_url": "https://example.com/hotel.jpg", "alt_text": "Hotel exterior", "is_cover": True, "display_order": 0},
            admin_token,
        )
        self.assertEqual(status_code, 201, image)

        amenity_ids: list[int] = []
        for name, slug in [("Test Wi-Fi", self.amenity_slugs[0]), ("Test Parking", self.amenity_slugs[1])]:
            status_code, amenity = request_json(
                "POST",
                "/admin/amenities",
                {"name": f"{name} {self.hotel_slug[-6:]}", "slug": slug, "category": "Test", "is_active": True},
                admin_token,
            )
            self.assertEqual(status_code, 201, amenity)
            amenity_ids.append(int(amenity["id"]))

        status_code, assigned = request_json(
            "PUT",
            f"/admin/hotels/{hotel_id}/amenities",
            {"amenity_ids": amenity_ids},
            admin_token,
        )
        self.assertEqual(status_code, 200, assigned)
        self.assertEqual(len(assigned), 2)

        status_code, policy = request_json(
            "POST",
            f"/admin/hotels/{hotel_id}/policy",
            {"cancellation_policy": "Free cancellation until 24 hours before arrival.", "smoking_policy": "No smoking."},
            admin_token,
        )
        self.assertEqual(status_code, 201, policy)

        room_payload = {
            "name": "Deluxe Room",
            "description": "Temporary room type.",
            "max_adults": 2,
            "max_children": 1,
            "max_guests": 3,
            "bed_type": "King",
            "bed_count": 1,
            "room_size_sqm": "32.50",
            "base_price": "6500.00",
            "currency": "INR",
            "total_rooms": 12,
            "is_active": True,
        }
        status_code, room = request_json(
            "POST",
            f"/admin/hotels/{hotel_id}/rooms",
            room_payload,
            admin_token,
        )
        self.assertEqual(status_code, 201, room)
        room_id = int(room["id"])

        status_code, inventory = request_json(
            "POST",
            f"/admin/rooms/{room_id}/inventory",
            {
                "inventory_date": "2026-09-01",
                "total_inventory": 12,
                "available_inventory": 10,
                "blocked_inventory": 2,
                "price": "7000.00",
                "is_closed": False,
            },
            admin_token,
        )
        self.assertEqual(status_code, 201, inventory)

        status_code, duplicate_inventory = request_json(
            "POST",
            f"/admin/rooms/{room_id}/inventory",
            {
                "inventory_date": "2026-09-01",
                "total_inventory": 12,
                "available_inventory": 12,
                "blocked_inventory": 0,
                "price": "7000.00",
                "is_closed": False,
            },
            admin_token,
        )
        self.assertEqual(status_code, 409, duplicate_inventory)

        status_code, invalid_inventory = request_json(
            "POST",
            f"/admin/rooms/{room_id}/inventory",
            {
                "inventory_date": "2026-09-02",
                "total_inventory": 12,
                "available_inventory": 13,
                "blocked_inventory": 0,
                "price": "7000.00",
                "is_closed": False,
            },
            admin_token,
        )
        self.assertEqual(status_code, 422, invalid_inventory)

        status_code, inventory_list = request_json(
            "GET",
            f"/admin/rooms/{room_id}/inventory?start_date=2026-09-01&end_date=2026-09-30",
            token=admin_token,
        )
        self.assertEqual(status_code, 200, inventory_list)
        self.assertEqual(len(inventory_list), 1)
        self.assertEqual(inventory_list[0]["inventory_date"], "2026-09-01")

        status_code, final_detail = request_json("GET", f"/admin/hotels/{hotel_id}", token=admin_token)
        self.assertEqual(status_code, 200, final_detail)
        self.assertEqual(len(final_detail["amenities"]), 2)
        self.assertEqual(len(final_detail["room_types"]), 1)
        self.assertIsNotNone(final_detail["policy"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
