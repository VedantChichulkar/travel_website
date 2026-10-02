import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, BookingTraveller, PaymentStatus
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, InventoryHold, PropertyType, RoomInventory, RoomType, RoomTypeStatus
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from tests.test_auth_integration import request_json
from app.services import inventory_service


class BookingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        digits = str(uuid.uuid4().int)[-9:]
        cls.password = "StrongPass123"
        cls.user_email = f"booking-user-{suffix}@example.com"
        cls.other_email = f"booking-other-{suffix}@example.com"
        cls.admin_email = f"booking-admin-{suffix}@example.com"
        cls.partner_email = f"booking-partner-{suffix}@example.com"
        cls.other_partner_email = f"booking-other-partner-{suffix}@example.com"
        with SessionLocal() as db:
            users = [
                User(full_name="Booking User", email=cls.user_email, phone=f"+919{digits}", password_hash=hash_password(cls.password), role=UserRole.USER),
                User(full_name="Other User", email=cls.other_email, phone=f"+918{digits}", password_hash=hash_password(cls.password), role=UserRole.USER),
                User(full_name="Booking Admin", email=cls.admin_email, phone=f"+917{digits}", password_hash=hash_password(cls.password), role=UserRole.ADMIN),
                User(full_name="Booking Partner", email=cls.partner_email, phone=f"+916{digits}", password_hash=hash_password(cls.password), role=UserRole.HOTEL_PARTNER),
                User(full_name="Other Booking Partner", email=cls.other_partner_email, phone=f"+915{digits}", password_hash=hash_password(cls.password), role=UserRole.HOTEL_PARTNER),
            ]
            db.add_all(users)
            db.flush()
            hotel = Hotel(name="Booking Test Hotel", slug=f"booking-test-{suffix}", partner_id=users[3].id, property_type=PropertyType.HOTEL, star_rating=Decimal("4.0"), status=HotelStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Booking Road", city="Test City", state="Goa", country="India", postal_code="403001", check_in_time=time(14), check_out_time=time(11))
            other_hotel = Hotel(name="Other Booking Hotel", slug=f"booking-other-{suffix}", partner_id=users[4].id, property_type=PropertyType.HOTEL, star_rating=Decimal("3.0"), status=HotelStatus.ACTIVE, address_line1="2 Booking Road", city="Test City", state="Goa", country="India", postal_code="403002", check_in_time=time(14), check_out_time=time(11))
            db.add_all([hotel, other_hotel])
            db.flush()
            db.add(HotelVerification(hotel_id=hotel.id, business_name=hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED))
            room = RoomType(hotel_id=hotel.id, name="Booking Deluxe", max_adults=2, max_children=1, max_guests=3, bed_type="King", bed_count=1, base_price=Decimal("4000.00"), currency="INR", total_rooms=5, is_active=True, status=RoomTypeStatus.BOOKABLE)
            wrong_room = RoomType(hotel_id=other_hotel.id, name="Other Room", max_adults=2, max_children=0, max_guests=2, bed_type="Queen", bed_count=1, base_price=Decimal("3000.00"), currency="INR", total_rooms=2, is_active=True, status=RoomTypeStatus.BOOKABLE)
            db.add_all([room, wrong_room])
            db.flush()
            db.add_all([
                RoomInventory(room_type_id=room.id, inventory_date=date(2026, 12, 20), total_inventory=5, available_inventory=3, blocked_inventory=0, price=Decimal("5000.00"), is_closed=False),
                RoomInventory(room_type_id=room.id, inventory_date=date(2026, 12, 21), total_inventory=5, available_inventory=2, blocked_inventory=0, price=Decimal("6000.00"), is_closed=False),
            ])
            db.commit()
            cls.user_id, cls.other_user_id, cls.admin_id, cls.partner_id, cls.other_partner_id = (user.id for user in users)
            cls.hotel_id, cls.other_hotel_id, cls.room_id, cls.wrong_room_id = hotel.id, other_hotel.id, room.id, wrong_room.id

        cls.user_token = cls._login(cls.user_email)
        cls.other_token = cls._login(cls.other_email)
        cls.admin_token = cls._login(cls.admin_email)
        cls.partner_token = cls._login(cls.partner_email)
        cls.other_partner_token = cls._login(cls.other_partner_email)

    @classmethod
    def _login(cls, email: str) -> str:
        code, result = request_json("POST", "/auth/login", {"email": email, "password": cls.password})
        if code != 200:
            raise AssertionError(result)
        return str(result["access_token"])

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            booking_ids = list(db.scalars(select(Booking.id).where(Booking.user_id.in_([cls.user_id, cls.other_user_id]))))
            if booking_ids:
                db.execute(delete(BookingStatusHistory).where(BookingStatusHistory.booking_id.in_(booking_ids)))
                db.execute(delete(BookingTraveller).where(BookingTraveller.booking_id.in_(booking_ids)))
                db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))
            db.execute(delete(InventoryHold).where(InventoryHold.room_type_id == cls.room_id))
            db.execute(delete(RoomInventory).where(RoomInventory.room_type_id == cls.room_id))
            db.execute(delete(HotelVerification).where(HotelVerification.hotel_id == cls.hotel_id))
            db.execute(delete(RoomType).where(RoomType.id.in_([cls.room_id, cls.wrong_room_id])))
            db.execute(delete(Hotel).where(Hotel.id.in_([cls.hotel_id, cls.other_hotel_id])))
            db.execute(delete(User).where(User.id.in_([cls.user_id, cls.other_user_id, cls.admin_id, cls.partner_id, cls.other_partner_id])))
            db.commit()

    def test_booking_flow_authorization_and_validation(self) -> None:
        stay = {"hotel_id": self.hotel_id, "room_type_id": self.room_id, "check_in": "2026-12-20", "check_out": "2026-12-22", "rooms": 1, "adults": 2, "children": 0}
        code, body = request_json("POST", "/bookings/quote", stay)
        self.assertEqual(code, 401, body)
        code, quote = request_json("POST", "/bookings/quote", stay, self.user_token)
        self.assertEqual(code, 200, quote)
        self.assertEqual(quote["nights"], 2)
        self.assertEqual(quote["subtotal"], "11000.00")
        self.assertEqual(quote["taxes"], "1320.00")
        self.assertEqual(quote["total_amount"], "12320.00")

        code, hold = request_json("POST", "/bookings/holds", stay, self.user_token)
        self.assertEqual(code, 201, hold)
        payload = {**stay, "hold_token": hold["hold_token"], "idempotency_key": f"booking-{uuid.uuid4().hex}", "travellers": [{"full_name": "Primary Traveller", "age": 30, "email": self.user_email, "phone": "+919876543210", "is_primary": True}, {"full_name": "Second Traveller", "age": 28, "is_primary": False}]}
        code, stolen = request_json("POST", "/bookings", payload, self.other_token)
        self.assertEqual(code, 404, stolen)
        code, created = request_json("POST", "/bookings", payload, self.user_token)
        self.assertEqual(code, 201, created)
        self.assertRegex(str(created["booking_reference"]), r"^TRV-HOT-\d{4}-\d{6}$")
        self.assertEqual(created["status"], BookingStatus.PAYMENT_PENDING.value)
        self.assertEqual(created["payment_status"], PaymentStatus.NOT_STARTED.value)
        self.assertEqual(created["hold_token"], hold["hold_token"])
        self.assertEqual(created["room_snapshot"]["name"], "Booking Deluxe")
        self.assertEqual(created["price_snapshot"]["total_amount"], "12320.00")
        self.assertEqual(created["hotel"]["id"], self.hotel_id)
        self.assertEqual(created["room"]["id"], self.room_id)
        self.assertEqual(len(created["travellers"]), 2)
        self.assertEqual(created["status_history"][0]["new_status"], BookingStatus.PAYMENT_PENDING.value)
        booking_id = int(created["id"])

        code, repeated = request_json("POST", "/bookings", payload, self.user_token)
        self.assertEqual(code, 201, repeated)
        self.assertEqual(repeated["id"], booking_id)

        with SessionLocal() as db:
            inventory = list(db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == self.room_id).order_by(RoomInventory.inventory_date)))
            # The booking keeps its temporary hold until a verified payment
            # atomically converts it to a confirmed commitment.
            self.assertEqual([row.available_inventory for row in inventory], [2, 1])

        code, mine = request_json("GET", "/bookings/me", token=self.user_token)
        self.assertEqual(code, 200, mine)
        self.assertEqual(mine["total"], 1)
        code, detail = request_json("GET", f"/bookings/{booking_id}", token=self.user_token)
        self.assertEqual(code, 200, detail)
        code, hidden = request_json("GET", f"/bookings/{booking_id}", token=self.other_token)
        self.assertEqual(code, 404, hidden)
        code, admin_detail = request_json("GET", f"/admin/bookings/{booking_id}", token=self.admin_token)
        self.assertEqual(code, 200, admin_detail)
        code, admin_list = request_json("GET", "/admin/bookings", token=self.admin_token)
        self.assertEqual(code, 200, admin_list)
        self.assertGreaterEqual(admin_list["total"], 1)
        code, forbidden = request_json("GET", "/admin/bookings", token=self.user_token)
        self.assertEqual(code, 403, forbidden)

        code, wrong_relation = request_json("POST", "/bookings/quote", {**stay, "room_type_id": self.wrong_room_id}, self.user_token)
        self.assertEqual(code, 422, wrong_relation)
        code, capacity = request_json("POST", "/bookings/quote", {**stay, "adults": 3}, self.user_token)
        self.assertEqual(code, 422, capacity)
        code, unavailable = request_json("POST", "/bookings/quote", {**stay, "rooms": 3}, self.user_token)
        self.assertEqual(code, 409, unavailable)
        code, invalid_dates = request_json("POST", "/bookings/quote", {**stay, "check_out": "2026-12-20"}, self.user_token)
        self.assertEqual(code, 422, invalid_dates)
        code, invalid_travellers = request_json("POST", "/bookings", {**stay, "travellers": [{"full_name": "Only Traveller", "age": 30, "is_primary_guest": True}]}, self.user_token)
        self.assertEqual(code, 422, invalid_travellers)

        aliased_stay = {"hotel_id": self.hotel_id, "room_type_id": self.room_id, "check_in_date": "2026-12-20", "check_out_date": "2026-12-22", "rooms_booked": 1, "adults": 2, "children": 0}
        code, aliased_quote = request_json("POST", "/bookings/quote", aliased_stay, self.user_token)
        self.assertEqual(code, 200, aliased_quote)
        self.assertEqual(aliased_quote["total_amount"], "12320.00")

    def test_expired_hold_releases_capacity(self) -> None:
        stay = {"hotel_id": self.hotel_id, "room_type_id": self.room_id, "check_in": "2026-12-20", "check_out": "2026-12-22", "rooms": 1, "adults": 2, "children": 0}
        code, hold = request_json("POST", "/bookings/holds", stay, self.user_token)
        self.assertEqual(code, 201, hold)
        with SessionLocal() as db:
            inventory_service.expire_holds(db, room_type_id=self.room_id, now=datetime.now(timezone.utc) + timedelta(hours=1))
            db.commit()
            inventory = list(db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == self.room_id).order_by(RoomInventory.inventory_date)))
            self.assertEqual([row.held_inventory for row in inventory], [0, 0])
        payload = {**stay, "hold_token": hold["hold_token"], "idempotency_key": f"expired-{uuid.uuid4().hex}", "travellers": [{"full_name": "Primary Traveller", "age": 30, "is_primary": True}, {"full_name": "Second Traveller", "age": 28, "is_primary": False}]}
        code, expired = request_json("POST", "/bookings", payload, self.user_token)
        self.assertEqual(code, 409, expired)

    def test_partner_booking_request_routes_enforce_ownership_and_decisions(self) -> None:
        stay = {"hotel_id": self.hotel_id, "room_type_id": self.room_id, "check_in": "2026-12-20", "check_out": "2026-12-22", "rooms": 1, "adults": 1, "children": 0}
        with SessionLocal() as db:
            hotel = db.get(Hotel, self.hotel_id)
            hotel.partner_booking_gateway_status = BookingGatewayStatus.BOOKING_ON_REQUEST
            hotel.booking_gateway_status = BookingGatewayStatus.BOOKING_ON_REQUEST
            db.execute(delete(InventoryHold).where(InventoryHold.room_type_id == self.room_id))
            for inventory in db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == self.room_id)):
                inventory.held_inventory = 0
                inventory.confirmed_inventory = 0
                inventory.available_inventory = inventory.total_inventory - inventory.blocked_inventory
            db.commit()
        try:
            code, hold = request_json("POST", "/bookings/holds", stay, self.user_token)
            self.assertEqual(code, 201, hold)
            payload = {**stay, "hold_token": hold["hold_token"], "idempotency_key": f"partner-request-{uuid.uuid4().hex}", "travellers": [{"full_name": "Request Guest", "age": 30, "is_primary": True}]}
            code, created = request_json("POST", "/bookings", payload, self.user_token)
            self.assertEqual(code, 201, created)
            self.assertEqual(created["status"], BookingStatus.PENDING.value)

            code, listed = request_json("GET", "/partner/booking-requests", token=self.partner_token)
            self.assertEqual(code, 200, listed)
            self.assertIn(created["booking_reference"], [item["booking_reference"] for item in listed["items"]])
            code, all_bookings = request_json("GET", "/partner/bookings", token=self.partner_token)
            self.assertEqual(code, 200, all_bookings)
            self.assertIn(created["booking_reference"], [item["booking_reference"] for item in all_bookings["items"]])
            code, other_list = request_json("GET", "/partner/booking-requests", token=self.other_partner_token)
            self.assertEqual(code, 200, other_list)
            self.assertNotIn(created["booking_reference"], [item["booking_reference"] for item in other_list["items"]])
            code, other_all = request_json("GET", "/partner/bookings", token=self.other_partner_token)
            self.assertEqual(code, 200, other_all)
            self.assertNotIn(created["booking_reference"], [item["booking_reference"] for item in other_all["items"]])
            code, hidden = request_json("POST", f"/partner/booking-requests/{created['id']}/accept", {}, self.other_partner_token)
            self.assertEqual(code, 404, hidden)
            code, accepted = request_json("POST", f"/partner/booking-requests/{created['id']}/accept", {}, self.partner_token)
            self.assertEqual(code, 200, accepted)
            self.assertEqual(accepted["status"], BookingStatus.PAYMENT_PENDING.value)
            code, duplicate = request_json("POST", f"/partner/booking-requests/{created['id']}/accept", {}, self.partner_token)
            self.assertEqual(code, 409, duplicate)

            code, second_hold = request_json("POST", "/bookings/holds", stay, self.other_token)
            self.assertEqual(code, 201, second_hold)
            second_payload = {**stay, "hold_token": second_hold["hold_token"], "idempotency_key": f"partner-reject-{uuid.uuid4().hex}", "travellers": [{"full_name": "Declined Guest", "age": 29, "is_primary": True}]}
            code, second = request_json("POST", "/bookings", second_payload, self.other_token)
            self.assertEqual(code, 201, second)
            code, invalid = request_json("POST", f"/partner/booking-requests/{second['id']}/reject", {"reason": "no"}, self.partner_token)
            self.assertEqual(code, 422, invalid)
            code, rejected = request_json("POST", f"/partner/booking-requests/{second['id']}/reject", {"reason": "Requested dates cannot be accommodated."}, self.partner_token)
            self.assertEqual(code, 200, rejected)
            self.assertEqual(rejected["status"], BookingStatus.REQUEST_REJECTED.value)
        finally:
            with SessionLocal() as db:
                hotel = db.get(Hotel, self.hotel_id)
                hotel.partner_booking_gateway_status = BookingGatewayStatus.ACTIVE
                hotel.booking_gateway_status = BookingGatewayStatus.ACTIVE
                db.commit()

    def test_only_active_bookable_rooms_cross_booking_boundaries(self) -> None:
        stay = {"hotel_id": self.hotel_id, "room_type_id": self.room_id, "check_in": "2026-12-20", "check_out": "2026-12-22", "rooms": 1, "adults": 2, "children": 0}
        blocked_statuses = (RoomTypeStatus.DRAFT, RoomTypeStatus.PENDING, RoomTypeStatus.APPROVED, RoomTypeStatus.NEEDS_CHANGES)
        try:
            for room_status in blocked_statuses:
                with self.subTest(room_status=room_status.value), SessionLocal() as db:
                    room = db.get(RoomType, self.room_id)
                    room.status = room_status
                    db.commit()
                code, body = request_json("POST", "/bookings/quote", stay, self.user_token)
                self.assertEqual(code, 409, body)
                code, body = request_json("POST", "/bookings/holds", stay, self.user_token)
                self.assertEqual(code, 409, body)

            with SessionLocal() as db:
                room = db.get(RoomType, self.room_id)
                room.status = RoomTypeStatus.BOOKABLE
                room.is_active = False
                db.commit()
            code, body = request_json("POST", "/bookings/quote", stay, self.user_token)
            self.assertEqual(code, 409, body)

            with SessionLocal() as db:
                room = db.get(RoomType, self.room_id)
                room.is_active = True
                db.commit()
            code, hold = request_json("POST", "/bookings/holds", stay, self.user_token)
            self.assertEqual(code, 201, hold)
            with SessionLocal() as db:
                room = db.get(RoomType, self.room_id)
                room.status = RoomTypeStatus.APPROVED
                db.commit()
            payload = {**stay, "hold_token": hold["hold_token"], "idempotency_key": f"lifecycle-{uuid.uuid4().hex}", "travellers": [{"full_name": "Primary Traveller", "age": 30, "is_primary": True}, {"full_name": "Second Traveller", "age": 28, "is_primary": False}]}
            code, body = request_json("POST", "/bookings", payload, self.user_token)
            self.assertEqual(code, 409, body)
        finally:
            with SessionLocal() as db:
                room = db.get(RoomType, self.room_id)
                room.status = RoomTypeStatus.BOOKABLE
                room.is_active = True
                db.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
