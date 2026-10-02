import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.permission import require_hotel_partner_only
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.booking import (
    Booking,
    BookingStatus,
    BookingStatusHistory,
    BookingTraveller,
    Cancellation,
    CancellationStatus,
    CancellationType,
    Payment,
    PaymentWebhookEvent,
)
from app.models.hotel import BookingGatewayStatus, Hotel, HotelPolicy, HotelStatus, InventoryHold, PropertyType, RoomInventory, RoomType, RoomTypeStatus
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, InventoryHoldCreate, OperationBookingResponse
from app.services import booking_service, hotel_operations_service, payment_service


class HotelOperationsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            cls.customer = User(full_name="Operations Guest", email=f"ops-guest-{suffix}@example.com", phone=f"+919{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.CUSTOMER)
            cls.partner = User(full_name="Operations Partner", email=f"ops-partner-{suffix}@example.com", phone=f"+918{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            cls.other_partner = User(full_name="Other Partner", email=f"ops-other-{suffix}@example.com", phone=f"+917{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            cls.customer_actor = User(full_name="Unauthorized Customer", email=f"ops-auth-{suffix}@example.com", phone=f"+916{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.CUSTOMER)
            hotel = Hotel(name="Operations Hotel", slug=f"operations-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=None, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Ops Street", city="Goa", state="Goa", country="India", postal_code="403001", check_in_time=time(14), check_out_time=time(11))
            other_hotel = Hotel(name="Other Operations Hotel", slug=f"operations-other-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=None, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="2 Ops Street", city="Goa", state="Goa", country="India", postal_code="403002", check_in_time=time(14), check_out_time=time(11))
            db.add_all([cls.customer, cls.partner, cls.other_partner, cls.customer_actor, hotel, other_hotel]); db.flush(); hotel.partner_id = cls.partner.id; other_hotel.partner_id = cls.other_partner.id
            db.add_all([
                HotelVerification(hotel_id=hotel.id, business_name=hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED),
                HotelVerification(hotel_id=other_hotel.id, business_name=other_hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED),
                HotelPolicy(hotel_id=hotel.id, cancellation_policy="Current hotel policy offers a full refund."),
            ])
            room = RoomType(hotel_id=hotel.id, name="Operations Room", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("2000"), currency="INR", total_rooms=5, is_active=True, status=RoomTypeStatus.BOOKABLE); db.add(room); db.flush()
            cls.customer_id, cls.partner_id, cls.other_partner_id, cls.customer_actor_id = cls.customer.id, cls.partner.id, cls.other_partner.id, cls.customer_actor.id
            cls.hotel_id, cls.other_hotel_id, cls.room_id = hotel.id, other_hotel.id, room.id
            for offset in range(31):
                db.add(RoomInventory(room_type_id=room.id, inventory_date=date(2026, 12, 1) + timedelta(days=offset), total_inventory=5, available_inventory=5, blocked_inventory=0, price=Decimal("2000"), is_closed=False))
            db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            ids = list(db.scalars(select(Booking.id).where(Booking.user_id == cls.customer_id))); pids = list(db.scalars(select(Payment.id).where(Payment.booking_id.in_(ids)))) if ids else []
            if pids: db.execute(delete(PaymentWebhookEvent).where(PaymentWebhookEvent.payment_id.in_(pids)))
            if ids: db.execute(delete(Payment).where(Payment.booking_id.in_(ids))); db.execute(delete(Cancellation).where(Cancellation.booking_id.in_(ids))); db.execute(delete(BookingStatusHistory).where(BookingStatusHistory.booking_id.in_(ids))); db.execute(delete(BookingTraveller).where(BookingTraveller.booking_id.in_(ids))); db.execute(delete(Booking).where(Booking.id.in_(ids)))
            db.execute(delete(InventoryHold).where(InventoryHold.room_type_id == cls.room_id)); db.execute(delete(RoomInventory).where(RoomInventory.room_type_id == cls.room_id)); db.execute(delete(HotelVerification).where(HotelVerification.hotel_id.in_([cls.hotel_id, cls.other_hotel_id]))); db.execute(delete(HotelPolicy).where(HotelPolicy.hotel_id.in_([cls.hotel_id, cls.other_hotel_id]))); db.execute(delete(RoomType).where(RoomType.id == cls.room_id)); db.execute(delete(Hotel).where(Hotel.id.in_([cls.hotel_id, cls.other_hotel_id]))); db.execute(delete(User).where(User.id.in_([cls.customer_id, cls.partner_id, cls.other_partner_id, cls.customer_actor_id]))); db.commit()

    def _confirmed(self, db, day: date, policy: str = "No-show is non-refundable.") -> Booking:
        stay = InventoryHoldCreate(hotel_id=self.hotel_id, room_type_id=self.room_id, check_in=day, check_out=day + timedelta(days=1), rooms=1, adults=1, children=0)
        hold = booking_service.create_inventory_hold(db, self.customer, stay)
        booking = booking_service.create_booking(db, self.customer, BookingCreate(**stay.model_dump(), hold_token=hold.hold_token, idempotency_key=uuid.uuid4().hex, travellers=[{"full_name": "Operations Guest", "age": 31, "is_primary": True}]))
        booking.policy_snapshot = {"cancellation_policy": policy}
        payment = payment_service.create_order(db, self.customer, booking.id)
        payment_service.process_webhook(db, payment.provider, uuid.uuid4().hex, payment.provider_order_id, "succeeded", payment.amount, payment.currency, uuid.uuid4().hex)
        return db.get(Booking, booking.id)

    def test_lookup_by_id_reference_and_qr_is_tenant_scoped(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 2))
            by_id = hotel_operations_service.lookup(db, self.partner, booking_id=booking.id)
            self.assertTrue(by_id.operation_qr_token)
            self.assertEqual(hotel_operations_service.lookup(db, self.partner, booking_reference=booking.booking_reference.lower()).id, booking.id)
            self.assertEqual(hotel_operations_service.lookup(db, self.partner, qr_token=by_id.operation_qr_token).id, booking.id)
            with self.assertRaises(HTTPException) as raised:
                hotel_operations_service.lookup(db, self.other_partner, booking_id=booking.id)
            self.assertEqual(raised.exception.status_code, 404)

    def test_valid_and_duplicate_check_in_with_room_assignment(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 3))
            checked_in_at = datetime(2026, 12, 3, 14, 5, tzinfo=timezone.utc)
            checked_in = hotel_operations_service.check_in(db, self.partner, booking.id, "A-101", now=checked_in_at)
            self.assertEqual(checked_in.status, BookingStatus.CHECKED_IN)
            self.assertEqual(checked_in.assigned_room, "A-101")
            self.assertEqual(checked_in.checked_in_at.replace(tzinfo=timezone.utc), checked_in_at)
            self.assertEqual(checked_in.status_history[-1].changed_by_user_id, self.partner_id)
            with self.assertRaises(HTTPException) as raised:
                hotel_operations_service.check_in(db, self.partner, booking.id, "A-102")
            self.assertEqual(raised.exception.status_code, 409)

    def test_check_in_issue_is_a_support_state_not_no_show(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 4))
            issue = hotel_operations_service.report_issue(db, self.partner, booking.id, "MISSING_OR_INVALID_ID", "Passport image is unreadable")
            self.assertEqual(issue.status, BookingStatus.CHECK_IN_ISSUE)
            self.assertIn("MISSING_OR_INVALID_ID", issue.status_history[-1].note)
            hotel_operations_service.run_fallbacks(db, self.partner, datetime(2026, 12, 6, tzinfo=timezone.utc))
            self.assertEqual(db.get(Booking, booking.id).status, BookingStatus.CHECK_IN_ISSUE)

    def test_valid_and_duplicate_checkout(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 5))
            hotel_operations_service.check_in(db, self.partner, booking.id, "B-202")
            checked_out_at = datetime(2026, 12, 6, 11, 10, tzinfo=timezone.utc)
            checked_out = hotel_operations_service.check_out(db, self.partner, booking.id, now=checked_out_at)
            self.assertEqual(checked_out.status, BookingStatus.CHECKED_OUT)
            self.assertEqual(checked_out.checked_out_at.replace(tzinfo=timezone.utc), checked_out_at)
            self.assertEqual(checked_out.status_history[-1].changed_by_user_id, self.partner_id)
            with self.assertRaises(HTTPException) as raised:
                hotel_operations_service.check_out(db, self.partner, booking.id)
            self.assertEqual(raised.exception.status_code, 409)

    def test_auto_checkout_uses_hotel_checkout_time_and_marks_platform(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 7))
            hotel_operations_service.check_in(db, self.partner, booking.id, "C-303")
            before_due = datetime(2026, 12, 8, 11 + settings.AUTO_CHECKOUT_GRACE_HOURS - 1, tzinfo=timezone.utc)
            self.assertNotIn(booking.id, [item.id for item in hotel_operations_service.run_fallbacks(db, self.partner, before_due)])
            after_due = datetime(2026, 12, 8, 11 + settings.AUTO_CHECKOUT_GRACE_HOURS, 1, tzinfo=timezone.utc)
            changed = hotel_operations_service.run_fallbacks(db, self.partner, after_due)
            self.assertIn(booking.id, [item.id for item in changed])
            auto_closed = db.get(Booking, booking.id)
            self.assertEqual(auto_closed.status, BookingStatus.CHECKED_OUT)
            self.assertIsNone(auto_closed.status_history[-1].changed_by_user_id)
            self.assertIn("Auto-closed by Maharashtra Tourist Places", auto_closed.status_history[-1].note)

    def test_manual_no_show_uses_snapshot_and_existing_financial_review(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 9), policy="No-show is non-refundable.")
            no_show = hotel_operations_service.report_no_show(db, self.partner, booking.id, now=datetime(2026, 12, 9, 15, tzinfo=timezone.utc))
            self.assertEqual(no_show.status, BookingStatus.NO_SHOW)
            self.assertEqual(no_show.status_history[-1].changed_by_user_id, self.partner_id)
            cancellation = db.scalar(select(Cancellation).where(Cancellation.booking_id == booking.id))
            self.assertEqual(cancellation.cancellation_type, CancellationType.NO_SHOW)
            self.assertEqual(cancellation.status, CancellationStatus.COMPLETED)
            self.assertEqual(cancellation.policy_snapshot["cancellation_policy"], "No-show is non-refundable.")

    def test_automatic_no_show_requires_reminder_opportunity_first(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 10), policy="Contact support for no-show implications.")
            first_run = datetime(2026, 12, 10, 14 + settings.NO_SHOW_FALLBACK_HOURS + 1, tzinfo=timezone.utc)
            changed = hotel_operations_service.run_fallbacks(db, self.partner, first_run)
            self.assertIn(booking.id, [item.id for item in changed])
            reminded = db.get(Booking, booking.id)
            self.assertEqual(reminded.status, BookingStatus.CONFIRMED)
            self.assertIn("hotel action requested", reminded.status_history[-1].note)
            second_run = first_run + timedelta(minutes=settings.NO_SHOW_REMINDER_OPPORTUNITY_MINUTES + 1)
            hotel_operations_service.run_fallbacks(db, self.partner, second_run)
            fallback = db.get(Booking, booking.id)
            self.assertEqual(fallback.status, BookingStatus.NO_SHOW)
            self.assertIsNone(fallback.status_history[-1].changed_by_user_id)
            self.assertTrue(fallback.cancellation.requires_manual_review)

    def test_automatic_no_show_quarantines_inconsistent_inventory_and_continues(self) -> None:
        with SessionLocal() as db:
            stay_date = date(2026, 12, 12)
            booking = self._confirmed(db, stay_date)
            db.execute(delete(RoomInventory).where(
                RoomInventory.room_type_id == self.room_id,
                RoomInventory.inventory_date == stay_date,
            ))
            db.commit()

            first_run = datetime(2026, 12, 12, 21, tzinfo=timezone.utc)
            hotel_operations_service.run_fallbacks(db, self.partner, first_run)
            second_run = first_run + timedelta(minutes=settings.NO_SHOW_REMINDER_OPPORTUNITY_MINUTES + 1)
            changed = hotel_operations_service.run_fallbacks(db, self.partner, second_run)

            self.assertIn(booking.id, [item.id for item in changed])
            quarantined = db.get(Booking, booking.id)
            self.assertEqual(quarantined.status, BookingStatus.CHECK_IN_ISSUE)
            self.assertIn("inventory ledger requires support review", quarantined.status_history[-1].note)

    def test_operations_board_and_response_expose_only_operational_fields(self) -> None:
        with SessionLocal() as db:
            booking = self._confirmed(db, date(2026, 12, 11))
            board = hotel_operations_service.list_board(db, self.partner, date(2026, 12, 11))
            self.assertIn(booking.id, [item.id for item in board["arrivals"]])
            response = OperationBookingResponse.from_booking(board["arrivals"][0]).model_dump()
            self.assertIn("primary_guest_name", response)
            self.assertNotIn("payments", response)
            self.assertNotIn("price_snapshot", response)
            self.assertNotIn("policy_snapshot", response)
            self.assertNotIn("email", response)
            self.assertNotIn("phone", response)

    def test_customer_is_rejected_by_partner_authorization(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            require_hotel_partner_only(self.customer_actor)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
