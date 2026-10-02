import unittest
import uuid
import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.services import auth_security_service
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, BookingTraveller, Cancellation, Payment, PaymentWebhookEvent, Refund, RefundStatus
from app.models.hotel import BookingGatewayStatus, Hotel, HotelPolicy, HotelStatus, InventoryHold, PropertyType, RoomInventory, RoomType, RoomTypeStatus
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.settlement import Settlement, SettlementAdjustment, SettlementEvent, SettlementStatus
from app.schemas.booking import BookingCreate, InventoryHoldCreate
from app.services import booking_service, cancellation_service, payment_service, refund_execution_service
from tests.test_auth_integration import _asgi_request, request_json


class CancellationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suffix = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            cls.customer = User(full_name="Cancellation Customer", email=f"cancel-{suffix}@example.com", phone=f"+919{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.USER)
            cls.admin = User(full_name="Cancellation Admin", email=f"cancel-admin-{suffix}@example.com", phone=f"+918{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.ADMIN)
            hotel = Hotel(name="Cancellation Hotel", slug=f"cancellation-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4.0"), status=HotelStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Cancellation Lane", city="Goa", state="Goa", country="India", postal_code="403001", check_in_time=time(14), check_out_time=time(11))
            db.add_all([cls.customer, cls.admin, hotel]); db.flush(); hotel.policy = HotelPolicy(cancellation_policy="Free cancellation until 24 hours before arrival.")
            db.add(HotelVerification(hotel_id=hotel.id, business_name=hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED))
            room = RoomType(hotel_id=hotel.id, name="Cancellation Suite", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("3000.00"), currency="INR", total_rooms=5, is_active=True, status=RoomTypeStatus.BOOKABLE)
            db.add(room); db.flush()
            cls.customer_id, cls.admin_id, cls.hotel_id, cls.room_id = cls.customer.id, cls.admin.id, hotel.id, room.id
            for day in range(6): db.add(RoomInventory(room_type_id=room.id, inventory_date=date(2026, 12, 20) + timedelta(days=day), total_inventory=5, available_inventory=5, blocked_inventory=0, price=Decimal("3000.00"), is_closed=False))
            db.commit()

    @classmethod
    def tearDownClass(cls):
        with SessionLocal() as db:
            booking_ids = list(db.scalars(select(Booking.id).where(Booking.user_id == cls.customer_id))); cancellation_ids = list(db.scalars(select(Cancellation.id).where(Cancellation.booking_id.in_(booking_ids)))) if booking_ids else []; payment_ids = list(db.scalars(select(Payment.id).where(Payment.booking_id.in_(booking_ids)))) if booking_ids else []
            settlement_ids = list(db.scalars(select(Settlement.id).where(Settlement.booking_id.in_(booking_ids)))) if booking_ids else []
            if settlement_ids: db.execute(delete(SettlementAdjustment).where(SettlementAdjustment.settlement_id.in_(settlement_ids))); db.execute(delete(SettlementEvent).where(SettlementEvent.settlement_id.in_(settlement_ids))); db.execute(delete(Settlement).where(Settlement.id.in_(settlement_ids)))
            if cancellation_ids: db.execute(delete(Refund).where(Refund.cancellation_id.in_(cancellation_ids)))
            if payment_ids: db.execute(delete(PaymentWebhookEvent).where(PaymentWebhookEvent.payment_id.in_(payment_ids)))
            if booking_ids: db.execute(delete(Cancellation).where(Cancellation.booking_id.in_(booking_ids))); db.execute(delete(Payment).where(Payment.booking_id.in_(booking_ids))); db.execute(delete(BookingStatusHistory).where(BookingStatusHistory.booking_id.in_(booking_ids))); db.execute(delete(BookingTraveller).where(BookingTraveller.booking_id.in_(booking_ids))); db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))
            db.execute(delete(InventoryHold).where(InventoryHold.room_type_id == cls.room_id)); db.execute(delete(RoomInventory).where(RoomInventory.room_type_id == cls.room_id)); db.execute(delete(HotelPolicy).where(HotelPolicy.hotel_id == cls.hotel_id)); db.execute(delete(HotelVerification).where(HotelVerification.hotel_id == cls.hotel_id)); db.execute(delete(RoomType).where(RoomType.id == cls.room_id)); db.execute(delete(Hotel).where(Hotel.id == cls.hotel_id)); db.execute(delete(User).where(User.id.in_([cls.customer_id, cls.admin_id]))); db.commit()

    def _confirmed_booking(self, db, day: date, ambiguous: bool = False):
        stay = InventoryHoldCreate(hotel_id=self.hotel_id, room_type_id=self.room_id, check_in=day, check_out=day + timedelta(days=1), rooms=1, adults=1, children=0)
        hold = booking_service.create_inventory_hold(db, self.customer, stay)
        booking = booking_service.create_booking(db, self.customer, BookingCreate(**stay.model_dump(), hold_token=hold.hold_token, idempotency_key=uuid.uuid4().hex, travellers=[{"full_name": "Cancellation Customer", "age": 30, "is_primary": True}]))
        if ambiguous: booking.policy_snapshot = {"cancellation_policy": "Contact the hotel for cancellation terms."}; db.commit()
        payment = payment_service.create_order(db, self.customer, booking.id)
        payment_service.process_webhook(db, payment.provider, uuid.uuid4().hex, payment.provider_order_id, "succeeded", payment.amount, payment.currency, uuid.uuid4().hex)
        return db.get(Booking, booking.id)

    def test_customer_policy_refund_manual_exception_and_hotel_flow(self):
        with SessionLocal() as db:
            booking = self._confirmed_booking(db, date(2026, 12, 20))
            before = db.scalar(select(RoomInventory.available_inventory).where(RoomInventory.room_type_id == self.room_id, RoomInventory.inventory_date == booking.check_in))
            cancellation = cancellation_service.request_customer_cancellation(db, self.customer, booking.id, "Plans changed")
            self.assertEqual(cancellation.refundable_amount, booking.total_amount); self.assertEqual(cancellation.status.value, "REFUND_PENDING"); self.assertEqual(len(cancellation.refunds), 1)
            after = db.scalar(select(RoomInventory.available_inventory).where(RoomInventory.room_type_id == self.room_id, RoomInventory.inventory_date == booking.check_in)); self.assertEqual(after, before + 1)
            refund = cancellation.refunds[0]
            self.assertEqual(refund.status, RefundStatus.PROCESSING)
            settled = refund_execution_service.process_webhook(db, refund.provider, uuid.uuid4().hex, refund.provider_refund_id, "completed", refund.amount, refund.currency)
            self.assertEqual(settled.status, RefundStatus.SUCCEEDED); self.assertEqual(db.get(Booking, booking.id).status, BookingStatus.REFUNDED)
            with self.assertRaises(HTTPException): cancellation_service.settle_refund(db, self.admin, refund.id, RefundStatus.SUCCEEDED)

            manual_booking = self._confirmed_booking(db, date(2026, 12, 21), ambiguous=True)
            manual = cancellation_service.request_customer_cancellation(db, self.customer, manual_booking.id, "Need cancellation")
            self.assertTrue(manual.requires_manual_review); self.assertEqual(manual.status.value, "MANUAL_REVIEW"); self.assertEqual(manual.refunds, [])
            with self.assertRaises(HTTPException):
                cancellation_service.approve_manual_refund(db, self.admin, manual.id, manual_booking.total_amount + Decimal("1.00"), "Invalid over-refund")
            db.rollback()
            decided = cancellation_service.approve_manual_refund(db, self.admin, manual.id, Decimal("1000.00"), "Goodwill exception approved")
            self.assertEqual(decided.refundable_amount, Decimal("1000.00")); self.assertEqual(decided.refunds[0].status, RefundStatus.PROCESSING)

            hotel_booking = self._confirmed_booking(db, date(2026, 12, 22))
            hotel_cancellation = cancellation_service.create_hotel_caused_cancellation(db, self.admin, hotel_booking.id, "Property closed unexpectedly")
            self.assertEqual(hotel_cancellation.cancellation_type.value, "HOTEL_CAUSED"); self.assertEqual(hotel_cancellation.refundable_amount, hotel_booking.total_amount)

    def test_refund_callbacks_reconciliation_snapshot_and_idempotency(self):
        with SessionLocal() as db:
            booking = self._confirmed_booking(db, date(2026, 12, 23))
            captured_policy = booking.policy_snapshot["cancellation_policy"]
            hotel_policy = db.scalar(select(HotelPolicy).where(HotelPolicy.hotel_id == self.hotel_id))
            hotel_policy.cancellation_policy = "This current policy is non-refundable."
            db.commit()
            before = db.scalar(select(RoomInventory.available_inventory).where(RoomInventory.room_type_id == self.room_id, RoomInventory.inventory_date == booking.check_in))
            cancellation = cancellation_service.request_customer_cancellation(db, self.customer, booking.id, "Snapshot policy test")
            self.assertEqual(cancellation.policy_snapshot["cancellation_policy"], captured_policy)
            self.assertEqual(cancellation.refundable_amount, booking.total_amount)
            after = db.scalar(select(RoomInventory.available_inventory).where(RoomInventory.room_type_id == self.room_id, RoomInventory.inventory_date == booking.check_in))
            self.assertEqual(after, before + 1)
            with self.assertRaises(HTTPException):
                cancellation_service.request_customer_cancellation(db, self.customer, booking.id, "Double click")
            db.rollback()
            refund = db.get(Refund, cancellation.refunds[0].id)
            detail = refund_execution_service.admin_detail(db, refund.id)
            self.assertEqual(detail.customer_id, self.customer.id)
            customer_token, _ = auth_security_service.create_session_tokens(db, self.customer)
            forbidden_status, _ = request_json("POST", f"/admin/control/refunds/{refund.id}/action", {"action": "MANUAL_REVIEW", "reason": "Customer cannot manage refund state"}, customer_token)
            self.assertEqual(forbidden_status, 403)
            raw_callback = json.dumps({"event_id": uuid.uuid4().hex, "provider_refund_id": refund.provider_refund_id, "outcome": "completed", "amount": str(refund.amount), "currency": refund.currency}).encode()
            callback_status, _, _ = _asgi_request("POST", f"/bookings/payments/refunds/webhooks/{refund.provider}", raw_callback, {"Content-Type": "application/json", "X-Vayora-Signature": "invalid"})
            self.assertEqual(callback_status, 401)
            event_id = uuid.uuid4().hex
            pending = refund_execution_service.process_webhook(db, refund.provider, event_id, refund.provider_refund_id, "pending", refund.amount, refund.currency)
            self.assertEqual(pending.status, RefundStatus.PROCESSING)
            duplicate = refund_execution_service.process_webhook(db, refund.provider, event_id, refund.provider_refund_id, "completed", refund.amount, refund.currency)
            self.assertEqual(duplicate.status, RefundStatus.PROCESSING)
            pending.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1); db.commit()
            with patch("app.services.payment_provider.SandboxHmacProvider.fetch_refund_status", return_value="completed"):
                refund_execution_service.run_due(db)
                refund_execution_service.run_due(db)
                completed = db.get(Refund, refund.id)
            self.assertEqual(completed.status, RefundStatus.SUCCEEDED)
            self.assertEqual(completed.cancellation.refunded_amount, refund.amount)
            db.refresh(db.scalar(select(RoomInventory).where(RoomInventory.room_type_id == self.room_id, RoomInventory.inventory_date == booking.check_in)))

            outsider = User(full_name="Other Refund Customer", email=f"refund-other-{uuid.uuid4().hex}@example.com", phone=f"+917{str(uuid.uuid4().int)[-9:]}", password_hash="x", role=UserRole.CUSTOMER)
            db.add(outsider); db.commit()
            with self.assertRaises(HTTPException) as hidden:
                cancellation_service.get_cancellation(db, booking.id, outsider)
            self.assertEqual(hidden.exception.status_code, 404)
            db.delete(outsider); db.commit()
            hotel_policy.cancellation_policy = "Free cancellation until 24 hours before arrival."
            db.commit()

    def test_provider_failure_and_settlement_refund_impacts(self):
        with SessionLocal() as db:
            pre = self._confirmed_booking(db, date(2026, 12, 24))
            eligible = Settlement(hotel_id=pre.hotel_id, booking_id=pre.id, currency=pre.currency, gross_amount=pre.total_amount, vayora_fee=Decimal("0"), refund_deductions=Decimal("0"), adjustment_total=Decimal("0"), net_payable=pre.total_amount, eligibility_date=datetime.now(timezone.utc), status=SettlementStatus.ELIGIBLE)
            db.add(eligible); db.commit()
            pre_cancel = cancellation_service.request_customer_cancellation(db, self.customer, pre.id, "Refund before payout")
            pre_refund = pre_cancel.refunds[0]
            refund_execution_service.process_webhook(db, pre_refund.provider, uuid.uuid4().hex, pre_refund.provider_refund_id, "completed", pre_refund.amount, pre_refund.currency)
            db.refresh(eligible)
            self.assertEqual(eligible.refund_deductions, pre_refund.amount)
            self.assertEqual(eligible.net_payable, Decimal("0.00"))

            post = self._confirmed_booking(db, date(2026, 12, 25))
            settled = Settlement(hotel_id=post.hotel_id, booking_id=post.id, currency=post.currency, gross_amount=post.total_amount, vayora_fee=Decimal("0"), refund_deductions=Decimal("0"), adjustment_total=Decimal("0"), net_payable=post.total_amount, eligibility_date=datetime.now(timezone.utc), status=SettlementStatus.SETTLED, payout_provider="BANK", payout_provider_reference=f"utr-{uuid.uuid4().hex}", settled_at=datetime.now(timezone.utc))
            db.add(settled); db.commit()
            post_cancel = cancellation_service.request_customer_cancellation(db, self.customer, post.id, "Refund after payout")
            post_refund = post_cancel.refunds[0]
            failed = refund_execution_service.process_webhook(db, post_refund.provider, uuid.uuid4().hex, post_refund.provider_refund_id, "failed", post_refund.amount, post_refund.currency, "Provider temporarily rejected")
            self.assertEqual(failed.status, RefundStatus.FAILED)
            with patch("app.services.payment_provider.SandboxHmacProvider.fetch_refund_status", return_value="completed"):
                refund_execution_service.reconcile_refund(db, post_refund.id, admin=self.admin, reason="Provider now confirms completion")
                refund_execution_service.reconcile_refund(db, post_refund.id, admin=self.admin, reason="Duplicate reconciliation is safe")
            reversals = list(db.scalars(select(SettlementAdjustment).where(SettlementAdjustment.settlement_id == settled.id)))
            self.assertEqual(len(reversals), 1)
            self.assertEqual(reversals[0].amount, -post_refund.amount)
            audit = db.scalar(select(AuditLog).where(AuditLog.action == "REFUND_RECONCILED", AuditLog.target_id == str(post_refund.id)))
            self.assertIsNotNone(audit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
