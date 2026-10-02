import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.core.security import hash_password
from app.core.config import settings
from app.core.permission import require_hotel_partner_only
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus, BookingStatusHistory, Cancellation, CancellationStatus, CancellationType, Payment, PaymentStatus, Refund, RefundStatus, SettlementImpactStatus
from app.models.communication import Conversation, ConversationKind, ConversationStatus
from app.models.audit import AuditLog
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, PropertyType, RoomType
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.settlement import Payout, PayoutStatus, PayoutWebhookEvent, Settlement, SettlementAdjustment, SettlementAdjustmentKind, SettlementEvent, SettlementStatus
from app.models.user import User, UserRole
from app.services import payout_provider, payout_service, settlement_service
from app.services.payout_provider import ProviderOutcomeUnknown, ProviderPayout, ProviderPayoutEvent
from app.schemas.settlement import PartnerSettlementResponse, SettlementResponse


class FakePayoutProvider:
    name = "TEST_PAYOUT"

    def __init__(self) -> None:
        self.reference_prefix = uuid.uuid4().hex
        self.state = "processing"
        self.creates = 0
        self.amount = Decimal("0")
        self.currency = "INR"
        self.create_exception = None
        self.lookup_result = None
        self.destination = None

    def create_payout(self, *, destination, amount, currency, idempotency_key):
        del idempotency_key
        self.creates += 1
        self.destination = destination
        self.amount, self.currency = amount, currency
        if self.create_exception:
            raise self.create_exception
        return ProviderPayout(provider_payout_id=f"test-payout-{self.reference_prefix}-{self.creates}", status="processing", amount=amount, currency=currency)

    def fetch_payout(self, provider_payout_id):
        return ProviderPayout(provider_payout_id, self.state, self.amount, self.currency)

    def find_payout_by_reference(self, idempotency_key):
        del idempotency_key
        return self.lookup_result

    def verify_payout_callback(self, payload, signature):
        del payload
        return signature == "valid"

    def parse_payout_callback(self, payload, event_id):
        import json
        data = json.loads(payload)
        return ProviderPayoutEvent(event_id or data["event_id"], data["payout_reference"], data["status"], Decimal(data["amount"]), data["currency"])


class SettlementIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_commission_rate = settings.VAYORA_COMMISSION_RATE
        settings.VAYORA_COMMISSION_RATE = Decimal("0.10")
        suffix = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            customer = User(full_name="Settlement Guest", email=f"settle-guest-{suffix}@example.com", phone=f"+919{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.CUSTOMER)
            partner = User(full_name="Settlement Partner", email=f"settle-partner-{suffix}@example.com", phone=f"+918{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            other_partner = User(full_name="Other Settlement Partner", email=f"settle-other-{suffix}@example.com", phone=f"+917{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            admin = User(full_name="Settlement Admin", email=f"settle-admin-{suffix}@example.com", phone=f"+916{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.ADMIN)
            db.add_all([customer, partner, other_partner, admin]); db.flush()
            hotel = Hotel(name="Settlement Hotel", slug=f"settlement-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=partner.id, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Ledger Street", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
            other_hotel = Hotel(name="Other Settlement Hotel", slug=f"settlement-other-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=other_partner.id, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="2 Ledger Street", city="Pune", state="Maharashtra", country="India", postal_code="411002", check_in_time=time(14), check_out_time=time(11))
            db.add_all([hotel, other_hotel]); db.flush()
            room = RoomType(hotel_id=hotel.id, name="Ledger Room", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("1000"), currency="INR", total_rooms=2, is_active=True)
            db.add(room); db.flush()
            verification = HotelVerification(hotel_id=hotel.id, business_name="Settlement Hotel", business_type=BusinessType.PROPRIETORSHIP, bank_account_number="123456789012", bank_ifsc="HDFC0001234", bank_beneficiary_name="Settlement Hotel", verification_status=VerificationStatus.APPROVED)
            db.add(verification); db.flush()
            cls.customer_id, cls.partner_id, cls.other_partner_id, cls.admin_id = customer.id, partner.id, other_partner.id, admin.id
            cls.hotel_id, cls.other_hotel_id, cls.room_id = hotel.id, other_hotel.id, room.id
            db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            booking_ids = list(db.scalars(select(Booking.id).where(Booking.user_id == cls.customer_id)))
            settlement_ids = list(db.scalars(select(Settlement.id).where(Settlement.booking_id.in_(booking_ids)))) if booking_ids else []
            cancellation_ids = list(db.scalars(select(Cancellation.id).where(Cancellation.booking_id.in_(booking_ids)))) if booking_ids else []
            if settlement_ids:
                payout_ids = list(db.scalars(select(Payout.id).where(Payout.settlement_id.in_(settlement_ids))))
                if payout_ids:
                    db.execute(delete(PayoutWebhookEvent).where(PayoutWebhookEvent.payout_id.in_(payout_ids)))
                    db.execute(delete(Payout).where(Payout.id.in_(payout_ids)))
                db.execute(delete(SettlementEvent).where(SettlementEvent.settlement_id.in_(settlement_ids)))
                db.execute(delete(SettlementAdjustment).where(SettlementAdjustment.settlement_id.in_(settlement_ids)))
                db.execute(delete(Settlement).where(Settlement.id.in_(settlement_ids)))
            if cancellation_ids:
                db.execute(delete(Refund).where(Refund.cancellation_id.in_(cancellation_ids)))
                db.execute(delete(Cancellation).where(Cancellation.id.in_(cancellation_ids)))
            if booking_ids:
                db.execute(delete(Conversation).where(Conversation.booking_id.in_(booking_ids)))
                db.execute(delete(Payment).where(Payment.booking_id.in_(booking_ids)))
                db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))
            db.execute(delete(HotelVerification).where(HotelVerification.hotel_id == cls.hotel_id))
            db.execute(delete(RoomType).where(RoomType.id == cls.room_id))
            db.execute(delete(Hotel).where(Hotel.id.in_([cls.hotel_id, cls.other_hotel_id])))
            db.execute(delete(User).where(User.id.in_([cls.customer_id, cls.partner_id, cls.other_partner_id, cls.admin_id])))
            db.commit()
        settings.VAYORA_COMMISSION_RATE = cls.original_commission_rate

    def _completed(self, db, checkout_at: datetime, amount: Decimal = Decimal("1200.00")) -> Booking:
        booking = Booking(
            booking_reference=f"VYR-STL-{uuid.uuid4().hex[:12].upper()}", user_id=self.customer_id, hotel_id=self.hotel_id, room_type_id=self.room_id,
            check_in=date(2026, 8, 1), check_out=date(2026, 8, 2), rooms=1, adults=1, children=0, nights=1, currency="INR",
            subtotal=Decimal("1000.00"), taxes=Decimal("200.00"), platform_fee=Decimal("0.00"), discount=Decimal("0.00"), total_amount=amount,
            room_snapshot={}, price_snapshot={}, policy_snapshot={}, status=BookingStatus.CHECKED_OUT, payment_status=PaymentStatus.PAID, checked_out_at=checkout_at,
        )
        db.add(booking); db.flush()
        db.add(Payment(booking_id=booking.id, provider="VAYORA_GATEWAY", provider_order_id=f"order_{uuid.uuid4().hex}", provider_payment_id=f"pay_{uuid.uuid4().hex}", amount=amount, currency="INR", status=PaymentStatus.PAID))
        db.commit(); db.refresh(booking)
        return booking

    def _no_show(self, db, occurred_at: datetime, policy: str, *, manual: bool = False) -> Booking:
        booking = Booking(
            booking_reference=f"VYR-NS-{uuid.uuid4().hex[:12].upper()}", user_id=self.customer_id, hotel_id=self.hotel_id, room_type_id=self.room_id,
            check_in=occurred_at.date(), check_out=occurred_at.date() + timedelta(days=1), rooms=1, adults=1, children=0, nights=1, currency="INR",
            subtotal=Decimal("1000.00"), taxes=Decimal("200.00"), platform_fee=Decimal("0.00"), discount=Decimal("0.00"), total_amount=Decimal("1200.00"),
            room_snapshot={}, price_snapshot={}, policy_snapshot={"cancellation_policy": policy}, status=BookingStatus.NO_SHOW, payment_status=PaymentStatus.PAID,
        )
        booking.status_history.append(BookingStatusHistory(old_status=BookingStatus.CONFIRMED, new_status=BookingStatus.NO_SHOW, note="Finalized no-show", created_at=occurred_at))
        db.add(booking); db.flush()
        db.add(Payment(booking_id=booking.id, provider="VAYORA_GATEWAY", provider_order_id=f"order_{uuid.uuid4().hex}", provider_payment_id=f"pay_{uuid.uuid4().hex}", amount=booking.total_amount, currency="INR", status=PaymentStatus.PAID))
        db.add(Cancellation(
            booking_id=booking.id, cancellation_type=CancellationType.NO_SHOW,
            status=CancellationStatus.MANUAL_REVIEW if manual else CancellationStatus.COMPLETED,
            reason="Finalized no-show", policy_snapshot={**booking.policy_snapshot, "refund_decision": "Policy explicitly retains the full amount" if not manual else "Manual review required"},
            refundable_amount=Decimal("0"), refunded_amount=Decimal("0"), requires_manual_review=manual,
        ))
        db.commit(); db.refresh(booking)
        return booking

    def test_seven_day_eligibility_and_duplicate_prevention(self) -> None:
        with SessionLocal() as db:
            checkout = datetime(2026, 8, 2, 11, tzinfo=timezone.utc)
            booking = self._completed(db, checkout)
            self.assertEqual(settlement_service.refresh_due_settlements(db, checkout + timedelta(days=7) - timedelta(seconds=1)), [])
            created = settlement_service.refresh_due_settlements(db, checkout + timedelta(days=7))
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].status, SettlementStatus.ELIGIBLE)
            self.assertEqual(created[0].net_payable, Decimal("1080.00"))
            self.assertEqual(created[0].vayora_fee, Decimal("120.00"))
            self.assertEqual(created[0].commission_rate, Decimal("0.100000"))
            self.assertEqual(settlement_service.refresh_due_settlements(db, checkout + timedelta(days=8)), [])
            self.assertEqual(db.scalar(select(func.count()).select_from(Settlement).where(Settlement.booking_id == booking.id)), 1)

    def test_dispute_hold_and_refund_deduction(self) -> None:
        with SessionLocal() as db:
            due = datetime(2026, 8, 12, 11, tzinfo=timezone.utc)
            disputed = self._completed(db, due - timedelta(days=8))
            db.add(Cancellation(booking_id=disputed.id, cancellation_type=CancellationType.CUSTOMER, status=CancellationStatus.MANUAL_REVIEW, reason="Post-stay billing dispute", policy_snapshot={}, refundable_amount=Decimal("0"), refunded_amount=Decimal("0"), requires_manual_review=True))
            refunded = self._completed(db, due - timedelta(days=8))
            cancellation = Cancellation(booking_id=refunded.id, cancellation_type=CancellationType.CUSTOMER, status=CancellationStatus.COMPLETED, reason="Approved post-stay deduction", policy_snapshot={}, refundable_amount=Decimal("300"), refunded_amount=Decimal("300"), requires_manual_review=False)
            db.add(cancellation); db.flush()
            payment = db.scalar(select(Payment).where(Payment.booking_id == refunded.id))
            refund = Refund(cancellation_id=cancellation.id, payment_id=payment.id, amount=Decimal("300"), currency="INR", status=RefundStatus.SUCCEEDED, provider_refund_id=f"refund_{uuid.uuid4().hex}", settlement_impact_status=SettlementImpactStatus.PENDING)
            db.add(refund); db.commit()
            settlement_service.refresh_due_settlements(db, due)
            held = db.scalar(select(Settlement).where(Settlement.booking_id == disputed.id))
            deducted = db.scalar(select(Settlement).where(Settlement.booking_id == refunded.id))
            self.assertEqual(held.status, SettlementStatus.ON_HOLD)
            self.assertIn("review", held.hold_reason.lower())
            self.assertEqual(deducted.refund_deductions, Decimal("300.00"))
            self.assertEqual(deducted.net_payable, Decimal("810.00"))
            self.assertEqual(db.get(Refund, refund.id).settlement_impact_status, SettlementImpactStatus.RECORDED)

    def test_hotel_isolation_admin_hold_release_and_settled_immutability(self) -> None:
        with SessionLocal() as db:
            now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
            booking = self._completed(db, now - timedelta(days=8))
            settlement = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == booking.id)
            partner, other, admin = db.get(User, self.partner_id), db.get(User, self.other_partner_id), db.get(User, self.admin_id)
            customer = db.get(User, self.customer_id)
            with self.assertRaises(HTTPException) as forbidden:
                require_hotel_partner_only(customer)
            self.assertEqual(forbidden.exception.status_code, 403)
            self.assertEqual(settlement_service.get_partner(db, partner, settlement.id).booking_id, booking.id)
            with self.assertRaises(HTTPException) as hidden:
                settlement_service.get_partner(db, other, settlement.id)
            self.assertEqual(hidden.exception.status_code, 404)

            held = settlement_service.hold(db, admin, settlement.id, "Chargeback evidence review")
            self.assertEqual(held.status, SettlementStatus.ON_HOLD)
            released = settlement_service.release(db, admin, settlement.id)
            self.assertEqual(released.status, SettlementStatus.ELIGIBLE)
            released.status = SettlementStatus.SETTLED
            released.payout_provider = "VERIFIED_TEST_PROVIDER"
            released.payout_provider_reference = f"utr-{uuid.uuid4().hex}"
            released.settled_at = now
            db.commit(); db.refresh(released)
            settled = released
            original_net = settled.net_payable
            with self.assertRaises(HTTPException):
                settlement_service.hold(db, admin, settlement.id, "Cannot rewrite history")
            corrected = settlement_service.add_adjustment(db, admin, settlement.id, SettlementAdjustmentKind.REVERSAL, Decimal("-50.00"), "Post-payout correction")
            self.assertEqual(corrected.status, SettlementStatus.SETTLED)
            self.assertEqual(corrected.net_payable, original_net)
            self.assertFalse(corrected.adjustments[-1].applies_to_current_settlement)
            self.assertGreaterEqual(len(corrected.events), 4)
            corrected.net_payable = Decimal("1.00")
            with self.assertRaises(ValueError):
                db.commit()
            db.rollback()

    def test_no_show_uses_booking_snapshot_and_unresolved_cases_hold(self) -> None:
        with SessionLocal() as db:
            now = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
            valid = self._no_show(db, now - timedelta(days=8), "No-show is non-refundable.")
            ambiguous = self._no_show(db, now - timedelta(days=8), "Contact support for no-show implications.", manual=True)
            disputed = self._no_show(db, now - timedelta(days=8), "No-show is non-refundable.")
            db.add(Conversation(hotel_id=self.hotel_id, customer_id=self.customer_id, booking_id=disputed.id, subject="No-show disputed", kind=ConversationKind.DISPUTE, status=ConversationStatus.OPEN))
            db.commit()

            settlement_service.refresh_due_settlements(db, now)
            valid_settlement = db.scalar(select(Settlement).where(Settlement.booking_id == valid.id))
            ambiguous_settlement = db.scalar(select(Settlement).where(Settlement.booking_id == ambiguous.id))
            disputed_settlement = db.scalar(select(Settlement).where(Settlement.booking_id == disputed.id))
            self.assertEqual(valid_settlement.status, SettlementStatus.ELIGIBLE)
            self.assertEqual(valid_settlement.gross_amount, Decimal("1200.00"))
            self.assertEqual(valid_settlement.vayora_fee, Decimal("120.00"))
            self.assertEqual(valid_settlement.net_payable, valid_settlement.gross_amount - valid_settlement.vayora_fee + valid_settlement.adjustment_total)
            self.assertEqual(ambiguous_settlement.status, SettlementStatus.ON_HOLD)
            self.assertIn("review", ambiguous_settlement.hold_reason.lower())
            self.assertEqual(disputed_settlement.status, SettlementStatus.ON_HOLD)
            self.assertIn("dispute", disputed_settlement.hold_reason.lower())

    def test_commission_snapshot_and_future_adjustment_are_immutable_and_once_only(self) -> None:
        with SessionLocal() as db:
            now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
            first_booking = self._completed(db, now - timedelta(days=8))
            first = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == first_booking.id)
            settings.VAYORA_COMMISSION_RATE = Decimal("0.20")
            settlement_service.refresh_due_settlements(db, now + timedelta(days=1))
            db.refresh(first)
            self.assertEqual(first.commission_rate, Decimal("0.100000"))
            self.assertEqual(first.vayora_fee, Decimal("120.00"))
            first.status = SettlementStatus.SETTLED
            first.payout_provider = "TEST_PAYOUT"
            first.payout_provider_reference = f"paid-{uuid.uuid4().hex}"
            first.settled_at = now
            db.commit()
            admin = db.get(User, self.admin_id)
            settlement_service.add_adjustment(db, admin, first.id, SettlementAdjustmentKind.REVERSAL, Decimal("-50"), "Recovery on next payout")

            second_booking = self._completed(db, now - timedelta(days=8))
            second = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == second_booking.id)
            self.assertEqual(second.adjustment_total, Decimal("-50.00"))
            self.assertEqual(second.net_payable, Decimal("910.00"))
            adjustment = db.scalar(select(SettlementAdjustment).where(SettlementAdjustment.settlement_id == first.id))
            self.assertEqual(adjustment.applied_to_settlement_id, second.id)
            third_booking = self._completed(db, now - timedelta(days=8))
            third = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == third_booking.id)
            self.assertEqual(third.adjustment_total, Decimal("0.00"))
            settings.VAYORA_COMMISSION_RATE = Decimal("0.10")

    def test_payout_idempotency_provider_success_failure_and_callback_dedupe(self) -> None:
        fake = FakePayoutProvider()
        original_provider = payout_provider.configured_provider
        payout_provider.configured_provider = lambda: fake
        try:
            with SessionLocal() as db:
                now = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)
                booking = self._completed(db, now - timedelta(days=8))
                settlement = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == booking.id)
                admin = db.get(User, self.admin_id)
                processing = payout_service.initiate(db, settlement.id, admin=admin, reason="Approved verified hotel payout")
                SettlementResponse.model_validate(processing)
                partner_payload = PartnerSettlementResponse.model_validate(processing).model_dump()
                self.assertNotIn("payout_provider_reference", partner_payload)
                self.assertNotIn("provider_payout_id", partner_payload["payout"])
                self.assertNotIn("provider_status", partner_payload["payout"])
                self.assertEqual(processing.status, SettlementStatus.PROCESSING)
                self.assertEqual(processing.payout.status, PayoutStatus.PROCESSING)
                self.assertIsNotNone(db.scalar(select(AuditLog).where(AuditLog.action == "PAYOUT_INITIATED", AuditLog.target_id == str(settlement.id))))
                duplicate = payout_service.initiate(db, settlement.id, admin=admin, reason="Duplicate click")
                self.assertEqual(duplicate.payout.id, processing.payout.id)
                self.assertEqual(fake.creates, 1)

                fake.state = "failed"
                failed = payout_service.reconcile(db, processing.payout.id, admin=admin)
                self.assertEqual(failed.status, PayoutStatus.FAILED)
                self.assertEqual(failed.settlement.status, SettlementStatus.RECONCILIATION_REQUIRED)
                fake.state = "completed"
                completed = payout_service.reconcile(db, processing.payout.id, admin=admin)
                self.assertEqual(completed.status, PayoutStatus.SUCCESS)
                self.assertEqual(completed.settlement.status, SettlementStatus.SETTLED)

                second_booking = self._completed(db, now - timedelta(days=8))
                second = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == second_booking.id)
                second_processing = payout_service.initiate(db, second.id, admin=admin, reason="Callback payout test")
                payload = (f'{{"event_id":"evt-1","payout_reference":"{second_processing.payout.provider_payout_id}","status":"completed","amount":"{second_processing.payout.amount}","currency":"INR"}}').encode()
                with self.assertRaises(HTTPException) as forged:
                    payout_service.handle_callback(db, payload, "forged")
                self.assertEqual(forged.exception.status_code, 401)
                callback = payout_service.handle_callback(db, payload, "valid")
                duplicate_callback = payout_service.handle_callback(db, payload, "valid")
                self.assertEqual(callback.id, duplicate_callback.id)
                self.assertEqual(callback.status, PayoutStatus.SUCCESS)
                self.assertEqual(db.scalar(select(func.count()).select_from(PayoutWebhookEvent).where(PayoutWebhookEvent.payout_id == callback.id)), 1)
        finally:
            payout_provider.configured_provider = original_provider

    def test_uncertain_submission_is_recovered_by_stable_reference_before_retry(self) -> None:
        fake = FakePayoutProvider()
        fake.create_exception = ProviderOutcomeUnknown("network result unknown")
        original_provider = payout_provider.configured_provider
        payout_provider.configured_provider = lambda: fake
        try:
            with SessionLocal() as db:
                now = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)
                booking = self._completed(db, now - timedelta(days=8))
                settlement = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == booking.id)
                admin = db.get(User, self.admin_id)
                uncertain = payout_service.initiate(db, settlement.id, admin=admin)
                self.assertEqual(uncertain.status, SettlementStatus.RECONCILIATION_REQUIRED)
                self.assertEqual(uncertain.payout.status, PayoutStatus.RECONCILIATION_REQUIRED)
                self.assertIsNone(uncertain.payout.provider_payout_id)
                with self.assertRaises(HTTPException):
                    payout_service.retry_submission(db, settlement.id, admin=admin, reason="Unsafe early retry")

                fake.lookup_result = ProviderPayout("remote-after-timeout", "processing", uncertain.payout.amount, "INR")
                recovered = payout_service.reconcile(db, uncertain.payout.id, admin=admin)
                self.assertEqual(recovered.provider_payout_id, "remote-after-timeout")
                self.assertEqual(recovered.status, PayoutStatus.PROCESSING)
                self.assertEqual(recovered.settlement.status, SettlementStatus.PROCESSING)
                self.assertEqual(fake.creates, 1)
        finally:
            payout_provider.configured_provider = original_provider

    def test_retry_requires_confirmed_absence_and_unchanged_destination(self) -> None:
        fake = FakePayoutProvider()
        fake.create_exception = ProviderOutcomeUnknown("network result unknown")
        original_provider = payout_provider.configured_provider
        payout_provider.configured_provider = lambda: fake
        try:
            with SessionLocal() as db:
                now = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
                booking = self._completed(db, now - timedelta(days=8))
                settlement = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == booking.id)
                admin = db.get(User, self.admin_id)
                uncertain = payout_service.initiate(db, settlement.id, admin=admin)
                absent = payout_service.reconcile(db, uncertain.payout.id, admin=admin)
                self.assertIn("No provider payout exists", absent.reconciliation_reason)

                verification = db.scalar(select(HotelVerification).where(HotelVerification.hotel_id == self.hotel_id))
                original_account = verification.bank_account_number
                verification.bank_account_number = "999999999999"
                db.commit()
                with self.assertRaises(HTTPException) as changed:
                    payout_service.retry_submission(db, settlement.id, admin=admin, reason="Destination changed")
                self.assertEqual(changed.exception.status_code, 409)
                verification.bank_account_number = original_account
                db.commit()
        finally:
            payout_provider.configured_provider = original_provider

    def test_payout_rechecks_refund_and_dispute_immediately_before_submission(self) -> None:
        fake = FakePayoutProvider()
        original_provider = payout_provider.configured_provider
        payout_provider.configured_provider = lambda: fake
        try:
            with SessionLocal() as db:
                now = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)
                disputed_booking = self._completed(db, now - timedelta(days=8))
                disputed = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == disputed_booking.id)
                db.add(Conversation(hotel_id=self.hotel_id, customer_id=self.customer_id, booking_id=disputed_booking.id, subject="Late payout dispute", kind=ConversationKind.DISPUTE, status=ConversationStatus.OPEN))
                db.commit()
                with self.assertRaises(HTTPException):
                    payout_service.initiate(db, disputed.id, admin=db.get(User, self.admin_id))

                refunded_booking = self._completed(db, now - timedelta(days=8))
                refunded = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == refunded_booking.id)
                cancellation = Cancellation(booking_id=refunded_booking.id, cancellation_type=CancellationType.CUSTOMER, status=CancellationStatus.COMPLETED, reason="Late verified refund", policy_snapshot={}, refundable_amount=Decimal("100"), refunded_amount=Decimal("100"), requires_manual_review=False)
                db.add(cancellation); db.flush()
                payment = db.scalar(select(Payment).where(Payment.booking_id == refunded_booking.id))
                db.add(Refund(cancellation_id=cancellation.id, payment_id=payment.id, amount=Decimal("100"), currency="INR", status=RefundStatus.SUCCEEDED, provider_refund_id=f"late_{uuid.uuid4().hex}", settlement_impact_status=SettlementImpactStatus.PENDING))
                db.commit()
                with self.assertRaises(HTTPException):
                    payout_service.initiate(db, refunded.id, admin=db.get(User, self.admin_id))
                self.assertEqual(fake.creates, 0)
        finally:
            payout_provider.configured_provider = original_provider

    def test_completed_payout_reversal_is_terminal_and_audited(self) -> None:
        fake = FakePayoutProvider()
        original_provider = payout_provider.configured_provider
        payout_provider.configured_provider = lambda: fake
        try:
            with SessionLocal() as db:
                now = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)
                booking = self._completed(db, now - timedelta(days=8))
                settlement = next(item for item in settlement_service.refresh_due_settlements(db, now) if item.booking_id == booking.id)
                processing = payout_service.initiate(db, settlement.id, admin=db.get(User, self.admin_id))
                payout_id = processing.payout.provider_payout_id

                def callback(event_id: str, state: str):
                    body = f'{{"event_id":"{event_id}","payout_reference":"{payout_id}","status":"{state}","amount":"{processing.payout.amount}","currency":"INR"}}'.encode()
                    return payout_service.handle_callback(db, body, "valid")

                completed = callback("evt-completed", "completed")
                self.assertEqual(completed.settlement.status, SettlementStatus.SETTLED)
                reversed_payout = callback("evt-reversed", "reversed")
                self.assertEqual(reversed_payout.status, PayoutStatus.REVERSED)
                self.assertEqual(reversed_payout.settlement.status, SettlementStatus.RECONCILIATION_REQUIRED)
                self.assertIn("reversal", reversed_payout.settlement.hold_reason.lower())
                stale = callback("evt-stale-processing", "processing")
                self.assertEqual(stale.status, PayoutStatus.REVERSED)
                self.assertEqual(stale.settlement.status, SettlementStatus.RECONCILIATION_REQUIRED)
                self.assertTrue(any(event.new_status == SettlementStatus.RECONCILIATION_REQUIRED for event in stale.settlement.events))
        finally:
            payout_provider.configured_provider = original_provider


if __name__ == "__main__":
    unittest.main(verbosity=2)
