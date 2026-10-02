import unittest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.audit import AuditLog
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.hotel import Hotel, HotelStatus, InventoryHold, PropertyType, RoomInventory, RoomType
from app.models.user import User, UserRole
from app.schemas.hotel import PartnerInventoryRangeUpdate, RoomInventoryUpdate
from app.services import inventory_service


class AdminInventorySafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.admin = User(full_name="Inventory Admin", email="inventory-admin@example.com", phone="+919100001001", password_hash="x", role=UserRole.ADMIN)
        self.customer = User(full_name="Inventory Guest", email="inventory-guest@example.com", phone="+919100001002", password_hash="x", role=UserRole.CUSTOMER)
        self.partner = User(full_name="Inventory Partner", email="inventory-partner@example.com", phone="+919100001003", password_hash="x", role=UserRole.HOTEL_PARTNER)
        self.db.add_all([self.admin, self.customer, self.partner]); self.db.flush()
        self.hotel = Hotel(name="Inventory Hotel", slug="inventory-hotel", property_type=PropertyType.HOMESTAY, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=self.partner.id, address_line1="1 Capacity Road", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
        self.db.add(self.hotel); self.db.flush()
        self.room = RoomType(hotel_id=self.hotel.id, name="Safe Room", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("1000"), currency="INR", total_rooms=10)
        self.db.add(self.room); self.db.flush()

        base_day = date.today() + timedelta(days=30)
        self.mixed_day, self.held_day, self.confirmed_day = base_day, base_day + timedelta(days=1), base_day + timedelta(days=2)
        self.rows = []
        for day, available, confirmed, held in (
            (self.mixed_day, 4, 3, 2),
            (self.held_day, 7, 0, 3),
            (self.confirmed_day, 7, 3, 0),
        ):
            row = RoomInventory(room_type_id=self.room.id, inventory_date=day, total_inventory=10, available_inventory=available, blocked_inventory=1 if day == self.mixed_day else 0, confirmed_inventory=confirmed, held_inventory=held, price=Decimal("1000"), is_closed=False)
            self.db.add(row); self.rows.append(row)
        self.db.flush()
        self.db.add(InventoryHold(hold_token="mixed-hold", hotel_id=self.hotel.id, room_type_id=self.room.id, user_id=self.customer.id, check_in=self.mixed_day, check_out=self.mixed_day + timedelta(days=1), rooms=2, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        self.db.add(InventoryHold(hold_token="held-only", hotel_id=self.hotel.id, room_type_id=self.room.id, user_id=self.customer.id, check_in=self.held_day, check_out=self.held_day + timedelta(days=1), rooms=3, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        self.db.add(self._booking("VYO-SAFE-MIXED", self.mixed_day, 3))
        self.db.add(self._booking("VYO-SAFE-CONFIRMED", self.confirmed_day, 3))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    def _booking(self, reference: str, check_in: date, rooms: int) -> Booking:
        return Booking(booking_reference=reference, user_id=self.customer.id, hotel_id=self.hotel.id, room_type_id=self.room.id, check_in=check_in, check_out=check_in + timedelta(days=1), rooms=rooms, adults=1, children=0, nights=1, currency="INR", subtotal=Decimal("1000"), taxes=Decimal("0"), platform_fee=Decimal("0"), discount=Decimal("0"), total_amount=Decimal("1000"), room_snapshot={}, price_snapshot={}, policy_snapshot={}, status=BookingStatus.CONFIRMED, payment_status=PaymentStatus.PAID)

    def test_admin_cannot_reduce_below_held_inventory(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            inventory_service.update_admin_inventory(self.db, self.rows[1].id, RoomInventoryUpdate(total_inventory=2), self.admin)
        self.assertEqual(raised.exception.status_code, 409)
        self.db.rollback()

    def test_admin_cannot_reduce_below_confirmed_inventory(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            inventory_service.update_admin_inventory(self.db, self.rows[2].id, RoomInventoryUpdate(total_inventory=2), self.admin)
        self.assertEqual(raised.exception.status_code, 409)
        self.db.rollback()

    def test_admin_update_uses_locking_path_and_creates_audit(self) -> None:
        with patch("app.services.inventory_service._locked_rows", wraps=inventory_service._locked_rows) as locked:
            updated = inventory_service.update_admin_inventory(self.db, self.rows[0].id, RoomInventoryUpdate(total_inventory=7), self.admin)
        self.assertTrue(locked.called)
        self.assertEqual(updated.confirmed_inventory, 3)
        self.assertEqual(updated.held_inventory, 2)
        self.assertEqual(updated.blocked_inventory, 1)
        self.assertEqual(updated.available_inventory, 1)
        audit = self.db.scalar(select(AuditLog).where(AuditLog.action == "ROOM_INVENTORY_UPDATED"))
        self.assertEqual(audit.actor_user_id, self.admin.id)
        self.assertEqual(audit.previous_value["confirmed_inventory"], 3)
        self.assertEqual(audit.new_value["held_inventory"], 2)

    def test_legacy_available_write_cannot_bypass_commitments(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            inventory_service.update_admin_inventory(self.db, self.rows[0].id, RoomInventoryUpdate(total_inventory=4, available_inventory=4), self.admin)
        self.assertEqual(raised.exception.status_code, 409)
        self.db.rollback()

    def test_admin_and_partner_share_capacity_calculation(self) -> None:
        admin_updated = inventory_service.update_admin_inventory(self.db, self.rows[0].id, RoomInventoryUpdate(total_inventory=8, blocked_inventory=0), self.admin)
        self.assertEqual(admin_updated.available_inventory, 3)
        partner_updated = inventory_service.update_partner_range(self.db, self.room, PartnerInventoryRangeUpdate(start_date=self.mixed_day, end_date=self.mixed_day, total_inventory=8, blocked_inventory=0))
        self.assertEqual(partner_updated[0].available_inventory, 3)
        self.assertEqual(partner_updated[0].confirmed_inventory, 3)
        self.assertEqual(partner_updated[0].held_inventory, 2)

    def test_property_type_contract_uses_backend_homestay_value(self) -> None:
        self.assertEqual(PropertyType.HOMESTAY.value, "HOMESTAY")
        with self.assertRaises(ValueError):
            PropertyType("GUEST_HOUSE")


if __name__ == "__main__":
    unittest.main()
