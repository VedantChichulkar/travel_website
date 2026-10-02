import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, PropertyType, RoomInventory, RoomType
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.services import booking_gateway_service
from app.api.v1.partner_hotels import update_booking_gateway
from app.schemas.hotel import HotelBookingGatewayUpdate


class BookingGatewayServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        token = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            self.partner = User(full_name="Gateway Partner", email=f"gateway-partner-{token}@example.com", phone=f"+919{uuid.uuid4().int % 1_000_000_000:09d}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            self.admin = User(full_name="Gateway Admin", email=f"gateway-admin-{token}@example.com", phone=f"+918{uuid.uuid4().int % 1_000_000_000:09d}", password_hash=hash_password("StrongPass123"), role=UserRole.ADMIN)
            db.add_all([self.partner, self.admin]); db.flush()
            self.hotel = Hotel(name="Gateway Hotel", slug=f"gateway-{token}", property_type=PropertyType.HOTEL, star_rating=Decimal("4.0"), status=HotelStatus.ACTIVE, booking_gateway_status=BookingGatewayStatus.PAUSED, partner_booking_gateway_status=BookingGatewayStatus.PAUSED, address_line1="1 Gateway Road", city="Pune", state="Maharashtra", country="India", postal_code="411001", partner_id=self.partner.id, check_in_time=time(14), check_out_time=time(11))
            db.add(self.hotel); db.flush()
            db.add(HotelVerification(hotel_id=self.hotel.id, business_name="Gateway Hotel", business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED))
            room = RoomType(hotel_id=self.hotel.id, name="Gateway Room", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("3000"), currency="INR", total_rooms=2)
            db.add(room); db.flush()
            db.add(RoomInventory(room_type_id=room.id, inventory_date=date.today() + timedelta(days=2), total_inventory=2, available_inventory=2, blocked_inventory=0, confirmed_inventory=0, held_inventory=0, price=Decimal("3000"), is_closed=False))
            db.commit()
            self.hotel_id, self.partner_id, self.admin_id, self.inventory_room_id = self.hotel.id, self.partner.id, self.admin.id, room.id

    def tearDown(self) -> None:
        with SessionLocal() as db:
            db.execute(delete(RoomInventory).where(RoomInventory.room_type_id == self.inventory_room_id))
            db.execute(delete(RoomType).where(RoomType.id == self.inventory_room_id))
            db.execute(delete(HotelVerification).where(HotelVerification.hotel_id == self.hotel_id))
            db.execute(delete(Hotel).where(Hotel.id == self.hotel_id))
            db.execute(delete(User).where(User.id.in_([self.partner_id, self.admin_id])))
            db.commit()

    def test_partner_transition_admin_override_and_stale_fallback(self) -> None:
        with SessionLocal() as db:
            hotel, admin, partner = db.get(Hotel, self.hotel_id), db.get(User, self.admin_id), db.get(User, self.partner_id)
            # Exercise the partner API handler with the authenticated tenant.
            active = update_booking_gateway(HotelBookingGatewayUpdate(booking_gateway_status=BookingGatewayStatus.ACTIVE), db, partner)
            self.assertEqual(active.effective_status, BookingGatewayStatus.ACTIVE)
            paused = booking_gateway_service.set_override(db, hotel, admin, BookingGatewayStatus.PAUSED, "Safety review")
            self.assertEqual(paused.effective_status, BookingGatewayStatus.PAUSED)
            self.assertEqual(hotel.booking_gateway_status, BookingGatewayStatus.PAUSED)
            with self.assertRaises(HTTPException):
                booking_gateway_service.update_partner(db, hotel, BookingGatewayStatus.BOOKING_ON_REQUEST)
            restored = booking_gateway_service.clear_override(db, hotel)
            self.assertEqual(restored.effective_status, BookingGatewayStatus.ACTIVE)
            self.assertEqual(hotel.booking_gateway_status, hotel.partner_booking_gateway_status)
            inventory = db.query(RoomInventory).filter_by(room_type_id=self.inventory_room_id).one()
            inventory.updated_at = datetime.now(timezone.utc) - timedelta(hours=25)
            db.commit()
            stale = booking_gateway_service.state(db, hotel)
            self.assertEqual(stale.effective_status, BookingGatewayStatus.BOOKING_ON_REQUEST)


if __name__ == "__main__":
    unittest.main()
