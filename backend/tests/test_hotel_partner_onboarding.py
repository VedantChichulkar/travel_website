import asyncio
import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path
from datetime import time
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from fastapi import UploadFile
from starlette.datastructures import Headers
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.permission import require_admin, require_customer, require_hotel_partner, require_hotel_partner_only
from app.core.security import hash_password
from app.core.config import settings
from app.database import Base
from app.models.hotel import Amenity, HotelStatus, PropertyType
from app.models.hotel_verification import BusinessType, VerificationStatus
from app.models.booking import Payment, PaymentStatus, Refund, RefundStatus
from app.models.audit import AuditLog
from app.models.user import User, UserRole, UserStatus
from app.repositories import hotel_repository, hotel_verification_repository, user_repository
from app.schemas.hotel import AmenityAssignment, HotelCreate, HotelImageCreate, HotelImageOrderUpdate, HotelUpdate, PartnerHotelProfileUpdate
from app.schemas.hotel_verification import (
    ReviewActionType,
    VerificationReviewRequest,
    VerificationSubmitRequest,
)
from app.schemas.user import UserCreate
from app.services import admin_verification_service, auth_service, partner_hotel_service, payment_service


class TestHotelPartnerOnboarding(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )
        self.db = self.SessionLocal()

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _create_user(
        self,
        email: str,
        role: UserRole = UserRole.CUSTOMER,
        phone: str = "+919876543210",
        full_name: str = "Test User",
    ) -> User:
        user = user_repository.create_user(
            self.db,
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=hash_password("StrongPassword123"),
            role=role,
            status=UserStatus.ACTIVE,
        )
        return user

    def _sample_hotel_create(self, **overrides) -> HotelCreate:
        data = {
            "name": "Sahyadri Heritage Resort",
            "slug": "sahyadri-heritage-resort",
            "description": "Authentic boutique resort nestled in Mahabaleshwar.",
            "property_type": PropertyType.RESORT,
            "star_rating": Decimal("4.5"),
            "address_line1": "Panchgani-Mahabaleshwar Road",
            "city": "Mahabaleshwar",
            "district": "Satara",
            "state": "Maharashtra",
            "country": "India",
            "postal_code": "412806",
            "check_in_time": time(14, 0),
            "check_out_time": time(11, 0),
            "contact_email": "reservations@sahyadriresort.com",
            "contact_phone": "+919822334455",
        }
        data.update(overrides)
        return HotelCreate(**data)

    def _sample_verification_submit(self, **overrides) -> VerificationSubmitRequest:
        data = {
            "business_name": "Sahyadri Hospitality LLP",
            "business_type": BusinessType.LLP,
            "gstin": "27ABCDE1234F1Z5",
            "pan": "ABCDE1234F",
            "bank_account_number": "12345678901234",
            "bank_ifsc": "HDFC0001234",
            "bank_name": "HDFC Bank Ltd",
            "bank_beneficiary_name": "Sahyadri Hospitality LLP",
            "document_proof_type": "TRADE_LICENSE",
        }
        data.update(overrides)
        return VerificationSubmitRequest(**data)

    def _pay_verification_fee(self, partner: User) -> None:
        payment = payment_service.create_verification_fee_order(self.db, partner)
        payment_service.process_webhook(self.db, payment.provider, uuid.uuid4().hex, payment.provider_order_id, "succeeded", payment.amount, payment.currency, uuid.uuid4().hex)

    def _create_partner_hotel(self, suffix: str) -> tuple[User, object]:
        partner = self._create_user(f"partner-{suffix}@example.com", UserRole.HOTEL_PARTNER, f"+9188{suffix[-8:].zfill(8)}", f"Partner {suffix}")
        hotel = partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create(name=f"Hotel {suffix}", slug=f"hotel-{suffix}"))
        return partner, hotel

    def test_verification_fee_gate_payment_and_changes_reuse(self) -> None:
        partner, hotel = self._create_partner_hotel("10000001")
        with self.assertRaises(HTTPException) as unpaid:
            partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())
        self.assertEqual(unpaid.exception.status_code, 409)
        self.db.rollback()

        payment = payment_service.create_verification_fee_order(self.db, partner)
        self.assertEqual(payment.amount, settings.VERIFICATION_FEE_AMOUNT)
        self.assertEqual(payment.currency, settings.VERIFICATION_FEE_CURRENCY)
        self.assertEqual(payment_service.create_verification_fee_order(self.db, partner).id, payment.id)
        paid = payment_service.process_webhook(self.db, payment.provider, "verification-paid-1", payment.provider_order_id, "succeeded", payment.amount, payment.currency, "provider-verification-1")
        self.assertEqual(paid.status, PaymentStatus.PAID)
        self.assertIsNone(hotel_verification_repository.get_verification_by_hotel_id(self.db, hotel.id))
        self.assertEqual(hotel_repository.get_hotel(self.db, hotel.id).status, HotelStatus.DRAFT)

        verification = partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())
        admin = self._create_user("fee-admin@example.com", UserRole.ADMIN, "+918700000001", "Fee Admin")
        changes = admin_verification_service.review_verification(self.db, admin, verification.id, VerificationReviewRequest(action=ReviewActionType.REQUEST_CHANGES, admin_notes="Upload a clearer licence"))
        self.assertEqual(changes.verification_status, VerificationStatus.NEEDS_CHANGES)
        self.assertEqual(self.db.scalar(select(func.count(Refund.id))), 0)
        partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit(bank_name="Updated Bank"))
        self.assertEqual(self.db.scalar(select(func.count(Payment.id)).where(Payment.verification_hotel_id == hotel.id)), 1)
        approved = admin_verification_service.review_verification(self.db, admin, verification.id, VerificationReviewRequest(action=ReviewActionType.APPROVE, admin_notes="Documents verified"))
        self.assertEqual(approved.verification_status, VerificationStatus.APPROVED)
        self.assertEqual(self.db.scalar(select(func.count(Refund.id))), 0)

    def test_final_rejection_creates_one_full_idempotent_refund(self) -> None:
        partner, hotel = self._create_partner_hotel("10000002")
        self._pay_verification_fee(partner)
        verification = partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())
        admin = self._create_user("reject-admin@example.com", UserRole.ADMIN, "+918700000002", "Reject Admin")
        decision = VerificationReviewRequest(action=ReviewActionType.REJECT, rejection_reason="Licence is invalid")
        rejected = admin_verification_service.review_verification(self.db, admin, verification.id, decision)
        self.assertEqual(rejected.verification_status, VerificationStatus.REJECTED)
        refunds = list(self.db.scalars(select(Refund).where(Refund.verification_id == verification.id)))
        self.assertEqual(len(refunds), 1)
        self.assertEqual(refunds[0].amount, settings.VERIFICATION_FEE_AMOUNT)
        admin_verification_service.review_verification(self.db, admin, verification.id, decision)
        self.assertEqual(self.db.scalar(select(func.count(Refund.id)).where(Refund.verification_id == verification.id)), 1)
        self.assertIsNotNone(self.db.scalar(select(AuditLog).where(AuditLog.action == "VERIFICATION_REFUND_TRIGGERED", AuditLog.target_id == str(refunds[0].id))))

    def test_refund_failure_keeps_rejection_and_tenant_authorization(self) -> None:
        partner, _ = self._create_partner_hotel("10000003")
        self._pay_verification_fee(partner)
        verification = partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())
        admin = self._create_user("failure-admin@example.com", UserRole.ADMIN, "+918700000003", "Failure Admin")
        with patch("app.services.payment_provider.SandboxHmacProvider.create_refund", side_effect=HTTPException(status_code=503, detail="temporarily unavailable")):
            admin_verification_service.review_verification(self.db, admin, verification.id, VerificationReviewRequest(action=ReviewActionType.REJECT, rejection_reason="Final compliance rejection"))
        self.assertEqual(hotel_verification_repository.get_verification_by_id(self.db, verification.id).verification_status, VerificationStatus.REJECTED)
        refund = self.db.scalar(select(Refund).where(Refund.verification_id == verification.id))
        self.assertIn(refund.status, (RefundStatus.RETRY_REQUIRED, RefundStatus.RECONCILIATION_REQUIRED))
        outsider, _ = self._create_partner_hotel("10000004")
        with self.assertRaises(HTTPException):
            partner_hotel_service.get_partner_verification(self.db, outsider)
        with self.assertRaises(HTTPException) as forbidden:
            require_admin(outsider)
        self.assertEqual(forbidden.exception.status_code, 403)

    # 1. Partner Registration & Role Verification
    def test_partner_registration(self) -> None:
        partner_data = UserCreate(
            full_name="Rajesh Patil",
            email="rajesh.patil@example.com",
            phone="+919811223344",
            password="PartnerPassword123",
            role=UserRole.HOTEL_PARTNER,
        )
        partner_response = auth_service.register_user(self.db, partner_data)
        self.assertEqual(partner_response.role, UserRole.HOTEL_PARTNER)
        self.assertEqual(partner_response.email, "rajesh.patil@example.com")
        self.assertTrue(partner_response.is_active)

    def test_admin_public_registration_is_blocked(self) -> None:
        with self.assertRaises(ValidationError):
            UserCreate(
                full_name="Attacker Admin",
                email="attacker@example.com",
                phone="+919811223399",
                password="AdminPassword123",
                role=UserRole.ADMIN,
            )

    # 2. Hotel Creation by Partner
    def test_partner_create_hotel(self) -> None:
        partner = self._create_user("partner1@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000001")
        hotel_data = self._sample_hotel_create()
        hotel_res = partner_hotel_service.create_partner_hotel(self.db, partner, hotel_data)

        self.assertEqual(hotel_res.name, "Sahyadri Heritage Resort")
        self.assertEqual(hotel_res.status, HotelStatus.DRAFT)
        self.assertEqual(hotel_res.partner_id, partner.id)

        # Ensure database record is updated
        db_hotel = hotel_repository.get_hotel_by_partner_id(self.db, partner.id)
        self.assertIsNotNone(db_hotel)
        self.assertEqual(db_hotel.status, HotelStatus.DRAFT)

    def test_partner_cannot_create_duplicate_hotel(self) -> None:
        partner = self._create_user("partner2@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000002")
        partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create(slug="hotel-one"))

        with self.assertRaises(HTTPException) as exc:
            partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create(slug="hotel-two"))
        self.assertEqual(exc.exception.status_code, 409)

    def test_profile_update_is_owner_scoped_and_persists_completion(self) -> None:
        owner = self._create_user("profile-owner@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000101")
        other_partner = self._create_user("profile-other@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000102")
        partner_hotel_service.create_partner_hotel(self.db, owner, self._sample_hotel_create(slug="owner-profile"))
        partner_hotel_service.create_partner_hotel(self.db, other_partner, self._sample_hotel_create(slug="other-profile", name="Other Resort"))
        wifi = Amenity(name="Wi-Fi", slug="profile-wifi", category="Basic", is_active=True)
        self.db.add(wifi)
        self.db.commit()

        result = partner_hotel_service.update_partner_profile(
            self.db,
            owner,
            PartnerHotelProfileUpdate(description="A complete, guest-ready resort profile.", district="Satara", state="Maharashtra"),
        )
        self.assertEqual(result.name, "Sahyadri Heritage Resort")
        self.assertEqual(result.profile_completion_percent, 86)  # all detail fields, before facilities/photos
        partner_hotel_service.replace_partner_amenities(self.db, owner, AmenityAssignment(amenity_ids=[wifi.id]))
        partner_hotel_service.add_partner_image(self.db, owner, HotelImageCreate(image_url="https://cdn.example.com/owner.jpg", is_cover=True))
        complete = partner_hotel_service.get_partner_profile(self.db, owner)
        self.assertTrue(complete.is_profile_complete)
        self.assertEqual(complete.profile_completion_percent, 100)
        self.assertEqual(len(complete.images), 1)
        self.assertEqual(len(complete.amenities), 1)
        self.assertEqual(hotel_repository.get_hotel_by_partner_id(self.db, other_partner.id).name, "Other Resort")

    def test_profile_authorization_rejects_non_partner_and_foreign_image(self) -> None:
        customer = self._create_user("profile-customer@example.com", role=UserRole.CUSTOMER, phone="+919000000103")
        with self.assertRaises(HTTPException) as exc:
            require_hotel_partner_only(customer)
        self.assertEqual(exc.exception.status_code, 403)

        owner = self._create_user("profile-image-owner@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000104")
        other = self._create_user("profile-image-other@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000105")
        partner_hotel_service.create_partner_hotel(self.db, owner, self._sample_hotel_create(slug="image-owner"))
        partner_hotel_service.create_partner_hotel(self.db, other, self._sample_hotel_create(slug="image-other"))
        image = partner_hotel_service.add_partner_image(self.db, owner, HotelImageCreate(image_url="https://cdn.example.com/owner.jpg"))
        with self.assertRaises(HTTPException) as exc:
            partner_hotel_service.delete_partner_image(self.db, other, image.id)
        self.assertEqual(exc.exception.status_code, 404)

    def test_uploaded_image_metadata_primary_order_and_deletion(self) -> None:
        owner = self._create_user("gallery-owner@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000106")
        other = self._create_user("gallery-other@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000107")
        partner_hotel_service.create_partner_hotel(self.db, owner, self._sample_hotel_create(slug="gallery-owner"))
        partner_hotel_service.create_partner_hotel(self.db, other, self._sample_hotel_create(slug="gallery-other"))
        old_root = settings.MEDIA_ROOT
        old_base_url = settings.MEDIA_BASE_URL
        with tempfile.TemporaryDirectory() as directory:
            settings.MEDIA_ROOT = Path(directory)
            settings.MEDIA_BASE_URL = "https://media.test"
            try:
                def upload(name: str) -> UploadFile:
                    return UploadFile(
                        filename=name,
                        file=BytesIO(b"\x89PNG\r\n\x1a\n" + b"gallery-image"),
                        headers=Headers({"content-type": "image/png"}),
                    )

                first = asyncio.run(partner_hotel_service.upload_partner_image(self.db, owner, upload("first.png"), alt_text="Exterior"))
                second = asyncio.run(partner_hotel_service.upload_partner_image(self.db, owner, upload("second.png"), alt_text="Lobby"))
                self.assertTrue(first.is_cover)
                self.assertEqual(first.content_type, "image/png")
                self.assertGreater(first.file_size or 0, 8)
                self.assertTrue((settings.MEDIA_ROOT / str(first.storage_key)).exists())

                primary = partner_hotel_service.set_partner_primary_image(self.db, owner, second.id)
                self.assertTrue(primary.is_cover)
                ordered = partner_hotel_service.reorder_partner_images(self.db, owner, HotelImageOrderUpdate(image_ids=[second.id, first.id]))
                self.assertEqual([image.id for image in ordered], [second.id, first.id])
                with self.assertRaises(HTTPException) as exc:
                    partner_hotel_service.delete_partner_image(self.db, other, first.id)
                self.assertEqual(exc.exception.status_code, 404)
                partner_hotel_service.delete_partner_image(self.db, owner, first.id)
                self.assertFalse((settings.MEDIA_ROOT / str(first.storage_key)).exists())
            finally:
                settings.MEDIA_ROOT = old_root
                settings.MEDIA_BASE_URL = old_base_url

    # 3. Verification Submission & Status Transition
    def test_verification_submission_moves_hotel_to_pending(self) -> None:
        partner = self._create_user("partner3@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000003")
        partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create())

        ver_data = self._sample_verification_submit()
        self._pay_verification_fee(partner)
        ver_res = partner_hotel_service.submit_partner_verification(self.db, partner, ver_data)

        self.assertEqual(ver_res.verification_status, VerificationStatus.PENDING)
        self.assertEqual(ver_res.business_name, "Sahyadri Hospitality LLP")
        self.assertEqual(ver_res.gstin, "27ABCDE1234F1Z5")

        # Verify hotel status is now PENDING
        db_hotel = hotel_repository.get_hotel_by_partner_id(self.db, partner.id)
        self.assertEqual(db_hotel.status, HotelStatus.PENDING)

        # Verify partner overview status
        overview = partner_hotel_service.get_partner_overview(self.db, partner)
        self.assertTrue(overview.has_hotel)
        self.assertTrue(overview.is_onboarding_complete)
        self.assertFalse(overview.can_access_portal)

    # 4. Verification Input Validations
    def test_invalid_gstin_and_pan_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self._sample_verification_submit(gstin="INVALID_GSTIN")

        with self.assertRaises(ValidationError):
            self._sample_verification_submit(pan="INVALID_PAN")

        with self.assertRaises(ValidationError):
            self._sample_verification_submit(bank_ifsc="INVALID_IFSC")

    # 5. Admin Review: Approval Flow
    def test_admin_approve_flow_atomic_transaction(self) -> None:
        admin = self._create_user("admin@platform.test", role=UserRole.ADMIN, phone="+919999999999")
        partner = self._create_user("partner4@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000004")

        partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create())
        self._pay_verification_fee(partner)
        ver_res = partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())

        # Admin lists verification requests
        pending_list = admin_verification_service.list_verification_requests(self.db, status_filter=VerificationStatus.PENDING)
        self.assertEqual(len(pending_list), 1)
        self.assertEqual(pending_list[0].id, ver_res.id)
        self.assertEqual(pending_list[0].partner_email, "partner4@example.com")

        # Admin inspects detail
        detail = admin_verification_service.get_verification_detail(self.db, ver_res.id)
        self.assertEqual(detail.hotel.name, "Sahyadri Heritage Resort")
        self.assertEqual(detail.partner["email"], "partner4@example.com")

        # Admin approves
        review_req = VerificationReviewRequest(action=ReviewActionType.APPROVE, admin_notes="Documents verified successfully.")
        reviewed_ver = admin_verification_service.review_verification(self.db, admin, ver_res.id, review_req)

        self.assertEqual(reviewed_ver.verification_status, VerificationStatus.APPROVED)
        self.assertEqual(reviewed_ver.reviewed_by, admin.id)
        self.assertIsNotNone(reviewed_ver.reviewed_at)

        # Verify hotel status is now ACTIVE
        db_hotel = hotel_repository.get_hotel_by_partner_id(self.db, partner.id)
        self.assertEqual(db_hotel.status, HotelStatus.ACTIVE)

        # Verify partner can now access portal
        overview = partner_hotel_service.get_partner_overview(self.db, partner)
        self.assertTrue(overview.can_access_portal)

    # 6. Admin Review: Rejection Flow
    def test_admin_reject_flow(self) -> None:
        admin = self._create_user("admin2@platform.test", role=UserRole.ADMIN, phone="+919999999998")
        partner = self._create_user("partner5@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000005")

        partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create())
        self._pay_verification_fee(partner)
        ver_res = partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())

        # Admin rejects with reason
        review_req = VerificationReviewRequest(
            action=ReviewActionType.REJECT,
            rejection_reason="Trade license expired. Please upload valid certificate.",
        )
        reviewed_ver = admin_verification_service.review_verification(self.db, admin, ver_res.id, review_req)

        self.assertEqual(reviewed_ver.verification_status, VerificationStatus.REJECTED)
        self.assertEqual(reviewed_ver.rejection_reason, "Trade license expired. Please upload valid certificate.")

        # Hotel status reverts to DRAFT
        db_hotel = hotel_repository.get_hotel_by_partner_id(self.db, partner.id)
        self.assertEqual(db_hotel.status, HotelStatus.DRAFT)

        # Partner cannot access portal, but sees rejection reason
        overview = partner_hotel_service.get_partner_overview(self.db, partner)
        self.assertFalse(overview.can_access_portal)
        self.assertEqual(overview.verification.verification_status, VerificationStatus.REJECTED)
        self.assertEqual(overview.verification.rejection_reason, "Trade license expired. Please upload valid certificate.")

    # 7. Admin Review: Additional Information Flow
    def test_admin_request_additional_info_flow(self) -> None:
        admin = self._create_user("admin3@platform.test", role=UserRole.ADMIN, phone="+919999999997")
        partner = self._create_user("partner6@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000006")

        partner_hotel_service.create_partner_hotel(self.db, partner, self._sample_hotel_create())
        self._pay_verification_fee(partner)
        ver_res = partner_hotel_service.submit_partner_verification(self.db, partner, self._sample_verification_submit())

        # Admin requests info
        review_req = VerificationReviewRequest(
            action=ReviewActionType.REQUEST_INFO,
            admin_notes="Please provide clearer electricity bill copy.",
        )
        reviewed_ver = admin_verification_service.review_verification(self.db, admin, ver_res.id, review_req)

        self.assertEqual(reviewed_ver.verification_status, VerificationStatus.ADDITIONAL_INFO_REQUIRED)
        self.assertEqual(reviewed_ver.admin_notes, "Please provide clearer electricity bill copy.")

        # Partner can re-submit
        update_ver_data = self._sample_verification_submit()
        resubmitted_ver = partner_hotel_service.submit_partner_verification(self.db, partner, update_ver_data)
        self.assertEqual(resubmitted_ver.verification_status, VerificationStatus.PENDING)
        self.assertFalse(resubmitted_ver.document_available)

    # 8. Authorization & Security Checks
    def test_customer_cannot_access_partner_endpoints(self) -> None:
        customer = self._create_user("customer@example.com", role=UserRole.CUSTOMER, phone="+919000000007")
        with self.assertRaises(HTTPException) as exc:
            require_hotel_partner(customer)
        self.assertEqual(exc.exception.status_code, 403)

    def test_partner_cannot_access_admin_verifications(self) -> None:
        partner = self._create_user("partner7@example.com", role=UserRole.HOTEL_PARTNER, phone="+919000000008")
        with self.assertRaises(HTTPException) as exc:
            require_admin(partner)
        self.assertEqual(exc.exception.status_code, 403)

    def test_admin_can_access_admin_verifications(self) -> None:
        admin = self._create_user("admin4@platform.test", role=UserRole.ADMIN, phone="+919000000009")
        validated_admin = require_admin(admin)
        self.assertEqual(validated_admin.id, admin.id)


if __name__ == "__main__":
    unittest.main()
