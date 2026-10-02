import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.permission import require_admin
from app.database import Base
from app.models.audit import AuditLog
from app.models.booking import Payment, PaymentPurpose, PaymentReconciliationStatus, PaymentStatus, Refund
from app.models.communication import Notification
from app.models.destination import Destination, District
from app.models.safari import Safari, SafariDocument, SafariDocumentKind, SafariRequest, SafariRequestStatus
from app.models.user import User, UserRole
from app.schemas.safari import AvailabilityDecision, AvailabilityRequestCreate, ConfirmationInput, PricingInput, SafariConfigurationUpdate, SafariOperationalNoticeCreate, SafariOperationalNoticeUpdate, TravellerSubmission
from app.services import payment_service, private_document_storage, refund_execution_service, safari_service


class SafariIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine); self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.customer = User(full_name="Safari Guest", email="safari@test.local", phone="+919200000001", password_hash="x", role=UserRole.CUSTOMER)
        self.other = User(full_name="Other Guest", email="other-safari@test.local", phone="+919200000002", password_hash="x", role=UserRole.CUSTOMER)
        self.admin = User(full_name="Safari Ops", email="safari-admin@test.local", phone="+919200000003", password_hash="x", role=UserRole.ADMIN)
        self.db.add_all([self.customer, self.other, self.admin]); self.db.flush()
        district = District(name="Test District", slug="test-district", division="Test", is_active=True)
        self.db.add(district); self.db.flush()
        destination = Destination(district_id=district.id, name="Test Reserve", slug="test-reserve", is_active=True)
        self.db.add(destination); self.db.flush()
        self.safari = Safari(name="Configured Test Safari", slug="configured-test-safari", district_id=district.id, destination_id=destination.id, short_description="A configured test catalog entry.", shifts=["MORNING"], zones=[], gates=[], traveller_requirements={"fields": [{"key": "full_name", "required": True}], "documents": []}, is_active=True, is_public=True)
        self.db.add(self.safari); self.db.commit()

    def tearDown(self): self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    def _request(self):
        return safari_service.create_request(self.db, self.customer, self.safari.slug, AvailabilityRequestCreate(preferred_date=date.today() + timedelta(days=20), preferred_shift="MORNING", visitor_count=1))

    def _available(self, request_id):
        safari_service.availability_decision(self.db, self.admin, request_id, AvailabilityDecision(action="START_CHECK", reason="Operations began checking"))
        return safari_service.availability_decision(self.db, self.admin, request_id, AvailabilityDecision(action="MARK_AVAILABLE", reason="External availability observed"))

    def _payment_ready(self):
        request = self._request(); self._available(request.id)
        safari_service.save_travellers(self.db, self.customer, request.id, TravellerSubmission(travellers=[{"details": {"full_name": "Safari Guest"}}]))
        safari_service.set_pricing(self.db, self.admin, request.id, PricingInput(amount=Decimal("4200.00"), currency="INR", breakdown={"managed_safari": "4200.00"}, reason="Operations confirmed final payable amount"))
        safari_service.submit_travellers(self.db, self.customer, request.id)
        return self.db.get(SafariRequest, request.id)

    def test_discovery_request_sla_notifications_and_ownership(self):
        public = safari_service.get_public(self.db, self.safari.slug)
        self.assertEqual(public.id, self.safari.id)
        self.assertEqual(public.destination_path, "/destinations/test-district/test-reserve")
        self.assertEqual(public.hotel_destination_filter, "test-district/test-reserve")
        before = datetime.now(timezone.utc); request = self._request()
        target = request.target_response_at if request.target_response_at.tzinfo else request.target_response_at.replace(tzinfo=timezone.utc)
        self.assertAlmostEqual((target - before).total_seconds(), settings.SAFARI_RESPONSE_TARGET_MINUTES * 60, delta=5)
        self.assertFalse(request.overdue); self.assertGreater(self.db.scalar(select(func.count(Notification.id))), 0)
        with self.assertRaises(HTTPException) as isolated: safari_service.get_customer(self.db, self.other, request.id)
        self.assertEqual(isolated.exception.status_code, 404)

    def test_manual_available_details_and_audit(self):
        request = self._request()
        with self.assertRaises(HTTPException): safari_service.save_travellers(self.db, self.customer, request.id, TravellerSubmission(travellers=[{"details": {"full_name": "Guest"}}]))
        available = self._available(request.id)
        self.assertEqual(available.status, SafariRequestStatus.AWAITING_TRAVELLER_DETAILS); self.assertIsNotNone(available.responded_at)
        saved = safari_service.save_travellers(self.db, self.customer, request.id, TravellerSubmission(travellers=[{"details": {"full_name": "Guest"}}]))
        self.assertEqual(saved.travellers[0].details["full_name"], "Guest")
        ciphertext = self.db.execute(text("SELECT details_encrypted FROM safari_travellers WHERE request_id = :request_id"), {"request_id": request.id}).scalar_one()
        self.assertTrue(ciphertext.startswith("enc:v1:")); self.assertNotIn("Guest", ciphertext)
        self.assertGreaterEqual(self.db.scalar(select(func.count(AuditLog.id)).where(AuditLog.target_type == "safari_request")), 2)

    def test_request_rejects_past_dates_and_unconfigured_shifts(self):
        with self.assertRaises(HTTPException) as past:
            safari_service.create_request(self.db, self.customer, self.safari.slug, AvailabilityRequestCreate(preferred_date=date.today() - timedelta(days=1), preferred_shift="MORNING", visitor_count=1))
        self.assertEqual(past.exception.status_code, 422)
        with self.assertRaises(HTTPException) as shift:
            safari_service.create_request(self.db, self.customer, self.safari.slug, AvailabilityRequestCreate(preferred_date=date.today() + timedelta(days=20), preferred_shift="EVENING", visitor_count=1))
        self.assertEqual(shift.exception.status_code, 422)

    def test_required_documents_gate_traveller_submission(self):
        self.safari.traveller_requirements = {"fields": [{"key": "full_name", "required": True}], "documents": [{"type": "identity", "required": True}]}
        self.db.commit()
        request = self._request(); self._available(request.id)
        safari_service.save_travellers(self.db, self.customer, request.id, TravellerSubmission(travellers=[{"details": {"full_name": "Safari Guest"}}]))
        with self.assertRaises(HTTPException) as missing:
            safari_service.submit_travellers(self.db, self.customer, request.id)
        self.assertEqual(missing.exception.status_code, 409)

    def test_unavailable_alternative_selection(self):
        request = self._request()
        unavailable = safari_service.availability_decision(self.db, self.admin, request.id, AvailabilityDecision(action="MARK_UNAVAILABLE", reason="Requested option unavailable", alternatives=[{"safari_date": date.today() + timedelta(days=21), "shift": "MORNING", "note": "Known available alternative"}]))
        self.assertEqual(unavailable.status, SafariRequestStatus.NOT_AVAILABLE)
        selected = safari_service.select_alternative(self.db, self.customer, request.id, unavailable.alternatives[0].id)
        self.assertEqual(selected.status, SafariRequestStatus.AWAITING_TRAVELLER_DETAILS); self.assertEqual(selected.selected_alternative_id, unavailable.alternatives[0].id)

    def test_booking_category_and_vehicle_are_configurable_and_manual(self):
        configured = safari_service.update_configuration(self.db, self.admin, self.safari.id, SafariConfigurationUpdate(
            booking_categories=[{"code": "REGULAR", "label": "Regular"}], vehicle_options=[{"code": "GYPSY", "label": "Gypsy"}],
            source_url="https://safaribooking.mahaforest.gov.in/", last_verified_at=datetime.now(timezone.utc), reason="Verified configurable official concepts",
        ))
        self.assertEqual(configured.booking_categories[0]["code"], "REGULAR")
        with self.assertRaises(HTTPException):
            safari_service.create_request(self.db, self.customer, self.safari.slug, AvailabilityRequestCreate(preferred_date=date.today() + timedelta(days=10), preferred_shift="MORNING", visitor_count=1))
        request = safari_service.create_request(self.db, self.customer, self.safari.slug, AvailabilityRequestCreate(preferred_date=date.today() + timedelta(days=10), preferred_shift="MORNING", preferred_booking_category="REGULAR", preferred_vehicle_option="GYPSY", visitor_count=1))
        self.assertEqual(request.status, SafariRequestStatus.AVAILABILITY_REQUESTED)
        self.assertEqual(request.preferred_booking_category, "REGULAR")
        self.assertIsNone(request.responded_at)

    def test_operational_notices_are_effective_dated_and_audited(self):
        now = datetime.now(timezone.utc)
        notice = safari_service.create_notice(self.db, self.admin, SafariOperationalNoticeCreate(safari_id=self.safari.id, title="Operations notice", body="Check the current official instruction.", effective_from=now - timedelta(hours=1), effective_until=now + timedelta(hours=1), source_url="https://safaribooking.mahaforest.gov.in/", last_verified_at=now, reason="Published verified operational notice"))
        public = safari_service.get_public(self.db, self.safari.slug)
        self.assertEqual([value.id for value in public.operational_notices], [notice.id])
        safari_service.update_notice(self.db, self.admin, notice.id, SafariOperationalNoticeUpdate(is_active=False, reason="Notice no longer applies"))
        self.assertEqual(safari_service.get_public(self.db, self.safari.slug).operational_notices, [])
        self.assertGreaterEqual(self.db.scalar(select(func.count(AuditLog.id)).where(AuditLog.target_type == "safari_operational_notice")), 2)

    def test_payment_eligibility_does_not_auto_confirm_and_manual_confirmation(self):
        request = self._payment_ready(); payment = safari_service.create_payment_order(self.db, self.customer, request.id)
        self.assertEqual(payment.purpose, PaymentPurpose.SAFARI_BOOKING); self.assertEqual(payment.amount, Decimal("4200.00"))
        paid = payment_service.process_webhook(self.db, payment.provider, "safari-payment-event", payment.provider_order_id, "succeeded", payment.amount, payment.currency, "safari-provider-payment")
        self.assertEqual(paid.status, PaymentStatus.PAID); self.assertEqual(self.db.get(SafariRequest, request.id).status, SafariRequestStatus.BOOKING_IN_PROGRESS)
        confirmed = safari_service.confirm(self.db, self.admin, request.id, ConfirmationInput(booking_reference="EXT-REF", safari_date=request.preferred_date, shift="MORNING", reporting_instructions="Report as instructed by operations.", final_amount=Decimal("4200.00"), reason="External permit confirmed"))
        self.assertEqual(confirmed.status, SafariRequestStatus.CONFIRMED)
        again = safari_service.confirm(self.db, self.admin, request.id, ConfirmationInput(booking_reference="EXT-REF", safari_date=request.preferred_date, shift="MORNING", reporting_instructions="Report as instructed by operations.", final_amount=Decimal("4200.00"), reason="Retry"))
        self.assertEqual(again.status, SafariRequestStatus.CONFIRMED)

    def test_official_reference_contact_and_ticket_can_gate_confirmation(self):
        self.safari.official_reference_required = True; self.safari.official_contact_required = True; self.safari.official_document_required = True; self.db.commit()
        request = self._payment_ready(); payment = safari_service.create_payment_order(self.db, self.customer, request.id)
        payment_service.process_webhook(self.db, payment.provider, "official-workflow-payment", payment.provider_order_id, "succeeded", payment.amount, payment.currency, "official-workflow-provider-payment")
        with self.assertRaises(HTTPException):
            safari_service.confirm(self.db, self.admin, request.id, ConfirmationInput(safari_date=request.preferred_date, shift="MORNING", reporting_instructions="Report at the configured gate.", final_amount=Decimal("4200.00"), reason="Missing official artifacts"))
        self.assertEqual(self.db.get(SafariRequest, request.id).status, SafariRequestStatus.BOOKING_IN_PROGRESS)
        document = SafariDocument(request_id=request.id, kind=SafariDocumentKind.CONFIRMATION, document_type="official_ticket_or_permit", storage_key=f"safari/{request.id}/permit.pdf", original_name="permit.pdf", content_type="application/pdf", size=10)
        self.db.add(document); self.db.commit()
        confirmed = safari_service.confirm(self.db, self.admin, request.id, ConfirmationInput(booking_reference="OFFICIAL-123", safari_date=request.preferred_date, shift="MORNING", official_booking_contact="9876543210", reporting_instructions="Report at the configured gate.", final_amount=Decimal("4200.00"), reason="Official booking and ticket verified"))
        self.assertEqual(confirmed.status, SafariRequestStatus.CONFIRMED); self.assertIsNotNone(confirmed.operator_confirmed_at)
        self.assertTrue(confirmed.official_booking_contact_masked.endswith("3210")); self.assertNotIn("987654", confirmed.official_booking_contact_masked)
        ciphertext = self.db.execute(text("SELECT official_booking_contact FROM safari_requests WHERE id = :request_id"), {"request_id": request.id}).scalar_one()
        self.assertTrue(ciphertext.startswith("enc:v1:")); self.assertNotIn("9876543210", ciphertext)
        owned = safari_service.document_path(self.db, self.customer, request.id, document.id)
        self.assertEqual(owned.id, document.id)
        with self.assertRaises(HTTPException): safari_service.document_path(self.db, self.other, request.id, document.id)

    def test_booking_failure_enters_refund_reconciliation_idempotently(self):
        request = self._payment_ready(); payment = safari_service.create_payment_order(self.db, self.customer, request.id)
        payment_service.process_webhook(self.db, payment.provider, "safari-fail-payment", payment.provider_order_id, "succeeded", payment.amount, payment.currency, "safari-fail-provider-payment")
        failed = safari_service.fail_booking(self.db, self.admin, request.id, "External booking could not be secured")
        again = safari_service.fail_booking(self.db, self.admin, request.id, "External booking could not be secured")
        self.assertEqual(failed.status, SafariRequestStatus.BOOKING_FAILED); self.assertEqual(again.status, SafariRequestStatus.BOOKING_FAILED)
        self.assertEqual(self.db.scalar(select(func.count(Refund.id)).where(Refund.safari_request_id == request.id)), 1)
        refund = self.db.scalar(select(Refund).where(Refund.safari_request_id == request.id))
        detail = refund_execution_service.admin_detail(self.db, refund.id)
        self.assertEqual(detail.subject_type, "SAFARI")
        self.assertEqual(detail.safari_request_id, request.id)
        self.assertEqual(detail.subject_reference, request.request_reference)
        self.assertIsNone(detail.hotel_id)
        self.db.refresh(payment); self.assertIn(payment.status, (PaymentStatus.REFUND_PENDING, PaymentStatus.REFUNDED))
        self.assertIn(payment.reconciliation_status, (PaymentReconciliationStatus.REFUND_REQUIRED, PaymentReconciliationStatus.RESOLVED))

    def test_rbac(self):
        with self.assertRaises(HTTPException): require_admin(self.customer)
