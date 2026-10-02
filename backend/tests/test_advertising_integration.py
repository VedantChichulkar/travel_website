import unittest
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.advertising import AdvertisingCampaign, AdvertisingCampaignStatus, AdvertisingEvent, AdvertisingEventType, AdvertisingPlacement
from app.models.booking import Payment, PaymentPurpose, PaymentStatus
from app.models.hotel import Hotel, HotelStatus, PropertyType
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.advertising import CampaignCreate
from app.services import advertising_service, payment_service


class AdvertisingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.partner = User(full_name="Ad Partner", email="ad-partner@test.local", phone="+919100001001", password_hash="x", role=UserRole.HOTEL_PARTNER)
        self.other = User(full_name="Other Partner", email="other-ad@test.local", phone="+919100001002", password_hash="x", role=UserRole.HOTEL_PARTNER)
        self.admin = User(full_name="Ad Admin", email="ad-admin@test.local", phone="+919100001003", password_hash="x", role=UserRole.ADMIN)
        self.db.add_all([self.partner, self.other, self.admin]); self.db.flush()
        self.hotel = Hotel(name="Advertiser", slug="advertiser", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=self.partner.id, address_line1="1 Ad Road", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
        self.other_hotel = Hotel(name="Other", slug="other-advertiser", property_type=PropertyType.HOTEL, star_rating=Decimal("3"), status=HotelStatus.ACTIVE, partner_id=self.other.id, address_line1="2 Ad Road", city="Pune", state="Maharashtra", country="India", postal_code="411002", check_in_time=time(14), check_out_time=time(11))
        self.db.add_all([self.hotel, self.other_hotel]); self.db.flush()
        self.db.add_all([HotelVerification(hotel_id=self.hotel.id, business_name=self.hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED), HotelVerification(hotel_id=self.other_hotel.id, business_name=self.other_hotel.name, business_type=BusinessType.PROPRIETORSHIP, verification_status=VerificationStatus.APPROVED)])
        self.db.commit()

    def tearDown(self):
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    def _campaign(self):
        item = advertising_service.create(self.db, self.partner, CampaignCreate(plan_code="HOME_7D", start_at=datetime.now(timezone.utc) + timedelta(minutes=1), alt_text="Hotel terrace"))
        campaign = self.db.get(AdvertisingCampaign, item.id)
        campaign.creative_url = "https://media.test/creative.webp"; campaign.creative_storage_key = f"hotels/{self.hotel.id}/campaigns/{campaign.id}/creative.webp"; campaign.creative_content_type = "image/webp"; campaign.creative_size = 100
        self.db.commit()
        return campaign

    def _pay(self, campaign):
        payment = advertising_service.create_payment_order(self.db, self.partner, campaign.id)
        return payment_service.process_webhook(self.db, payment.provider, f"event-{campaign.id}", payment.provider_order_id, "succeeded", payment.amount, payment.currency, f"provider-{campaign.id}")

    def test_payment_is_server_priced_idempotent_and_does_not_approve(self):
        campaign = self._campaign(); payment = advertising_service.create_payment_order(self.db, self.partner, campaign.id)
        self.assertEqual(payment.amount, next(plan.amount for plan in advertising_service.configured_plans() if plan.code == "HOME_7D"))
        self.assertEqual(payment.purpose, PaymentPurpose.ADVERTISING_CAMPAIGN)
        self.assertEqual(advertising_service.create_payment_order(self.db, self.partner, campaign.id).id, payment.id)
        self._pay(campaign); self.db.refresh(campaign)
        self.assertEqual(campaign.status, AdvertisingCampaignStatus.PAYMENT_PENDING)

    def test_unpaid_cannot_submit_and_tenant_isolation(self):
        campaign = self._campaign()
        with self.assertRaises(HTTPException) as unpaid: advertising_service.submit(self.db, self.partner, campaign.id)
        self.assertEqual(unpaid.exception.status_code, 409)
        with self.assertRaises(HTTPException) as isolated: advertising_service.create_payment_order(self.db, self.other, campaign.id)
        self.assertEqual(isolated.exception.status_code, 404)

    def test_review_changes_reuses_payment_and_reject_is_idempotent(self):
        campaign = self._campaign(); payment = self._pay(campaign)
        advertising_service.submit(self.db, self.partner, campaign.id)
        changed = advertising_service.review(self.db, self.admin, campaign.id, "REQUEST_CHANGES", "Use a clearer image")
        self.assertEqual(changed.status, AdvertisingCampaignStatus.NEEDS_CHANGES)
        self.assertEqual(self.db.scalar(select(func.count(Payment.id)).where(Payment.advertising_campaign_id == campaign.id)), 1)
        advertising_service.submit(self.db, self.partner, campaign.id)
        rejected = advertising_service.review(self.db, self.admin, campaign.id, "REJECT", "Creative violates policy")
        again = advertising_service.review(self.db, self.admin, campaign.id, "REJECT", "Creative violates policy")
        self.assertEqual(rejected.status, AdvertisingCampaignStatus.REJECTED); self.assertEqual(again.status, AdvertisingCampaignStatus.REJECTED)
        self.assertEqual(payment.status, PaymentStatus.PAID)

    def test_approved_campaign_public_delivery_metrics_and_expiry(self):
        campaign = self._campaign(); self._pay(campaign); advertising_service.submit(self.db, self.partner, campaign.id)
        campaign.start_at = datetime.now(timezone.utc) - timedelta(minutes=1); campaign.end_at = datetime.now(timezone.utc) + timedelta(days=1); self.db.commit()
        approved = advertising_service.review(self.db, self.admin, campaign.id, "APPROVE", None)
        self.assertEqual(approved.status, AdvertisingCampaignStatus.ACTIVE)
        public = advertising_service.public_campaigns(self.db, AdvertisingPlacement.HOMEPAGE_BANNER, None, None)
        self.assertEqual([item.id for item in public], [campaign.public_id])
        self.assertEqual(public[0].destination_url, f"/hotels/{self.hotel.slug}")
        self.assertTrue(advertising_service.record_event(self.db, campaign.public_id, AdvertisingEventType.IMPRESSION, "view-event-1", "visitor"))
        self.assertFalse(advertising_service.record_event(self.db, campaign.public_id, AdvertisingEventType.IMPRESSION, "view-event-1", "visitor"))
        self.assertFalse(advertising_service.record_event(self.db, campaign.public_id, AdvertisingEventType.IMPRESSION, "rotated-event-id", "visitor"))
        self.assertEqual(self.db.scalar(select(func.count(AdvertisingEvent.id))), 1)
        campaign.end_at = datetime.now(timezone.utc) - timedelta(seconds=1); self.db.commit(); advertising_service.refresh_due(self.db)
        self.assertEqual(campaign.status, AdvertisingCampaignStatus.EXPIRED)
        self.assertEqual(advertising_service.public_campaigns(self.db, AdvertisingPlacement.HOMEPAGE_BANNER, None, None), [])

    def test_ineligible_hotel_cannot_advertise(self):
        self.hotel.status = HotelStatus.SUSPENDED; self.db.commit()
        with self.assertRaises(HTTPException) as raised: advertising_service.create(self.db, self.partner, CampaignCreate(plan_code="HOME_7D", start_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        self.assertEqual(raised.exception.status_code, 409)
