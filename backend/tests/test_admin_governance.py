import unittest
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.permission import require_admin
from app.database import Base
from app.models.audit import AuditLog
from app.models.booking import Booking, BookingStatus, Cancellation, CancellationStatus, CancellationType, Payment, PaymentStatus, Refund, RefundStatus, SettlementImpactStatus
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, PropertyType, RoomType
from app.models.settlement import Settlement, SettlementStatus
from app.models.user import User, UserRole
from app.schemas.hotel import HotelStatusUpdate
from app.api.v1.admin_hotels import update_hotel_status as legacy_update_hotel_status
from app.services import audit_service, booking_gateway_service, cancellation_service, settlement_service


class AdminGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine); self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.admin = User(full_name="Governor", email="admin@gov.test", phone="+919100000001", password_hash="x", role=UserRole.ADMIN)
        self.customer = User(full_name="Guest", email="guest@gov.test", phone="+919100000002", password_hash="x", role=UserRole.CUSTOMER)
        self.partner = User(full_name="Partner", email="partner@gov.test", phone="+919100000003", password_hash="x", role=UserRole.HOTEL_PARTNER)
        self.db.add_all([self.admin, self.customer, self.partner]); self.db.flush()
        self.hotel = Hotel(name="Governed Hotel", slug="governed-hotel", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=self.partner.id, booking_gateway_status=BookingGatewayStatus.ACTIVE, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Audit Road", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
        self.db.add(self.hotel); self.db.flush()
        room = RoomType(hotel_id=self.hotel.id, name="Audit Room", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("1000"), currency="INR", total_rooms=2); self.db.add(room); self.db.flush()
        self.booking = Booking(booking_reference="VYO-GOV-1", user_id=self.customer.id, hotel_id=self.hotel.id, room_type_id=room.id, check_in=date(2026, 10, 1), check_out=date(2026, 10, 2), rooms=1, adults=1, children=0, nights=1, currency="INR", subtotal=Decimal("1000"), taxes=Decimal("120"), platform_fee=Decimal("0"), discount=Decimal("0"), total_amount=Decimal("1120"), room_snapshot={}, price_snapshot={}, policy_snapshot={}, status=BookingStatus.REFUND_PENDING, payment_status=PaymentStatus.REFUND_PENDING, checked_out_at=datetime(2026, 10, 2, 11, tzinfo=timezone.utc))
        self.db.add(self.booking); self.db.flush()
        payment = Payment(booking_id=self.booking.id, provider="TEST", provider_order_id="order-gov-1", provider_payment_id="payment-gov-1", amount=Decimal("1120"), currency="INR", status=PaymentStatus.PAID)
        self.db.add(payment); self.db.flush()
        cancellation = Cancellation(booking_id=self.booking.id, cancellation_type=CancellationType.CUSTOMER, status=CancellationStatus.REFUND_PENDING, reason="Customer request", policy_snapshot={}, refundable_amount=Decimal("1120"), refunded_amount=Decimal("0"), requires_manual_review=False)
        self.db.add(cancellation); self.db.flush()
        self.refund = Refund(cancellation_id=cancellation.id, payment_id=payment.id, amount=Decimal("1120"), currency="INR", status=RefundStatus.PENDING, settlement_impact_status=SettlementImpactStatus.PENDING)
        self.settlement = Settlement(hotel_id=self.hotel.id, booking_id=self.booking.id, currency="INR", gross_amount=Decimal("1120"), vayora_fee=Decimal("0"), refund_deductions=Decimal("0"), adjustment_total=Decimal("0"), net_payable=Decimal("1120"), eligibility_date=datetime(2026, 10, 9, tzinfo=timezone.utc), status=SettlementStatus.ELIGIBLE)
        self.db.add_all([self.refund, self.settlement]); self.db.commit()

    def tearDown(self) -> None:
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    def test_role_isolation_rejects_non_admin(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            require_admin(self.customer)
        self.assertEqual(raised.exception.status_code, 403)

    def test_hotel_override_creates_audit_entry(self) -> None:
        booking_gateway_service.set_override(self.db, self.hotel, self.admin, BookingGatewayStatus.PAUSED, "Fraud and inventory review")
        entry = self.db.scalar(select(AuditLog).where(AuditLog.action == "BOOKING_GATEWAY_OVERRIDDEN"))
        self.assertEqual(entry.actor_user_id, self.admin.id)
        self.assertEqual(entry.previous_value["override_status"], None)
        self.assertEqual(entry.new_value["override_status"], "PAUSED")

    def test_legacy_hotel_status_route_uses_audited_governance_path(self) -> None:
        updated = legacy_update_hotel_status(
            self.hotel.id,
            HotelStatusUpdate(status=HotelStatus.SUSPENDED, reason="Safety investigation in progress"),
            self.db,
            self.admin,
        )
        self.assertEqual(updated.status, HotelStatus.SUSPENDED)
        entry = self.db.scalar(select(AuditLog).where(AuditLog.action == "HOTEL_STATUS_CHANGED"))
        self.assertEqual(entry.actor_user_id, self.admin.id)
        self.assertEqual(entry.previous_value["status"], HotelStatus.ACTIVE.value)
        self.assertEqual(entry.new_value["status"], HotelStatus.SUSPENDED.value)
        self.assertEqual(entry.reason, "Safety investigation in progress")

    def test_sensitive_hotel_status_change_requires_reason(self) -> None:
        with self.assertRaises(ValidationError):
            HotelStatusUpdate(status=HotelStatus.SUSPENDED)

    def test_refund_and_settlement_interventions_are_audited(self) -> None:
        cancellation_service.settle_refund(self.db, self.admin, self.refund.id, RefundStatus.MANUAL_REVIEW, reason="Provider state requires investigation")
        settlement_service.hold(self.db, self.admin, self.settlement.id, "Reconcile completed refund before payout")
        actions = set(self.db.scalars(select(AuditLog.action)))
        self.assertIn("REFUND_SETTLED", actions)
        self.assertIn("SETTLEMENT_HELD", actions)

    def test_manual_settlement_refresh_is_audited_even_without_due_changes(self) -> None:
        changed = settlement_service.refresh_due_settlements(
            self.db,
            datetime(2026, 9, 18, tzinfo=timezone.utc),
            admin=self.admin,
            reason="Operator requested eligibility reconciliation",
        )
        self.assertEqual(changed, [])
        entry = self.db.scalar(select(AuditLog).where(AuditLog.action == "SETTLEMENT_ELIGIBILITY_REFRESHED"))
        self.assertEqual(entry.actor_user_id, self.admin.id)
        self.assertEqual(entry.new_value["changed_count"], 0)

    def test_audit_logs_reject_update_and_delete(self) -> None:
        entry = audit_service.record(self.db, actor=self.admin, action="TEST_ACTION", target_type="TEST", target_id=1, reason="Immutable history test", previous_value={"value": 1}, new_value={"value": 2})
        self.db.commit()
        entry.reason = "attempted rewrite"
        with self.assertRaises(ValueError):
            self.db.commit()
        self.db.rollback(); entry = self.db.get(AuditLog, entry.id); self.db.delete(entry)
        with self.assertRaises(ValueError):
            self.db.commit()


if __name__ == "__main__":
    unittest.main()
