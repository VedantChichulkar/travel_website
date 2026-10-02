import unittest
import uuid
import json
import hashlib
from unittest.mock import patch
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.services import auth_security_service
from app.database import SessionLocal
from app.models.audit import AuditLog
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, BookingTraveller, Cancellation, Payment, PaymentReconciliationStatus, PaymentStatus, PaymentWebhookEvent, Refund, RefundStatus
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, InventoryHold, PropertyType, RoomInventory, RoomType, RoomTypeStatus
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, InventoryHoldCreate, PaymentWebhookPayload
from app.services import booking_service, payment_reconciliation_service, payment_service
from tests.test_auth_integration import _asgi_request, request_json


class PaymentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suffix = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            cls.user = User(full_name="Payment Customer", email=f"payment-{suffix}@example.com", phone=f"+919{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.USER)
            cls.admin = User(full_name="Payment Admin", email=f"payment-admin-{suffix}@example.com", phone=f"+918{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.ADMIN)
            hotel = Hotel(name="Payment Hotel", slug=f"payment-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4.0"), status=HotelStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Payment Lane", city="Goa", state="Goa", country="India", postal_code="403001", check_in_time=time(14), check_out_time=time(11))
            db.add_all([cls.user, cls.admin, hotel]); db.flush()
            db.add(HotelVerification(hotel_id=hotel.id, business_name=hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED))
            room = RoomType(hotel_id=hotel.id, name="Payment Suite", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("2500.00"), currency="INR", total_rooms=8, is_active=True, status=RoomTypeStatus.BOOKABLE)
            db.add(room); db.flush()
            cls.user_id, cls.admin_id, cls.hotel_id, cls.room_id = cls.user.id, cls.admin.id, hotel.id, room.id
            for day in range(4): db.add(RoomInventory(room_type_id=room.id, inventory_date=date(2026, 12, 26) + timedelta(days=day), total_inventory=8, available_inventory=8, blocked_inventory=0, price=Decimal("2500.00"), is_closed=False))
            db.commit()

    @classmethod
    def tearDownClass(cls):
        with SessionLocal() as db:
            booking_ids = list(db.scalars(select(Booking.id).where(Booking.user_id == cls.user_id)))
            payment_ids = list(db.scalars(select(Payment.id).where(Payment.booking_id.in_(booking_ids)))) if booking_ids else []
            cancellation_ids = list(db.scalars(select(Cancellation.id).where(Cancellation.booking_id.in_(booking_ids)))) if booking_ids else []
            if payment_ids: db.execute(delete(PaymentWebhookEvent).where(PaymentWebhookEvent.payment_id.in_(payment_ids)))
            if booking_ids:
                if cancellation_ids: db.execute(delete(Refund).where(Refund.cancellation_id.in_(cancellation_ids))); db.execute(delete(Cancellation).where(Cancellation.id.in_(cancellation_ids)))
                db.execute(delete(Payment).where(Payment.booking_id.in_(booking_ids))); db.execute(delete(BookingStatusHistory).where(BookingStatusHistory.booking_id.in_(booking_ids))); db.execute(delete(BookingTraveller).where(BookingTraveller.booking_id.in_(booking_ids))); db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))
            db.execute(delete(InventoryHold).where(InventoryHold.room_type_id == cls.room_id)); db.execute(delete(RoomInventory).where(RoomInventory.room_type_id == cls.room_id)); db.execute(delete(HotelVerification).where(HotelVerification.hotel_id == cls.hotel_id)); db.execute(delete(RoomType).where(RoomType.id == cls.room_id)); db.execute(delete(Hotel).where(Hotel.id == cls.hotel_id)); db.execute(delete(User).where(User.id.in_((cls.user_id, cls.admin_id)))); db.commit()

    def _booking(self, db, check_in: date):
        stay = InventoryHoldCreate(hotel_id=self.hotel_id, room_type_id=self.room_id, check_in=check_in, check_out=check_in + timedelta(days=1), rooms=1, adults=1, children=0)
        hold = booking_service.create_inventory_hold(db, self.user, stay)
        created = booking_service.create_booking(db, self.user, BookingCreate(**stay.model_dump(), hold_token=hold.hold_token, idempotency_key=uuid.uuid4().hex, travellers=[{"full_name": "Payment Customer", "age": 30, "is_primary": True}]))
        return created

    def test_success_duplicate_failure_retry_and_reconciliation(self):
        with SessionLocal() as db:
            first = self._booking(db, date(2026, 12, 26)); payment = payment_service.create_order(db, self.user, first.id)
            self.assertEqual(payment.status, PaymentStatus.PENDING)
            success_event = f"evt-success-{uuid.uuid4().hex}"
            provider_payment_id = f"provider-payment-{uuid.uuid4().hex}"
            paid = payment_service.process_webhook(db, payment.provider, success_event, payment.provider_order_id, "succeeded", payment.amount, payment.currency, provider_payment_id)
            self.assertEqual(paid.status, PaymentStatus.PAID); self.assertEqual(paid.reconciliation_status, PaymentReconciliationStatus.RESOLVED)
            confirmed = db.get(Booking, first.id); self.assertEqual(confirmed.status, BookingStatus.CONFIRMED)
            duplicate = payment_service.process_webhook(db, payment.provider, success_event, payment.provider_order_id, "succeeded", payment.amount, payment.currency, provider_payment_id)
            self.assertEqual(duplicate.id, payment.id)
            self.assertEqual(len(list(db.scalars(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider_event_id == success_event)))), 1)

            second = self._booking(db, date(2026, 12, 27)); failed = payment_service.create_order(db, self.user, second.id)
            payment_service.process_webhook(db, failed.provider, f"evt-failed-{uuid.uuid4().hex}", failed.provider_order_id, "failed", failed.amount, failed.currency, failure_reason="declined")
            self.assertEqual(db.get(Booking, second.id).status, BookingStatus.PAYMENT_PENDING)
            retry = payment_service.create_order(db, self.user, second.id); self.assertNotEqual(retry.id, failed.id)

            third = self._booking(db, date(2026, 12, 28)); reconcile = payment_service.create_order(db, self.user, third.id)
            hold = db.scalar(select(InventoryHold).where(InventoryHold.hold_token == third.hold_token)); hold.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1); db.commit()
            result = payment_service.process_webhook(db, reconcile.provider, f"evt-reconcile-{uuid.uuid4().hex}", reconcile.provider_order_id, "succeeded", reconcile.amount, reconcile.currency, f"provider-payment-{uuid.uuid4().hex}")
            self.assertEqual(result.status, PaymentStatus.PAID); self.assertEqual(result.reconciliation_status, PaymentReconciliationStatus.REFUND_REQUIRED)
            self.assertEqual(db.get(Booking, third.id).status, BookingStatus.REFUND_PENDING)
            reconciliation_cancellation = db.scalar(select(Cancellation).where(Cancellation.booking_id == third.id))
            self.assertEqual(reconciliation_cancellation.cancellation_type.value, "PAYMENT_RECONCILIATION")
            refunds = list(db.scalars(select(Refund).where(Refund.cancellation_id == reconciliation_cancellation.id)))
            self.assertEqual(len(refunds), 1); self.assertEqual(refunds[0].status, RefundStatus.PROCESSING)

    def test_reconciliation_retry_history_visibility_and_audit(self):
        with SessionLocal() as db:
            booking = self._booking(db, date(2026, 12, 29))
            payment = payment_service.create_order(db, self.user, booking.id)
            self.assertEqual(payment.amount, booking.total_amount)
            self.assertEqual(payment.currency, booking.currency)
            transient_reference = f"provider-payment-{uuid.uuid4().hex}"
            with patch("app.services.payment_reconciliation_service.inventory_service.finalize_hold_as_confirmed", side_effect=RuntimeError("temporary lock contention")):
                pending = payment_service.process_webhook(db, payment.provider, f"evt-transient-{uuid.uuid4().hex}", payment.provider_order_id, "succeeded", payment.amount, payment.currency, transient_reference)
            self.assertEqual(pending.reconciliation_status, PaymentReconciliationStatus.CONFIRMATION_REQUIRED)
            resolved = payment_reconciliation_service.attempt_confirmation(db, payment.id, admin=self.admin, reason="Inventory lock cleared; retry verified payment confirmation")
            self.assertEqual(resolved.reconciliation_status, PaymentReconciliationStatus.RESOLVED)
            self.assertEqual(db.get(Booking, booking.id).status, BookingStatus.CONFIRMED)
            inventory = db.scalar(select(RoomInventory).where(RoomInventory.room_type_id == self.room_id, RoomInventory.inventory_date == date(2026, 12, 29)))
            self.assertEqual(inventory.confirmed_inventory, 1)
            again = payment_reconciliation_service.attempt_confirmation(db, payment.id, admin=self.admin, reason="Idempotency verification")
            self.assertEqual(again.reconciliation_status, PaymentReconciliationStatus.RESOLVED)
            db.refresh(inventory); self.assertEqual(inventory.confirmed_inventory, 1)

            history = payment_service.list_customer_payment_history(db, self.user)
            self.assertTrue(any(item.id == payment.id and item.booking_reference == booking.booking_reference for item in history))
            receipt = payment_service.receipt(db, self.user, booking.id, payment.id)
            self.assertEqual(receipt.payment_reference, transient_reference)
            detail = payment_service.admin_detail(db, payment.id)
            self.assertEqual(detail.customer_id, self.user.id); self.assertEqual(detail.expected_amount, payment.amount)
            audit = db.scalar(select(AuditLog).where(AuditLog.action == "PAYMENT_RECONCILIATION_CONFIRMED", AuditLog.target_id == str(payment.id)))
            self.assertIsNotNone(audit)

            outsider = User(full_name="Other Customer", email=f"other-{uuid.uuid4().hex}@example.com", phone=f"+917{str(uuid.uuid4().int)[-9:]}", password_hash="x", role=UserRole.CUSTOMER)
            db.add(outsider); db.commit()
            self.assertFalse(payment_service.list_customer_payment_history(db, outsider))
            db.delete(outsider); db.commit()

    def test_callback_validation_and_server_authoritative_order(self):
        with SessionLocal() as db:
            booking = self._booking(db, date(2026, 12, 26))
            payment = payment_service.create_order(db, self.user, booking.id)
            reused = payment_service.create_order(db, self.user, booking.id)
            self.assertEqual(reused.id, payment.id)
            self.assertEqual(payment.amount, Decimal(str(booking.price_snapshot["total_amount"])))
            self.assertFalse(payment_service.verify_webhook_signature(b"{}", "invalid"))
            callback = json.dumps({"event_id": f"evt-invalid-{uuid.uuid4().hex}", "provider_order_id": payment.provider_order_id, "outcome": "succeeded", "amount": str(payment.amount), "currency": payment.currency, "provider_payment_id": f"provider-payment-{uuid.uuid4().hex}"}).encode()
            callback_status, _, _ = _asgi_request("POST", f"/bookings/payments/webhooks/{payment.provider}", callback, {"Content-Type": "application/json", "X-Vayora-Signature": "invalid"})
            self.assertEqual(callback_status, 401)
            customer_token, _ = auth_security_service.create_session_tokens(db, self.user)
            response_status, _ = request_json("POST", f"/admin/control/payments/{payment.id}/reconciliation", {"action": "MANUAL_REVIEW", "reason": "Customer must not classify payments"}, customer_token)
            self.assertEqual(response_status, 403)
            with self.assertRaises(ValidationError):
                PaymentWebhookPayload(event_id="missing-reference", provider_order_id=payment.provider_order_id, outcome="succeeded", amount=payment.amount, currency=payment.currency)
            mismatch = payment_service.process_webhook(db, payment.provider, f"evt-amount-{uuid.uuid4().hex}", payment.provider_order_id, "succeeded", payment.amount + Decimal("1.00"), payment.currency, "provider-payment-mismatch")
            self.assertEqual(mismatch.status, PaymentStatus.FAILED)
            currency_booking = self._booking(db, date(2026, 12, 27))
            currency_payment = payment_service.create_order(db, self.user, currency_booking.id)
            currency_mismatch = payment_service.process_webhook(db, currency_payment.provider, f"evt-currency-{uuid.uuid4().hex}", currency_payment.provider_order_id, "succeeded", currency_payment.amount, "USD", f"provider-payment-{uuid.uuid4().hex}")
            self.assertEqual(currency_mismatch.status, PaymentStatus.FAILED)
            with self.assertRaises(HTTPException) as raised:
                payment_service.create_order(db, self.user, 999999999)
            self.assertEqual(raised.exception.status_code, 404)

    def test_razorpay_captured_webhook_is_normalized_and_replay_safe(self):
        with SessionLocal() as db:
            booking = self._booking(db, date(2026, 12, 26))
            payment = payment_service.create_order(db, self.user, booking.id)
            payment.provider = "RAZORPAY"
            payment.provider_order_id = f"order_{uuid.uuid4().hex}"
            db.commit()
            raw = json.dumps({
                "event": "payment.captured",
                "payload": {"payment": {"entity": {
                    "id": f"pay_{uuid.uuid4().hex}", "order_id": payment.provider_order_id,
                    "status": "captured", "amount": int(payment.amount * 100), "currency": payment.currency,
                }}},
            }, separators=(",", ":")).encode()
            first = payment_service.process_razorpay_payment_webhook(db, raw)
            second = payment_service.process_razorpay_payment_webhook(db, raw)
            self.assertEqual(first.id, payment.id)
            self.assertEqual(second.id, payment.id)
            self.assertEqual(db.get(Booking, booking.id).status, BookingStatus.CONFIRMED)
            event_id = f"rzp:{hashlib.sha256(raw).hexdigest()}"
            self.assertEqual(len(list(db.scalars(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider_event_id == event_id)))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
