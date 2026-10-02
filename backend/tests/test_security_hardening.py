import asyncio
import tempfile
import unittest
from datetime import time, timedelta
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import decode_token, hash_password, verify_password
from app.database import Base
from app.models.auth_security import AccountTokenPurpose
from app.models.hotel import Hotel, HotelStatus, PropertyType
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.hotel_verification import HotelVerificationResponse
from app.services import auth_security_service, partner_hotel_service, private_document_storage


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.user = User(full_name="Secure User", email="secure@example.com", phone="+919000001111", password_hash=hash_password("StrongPass123"), role=UserRole.CUSTOMER)
        self.partner = User(full_name="Secure Partner", email="partner-secure@example.com", phone="+919000001112", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
        self.other_partner = User(full_name="Other Partner", email="other-secure@example.com", phone="+919000001113", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
        self.db.add_all([self.user, self.partner, self.other_partner]); self.db.flush()
        self.hotel = Hotel(name="Secure Hotel", slug="secure-hotel", property_type=PropertyType.HOTEL, star_rating=4, status=HotelStatus.PENDING, partner_id=self.partner.id, address_line1="1 Safe Street", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
        self.db.add(self.hotel); self.db.commit()

    def tearDown(self) -> None:
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    def test_rate_limit_is_enforced_without_storing_identifier(self) -> None:
        auth_security_service.check_rate_limit(self.db, scope="test-login", identifier="person@example.com:127.0.0.1", maximum=2, window=timedelta(minutes=1))
        auth_security_service.check_rate_limit(self.db, scope="test-login", identifier="person@example.com:127.0.0.1", maximum=2, window=timedelta(minutes=1))
        with self.assertRaises(HTTPException) as exc:
            auth_security_service.check_rate_limit(self.db, scope="test-login", identifier="person@example.com:127.0.0.1", maximum=2, window=timedelta(minutes=1))
        self.assertEqual(exc.exception.status_code, 429)
        raw = self.db.execute(text("SELECT key_hash FROM auth_rate_limit_buckets")).scalar_one()
        self.assertNotIn("person", raw)

    def test_reset_is_single_use_and_revokes_session(self) -> None:
        access, _ = auth_security_service.create_session_tokens(self.db, self.user)
        payload = decode_token(access)
        self.assertIsNotNone(auth_security_service.get_active_session(self.db, session_id=payload["sid"], user=self.user, token_version=payload["ver"]))
        record, raw = auth_security_service._new_action_token(self.db, self.user, AccountTokenPurpose.PASSWORD_RESET, timedelta(minutes=5))
        self.db.commit()
        auth_security_service.reset_password(self.db, raw, "NewStrong456")
        self.db.refresh(self.user); self.db.refresh(record)
        self.assertTrue(verify_password("NewStrong456", self.user.password_hash))
        self.assertIsNotNone(record.used_at)
        self.assertIsNone(auth_security_service.get_active_session(self.db, session_id=payload["sid"], user=self.user, token_version=payload["ver"]))
        with self.assertRaises(HTTPException):
            auth_security_service.reset_password(self.db, raw, "AnotherStrong789")

    def test_expired_reset_token_is_rejected(self) -> None:
        _, raw = auth_security_service._new_action_token(self.db, self.user, AccountTokenPurpose.PASSWORD_RESET, timedelta(seconds=-1)); self.db.commit()
        with self.assertRaises(HTTPException) as exc:
            auth_security_service.reset_password(self.db, raw, "NewStrong456")
        self.assertEqual(exc.exception.status_code, 400)

    def test_email_verification_is_single_use(self) -> None:
        _, raw = auth_security_service._new_action_token(self.db, self.user, AccountTokenPurpose.EMAIL_VERIFICATION, timedelta(minutes=5)); self.db.commit()
        auth_security_service.verify_email(self.db, raw)
        self.assertTrue(self.user.is_email_verified)
        with self.assertRaises(HTTPException):
            auth_security_service.verify_email(self.db, raw)

    def test_sensitive_values_are_encrypted_and_masked(self) -> None:
        verification = HotelVerification(hotel_id=self.hotel.id, business_name="Secure Hospitality", business_type=BusinessType.LLP, gstin="27ABCDE1234F1Z5", pan="ABCDE1234F", bank_account_number="12345678901234", bank_ifsc="HDFC0001234", verification_status=VerificationStatus.PENDING)
        self.db.add(verification); self.db.commit()
        raw = self.db.execute(text("SELECT gstin, pan, bank_account_number FROM hotel_verifications WHERE id=:id"), {"id": verification.id}).mappings().one()
        self.assertTrue(raw["gstin"].startswith("enc:v1:")); self.assertNotIn("12345678901234", raw["bank_account_number"])
        payload = HotelVerificationResponse.model_validate(verification).model_dump(mode="json")
        self.assertTrue(payload["bank_account_number"].endswith("1234")); self.assertNotEqual(payload["pan"], "ABCDE1234F")

    def test_private_document_is_owner_scoped(self) -> None:
        old_root, old_mode = settings.PRIVATE_DOCUMENT_ROOT, settings.PRIVATE_DOCUMENT_MODE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                settings.PRIVATE_DOCUMENT_ROOT = Path(tmp); settings.PRIVATE_DOCUMENT_MODE = "local"
                upload = UploadFile(filename="license.pdf", file=BytesIO(b"%PDF-1.4 secure test"), headers=Headers({"content-type": "application/pdf"}))
                stored = asyncio.run(private_document_storage.store_verification_document(self.hotel.id, upload))
                verification = HotelVerification(hotel_id=self.hotel.id, business_name="Secure Hospitality", business_type=BusinessType.LLP, verification_status=VerificationStatus.PENDING, document_storage_key=stored.storage_key, document_original_name=stored.original_name, document_content_type=stored.content_type, document_size=stored.size)
                self.db.add(verification); self.db.commit()
                owned = partner_hotel_service.get_partner_verification_document(self.db, self.partner, verification.id)
                self.assertEqual(owned.id, verification.id)
                stream = private_document_storage.open_document(stored.storage_key)
                try:
                    self.assertTrue(b"".join(stream.chunks).startswith(b"%PDF-"))
                finally:
                    stream.close()
                with self.assertRaises(HTTPException) as exc:
                    partner_hotel_service.get_partner_verification_document(self.db, self.other_partner, verification.id)
                self.assertEqual(exc.exception.status_code, 404)
        finally:
            settings.PRIVATE_DOCUMENT_ROOT, settings.PRIVATE_DOCUMENT_MODE = old_root, old_mode


if __name__ == "__main__":
    unittest.main()
