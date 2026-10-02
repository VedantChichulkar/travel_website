import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.core.config import settings
from app.models.advertising import AdvertiserStatus, AdvertiserType, AdvertisingCampaign, AdvertisingCampaignStatus, AdvertisingEvent, AdvertisingEventType, AdvertisingPlacement
from app.models.booking import Payment, PaymentStatus
from app.models.user import User, UserRole
from app.schemas.advertising import AdvertiserProfileUpsert, ExternalCampaignCreate, ExternalCampaignUpdate
from app.services import advertising_service, payment_service


class ExternalAdvertisingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory(); self.original_media_root = settings.MEDIA_ROOT; settings.MEDIA_ROOT = Path(self.media_directory.name)
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine); self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.owner = User(full_name="QA Advertiser", email="qa-advertiser@test.local", phone="+919200001001", password_hash="x", role=UserRole.CUSTOMER)
        self.outsider = User(full_name="Other Advertiser", email="other-advertiser@test.local", phone="+919200001002", password_hash="x", role=UserRole.CUSTOMER)
        self.admin = User(full_name="Advertising Admin", email="qa-ad-admin@test.local", phone="+919200001003", password_hash="x", role=UserRole.ADMIN)
        self.db.add_all([self.owner, self.outsider, self.admin]); self.db.commit()
        self.profile = advertising_service.upsert_profile(self.db, self.owner, AdvertiserProfileUpsert(business_name="Maharashtra Tourist Places QA Business", contact_person="QA Person", business_email="qa-business@example.com", phone="+919200001004", category="Test business", description="Synthetic advertiser used only by automated tests.", website="https://example.com/about"))
        advertising_service.upsert_profile(self.db, self.outsider, AdvertiserProfileUpsert(business_name="Other QA Business", contact_person="Other Person", business_email="other-business@example.com", phone="+919200001005", category="Test business"))

    def tearDown(self):
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose(); settings.MEDIA_ROOT = self.original_media_root; self.media_directory.cleanup()

    def _create(self):
        result = advertising_service.create_external(self.db, self.owner, ExternalCampaignCreate(campaign_name="Autumn launch", headline="Explore local craft", short_copy="Meet independent makers near your next Maharashtra Tourist Places stay.", target_url="https://example.com/campaign", plan_code="HOME_7D", start_at=datetime.now(timezone.utc) + timedelta(minutes=1), alt_text="Handcrafted travel goods", creative_rights_confirmed=True, creative_source="Synthetic QA artwork"))
        item = self.db.get(AdvertisingCampaign, result.id); item.creative_url = "https://media.test/ad.webp"; item.creative_storage_key = "advertisers/test/ad.webp"; item.creative_content_type = "image/webp"; item.creative_size = 100; item.creative_width = 1200; item.creative_height = 675; self.db.commit(); return item

    def _pay(self, item):
        payment = advertising_service.create_external_payment_order(self.db, self.owner, item.id)
        return payment_service.process_webhook(self.db, payment.provider, f"external-event-{item.id}", payment.provider_order_id, "succeeded", payment.amount, payment.currency, f"external-provider-{item.id}")

    def test_external_owner_is_explicit_and_idor_is_hidden(self):
        item = self._create()
        self.assertEqual(item.advertiser_type, AdvertiserType.EXTERNAL); self.assertIsNone(item.hotel_id); self.assertEqual(item.advertiser_profile_id, self.profile.id)
        with self.assertRaises(HTTPException) as denied: advertising_service.create_external_payment_order(self.db, self.outsider, item.id)
        self.assertEqual(denied.exception.status_code, 404)

    def test_malicious_destinations_are_rejected(self):
        invalid = ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "http://example.com", "https://localhost/x", "https://127.0.0.1/x", "https://[::1]/x", "https://10.0.0.1/x", "https://user:pass@example.com/x", "not a url"]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(HTTPException): advertising_service.normalize_external_url(value)
        self.assertEqual(advertising_service.normalize_external_url("https://Example.COM/path#fragment"), "https://example.com/path")

    def test_payment_review_delivery_redirect_pause_and_expiry(self):
        item = self._create(); payment = self._pay(item); self.db.refresh(item)
        self.assertEqual(payment.status, PaymentStatus.PAID); self.assertEqual(item.status, AdvertisingCampaignStatus.PAYMENT_PENDING)
        advertising_service.submit_external(self.db, self.owner, item.id)
        item.start_at = datetime.now(timezone.utc) - timedelta(minutes=1); item.end_at = datetime.now(timezone.utc) + timedelta(days=1); self.db.commit()
        approved = advertising_service.review(self.db, self.admin, item.id, "APPROVE", None)
        self.assertEqual(approved.status, AdvertisingCampaignStatus.ACTIVE); self.assertEqual(item.approved_target_url, "https://example.com/campaign")
        public = advertising_service.public_campaigns(self.db, AdvertisingPlacement.HOMEPAGE_BANNER, None, None)
        self.assertEqual(public[0].advertiser_name, "Maharashtra Tourist Places QA Business"); self.assertTrue(public[0].is_external); self.assertNotIn("example.com/campaign", public[0].destination_url)
        self.assertEqual(advertising_service.click_destination(self.db, item.public_id, "qa-browser"), "https://example.com/campaign")
        self.assertEqual(self.db.scalar(select(func.count(AdvertisingEvent.id)).where(AdvertisingEvent.event_type == AdvertisingEventType.CLICK)), 1)
        paused = advertising_service.review(self.db, self.admin, item.id, "PAUSE", "Operational policy review")
        self.assertEqual(paused.status, AdvertisingCampaignStatus.PAUSED); self.assertEqual(advertising_service.public_campaigns(self.db, AdvertisingPlacement.HOMEPAGE_BANNER, None, None), [])

    def test_approval_requires_payment_and_paid_rejection_requires_policy_review(self):
        item = self._create(); item.status = AdvertisingCampaignStatus.PENDING_REVIEW; self.db.commit()
        with self.assertRaises(HTTPException): advertising_service.review(self.db, self.admin, item.id, "APPROVE", None)
        item.status = AdvertisingCampaignStatus.DRAFT; self.db.commit(); self._pay(item); advertising_service.submit_external(self.db, self.owner, item.id)
        rejected = advertising_service.review(self.db, self.admin, item.id, "REJECT", "Claims need substantiation")
        self.assertTrue(rejected.refund_review_required); self.assertEqual(self.db.scalar(select(func.count(Payment.id)).where(Payment.advertising_campaign_id == item.id)), 1)

    def test_material_target_change_revokes_approval(self):
        item = self._create(); self._pay(item); advertising_service.submit_external(self.db, self.owner, item.id); item.start_at = datetime.now(timezone.utc) - timedelta(minutes=1); item.end_at = datetime.now(timezone.utc) + timedelta(days=1); self.db.commit(); approved = advertising_service.review(self.db, self.admin, item.id, "APPROVE", None)
        updated = advertising_service.update_external(self.db, self.owner, item.id, ExternalCampaignUpdate(target_url="https://example.org/new", version=approved.version))
        self.assertEqual(updated.status, AdvertisingCampaignStatus.NEEDS_CHANGES); self.assertIsNone(item.approved_target_url)
        self.assertEqual(advertising_service.public_campaigns(self.db, AdvertisingPlacement.HOMEPAGE_BANNER, None, None), [])

    async def test_material_creative_replacement_revokes_approval_and_optimizes(self):
        item = self._create(); self._pay(item); advertising_service.submit_external(self.db, self.owner, item.id); item.start_at = datetime.now(timezone.utc) - timedelta(minutes=1); item.end_at = datetime.now(timezone.utc) + timedelta(days=1); self.db.commit(); advertising_service.review(self.db, self.admin, item.id, "APPROVE", None)
        content = BytesIO(); Image.new("RGB", (900, 500), (50, 100, 150)).save(content, "PNG")
        uploaded = await advertising_service.upload_external_creative(self.db, self.owner, item.id, UploadFile(filename="qa.png", file=BytesIO(content.getvalue()), headers={"content-type": "image/png"}), "Synthetic blue landscape", True, "Generated test image")
        self.assertEqual(uploaded.status, AdvertisingCampaignStatus.NEEDS_CHANGES); self.assertTrue(uploaded.creative_url.endswith(".webp")); self.assertIsNone(item.approved_target_url)

    def test_suspension_pauses_delivery_and_prevents_new_campaigns(self):
        item = self._create(); self._pay(item); advertising_service.submit_external(self.db, self.owner, item.id); item.start_at = datetime.now(timezone.utc) - timedelta(minutes=1); item.end_at = datetime.now(timezone.utc) + timedelta(days=1); self.db.commit(); advertising_service.review(self.db, self.admin, item.id, "APPROVE", None)
        profile = advertising_service.suspend_advertiser(self.db, self.admin, self.profile.id, True, "Governance review")
        self.assertEqual(profile.status, AdvertiserStatus.SUSPENDED); self.assertEqual(item.status, AdvertisingCampaignStatus.PAUSED)
        with self.assertRaises(HTTPException): self._create()


if __name__ == "__main__": unittest.main()
