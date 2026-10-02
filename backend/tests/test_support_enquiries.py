import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import delete, select, text

from app.core.security import hash_password
from app.core.config import settings
from app.database import SessionLocal
from app.models.auth_security import AuthRateLimitBucket, AuthSession
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.communication import Notification, NotificationJob
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, PropertyType, RoomType, RoomTypeStatus
from app.models.safari import Safari, SafariRequest
from app.models.support import SupportEnquiry
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user
from app.services import auth_security_service
from tests.test_auth_integration import request_json


class SupportEnquiryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suffix = uuid.uuid4().hex[:10]
        password_hash = hash_password("StrongPass123")
        with SessionLocal() as db:
            cls.customer = create_user(db, full_name="Support Customer", email=f"support-customer-{cls.suffix}@example.com", phone=f"+9191{uuid.uuid4().int % 100000000:08d}", password_hash=password_hash)
            cls.other = create_user(db, full_name="Other Customer", email=f"support-other-{cls.suffix}@example.com", phone=f"+9192{uuid.uuid4().int % 100000000:08d}", password_hash=password_hash)
            cls.admin = create_user(db, full_name="Support Admin", email=f"support-admin-{cls.suffix}@example.com", phone=f"+9193{uuid.uuid4().int % 100000000:08d}", password_hash=password_hash, role=UserRole.ADMIN)
            cls.customer_id, cls.other_id, cls.admin_id = cls.customer.id, cls.other.id, cls.admin.id
            cls.customer_token, _ = auth_security_service.create_session_tokens(db, cls.customer)
            cls.other_token, _ = auth_security_service.create_session_tokens(db, cls.other)
            cls.admin_token, _ = auth_security_service.create_session_tokens(db, cls.admin)

            hotel = Hotel(name="Support Test Hotel", slug=f"support-hotel-{cls.suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("3.0"), status=HotelStatus.ACTIVE, address_line1="1 Support Road", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
            db.add(hotel); db.flush()
            room = RoomType(hotel_id=hotel.id, name="Support Room", max_adults=2, max_children=1, max_guests=3, bed_type="Double", bed_count=1, base_price=Decimal("2000.00"), currency="INR", total_rooms=1, is_active=True, status=RoomTypeStatus.BOOKABLE)
            db.add(room); db.flush()
            cls.own_booking_ref = f"VYR-SUPPORT-{cls.suffix.upper()}"
            cls.other_booking_ref = f"VYR-OTHER-{cls.suffix.upper()}"
            own_booking = Booking(booking_reference=cls.own_booking_ref, user_id=cls.customer_id, hotel_id=hotel.id, room_type_id=room.id, check_in=date.today() + timedelta(days=30), check_out=date.today() + timedelta(days=31), rooms=1, adults=1, children=0, nights=1, currency="INR", subtotal=Decimal("2000"), taxes=Decimal("0"), platform_fee=Decimal("0"), discount=Decimal("0"), total_amount=Decimal("2000"), room_snapshot={}, price_snapshot={}, policy_snapshot={}, booking_mode=BookingGatewayStatus.ACTIVE, status=BookingStatus.PAYMENT_PENDING, payment_status=PaymentStatus.NOT_STARTED)
            other_booking = Booking(booking_reference=cls.other_booking_ref, user_id=cls.other_id, hotel_id=hotel.id, room_type_id=room.id, check_in=date.today() + timedelta(days=30), check_out=date.today() + timedelta(days=31), rooms=1, adults=1, children=0, nights=1, currency="INR", subtotal=Decimal("2000"), taxes=Decimal("0"), platform_fee=Decimal("0"), discount=Decimal("0"), total_amount=Decimal("2000"), room_snapshot={}, price_snapshot={}, policy_snapshot={}, booking_mode=BookingGatewayStatus.ACTIVE, status=BookingStatus.PAYMENT_PENDING, payment_status=PaymentStatus.NOT_STARTED)
            safari = Safari(name="Support Safari", slug=f"support-safari-{cls.suffix}", short_description="Support test Safari", shifts=[], zones=[], gates=[], booking_categories=[], vehicle_options=[], traveller_requirements={}, is_active=True, is_public=True)
            db.add_all([own_booking, other_booking, safari]); db.flush()
            cls.safari_ref = f"SAF-SUPPORT-{cls.suffix.upper()}"
            safari_request = SafariRequest(request_reference=cls.safari_ref, safari_id=safari.id, customer_id=cls.customer_id, preferred_date=date.today() + timedelta(days=40), visitor_count=2, target_response_at=datetime.now(timezone.utc) + timedelta(hours=1))
            db.add(safari_request); db.commit()
            cls.hotel_id, cls.room_id = hotel.id, room.id
            cls.booking_ids = [own_booking.id, other_booking.id]
            cls.safari_id, cls.safari_request_id = safari.id, safari_request.id
        cls.references: list[str] = []

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            if cls.references:
                keys = [f"SUPPORT_ENQUIRY_RECEIVED:{reference}" for reference in cls.references]
                notification_ids = list(db.scalars(select(Notification.id).where(Notification.dedupe_key.in_(keys))))
                if notification_ids:
                    db.execute(delete(NotificationJob).where(NotificationJob.notification_id.in_(notification_ids)))
                    db.execute(delete(Notification).where(Notification.id.in_(notification_ids)))
            db.execute(delete(SupportEnquiry).where(SupportEnquiry.reference.in_(cls.references)))
            db.execute(delete(AuthRateLimitBucket).where(AuthRateLimitBucket.scope == "support-enquiry"))
            db.execute(delete(AuthSession).where(AuthSession.user_id.in_([cls.customer_id, cls.other_id, cls.admin_id])))
            db.execute(delete(SafariRequest).where(SafariRequest.id == cls.safari_request_id))
            db.execute(delete(Safari).where(Safari.id == cls.safari_id))
            db.execute(delete(Booking).where(Booking.id.in_(cls.booking_ids)))
            db.execute(delete(RoomType).where(RoomType.id == cls.room_id))
            db.execute(delete(Hotel).where(Hotel.id == cls.hotel_id))
            db.execute(delete(User).where(User.id.in_([cls.customer_id, cls.other_id, cls.admin_id])))
            db.commit()

    @staticmethod
    def payload(key: str, enquiry_type: str = "GENERAL", reference: str | None = None) -> dict[str, object]:
        value: dict[str, object] = {"idempotency_key": key, "enquiry_type": enquiry_type, "name": "Test Traveller", "email": "traveller@example.com", "mobile": "+919876543210", "message": "Please help me with this Maharashtra Tourist Places enquiry."}
        if reference: value["customer_reference"] = reference
        return value

    def remember(self, response: dict[str, object]) -> None:
        self.references.append(str(response["reference"]))

    def test_anonymous_submission_is_durable_encrypted_and_idempotent(self) -> None:
        key = f"anon-{uuid.uuid4().hex}"
        code, first = request_json("POST", "/support/enquiries", self.payload(key))
        self.assertEqual(code, 201, first); self.remember(first)
        code, duplicate = request_json("POST", "/support/enquiries", self.payload(key))
        self.assertEqual(code, 201, duplicate)
        self.assertEqual(first["reference"], duplicate["reference"])
        with SessionLocal() as db:
            self.assertEqual(db.scalar(select(SupportEnquiry).where(SupportEnquiry.idempotency_key == key)).reference, first["reference"])
            raw = db.execute(text("SELECT name, message FROM support_enquiries WHERE reference=:reference"), {"reference": first["reference"]}).one()
            self.assertTrue(raw.name.startswith("enc:v1:")); self.assertTrue(raw.message.startswith("enc:v1:"))

    def test_authenticated_references_are_tenant_isolated(self) -> None:
        code, own = request_json("POST", "/support/enquiries", self.payload(f"own-{uuid.uuid4().hex}", "BOOKING_HELP", self.own_booking_ref), self.customer_token)
        self.assertEqual(code, 201, own); self.remember(own)
        code, denied = request_json("POST", "/support/enquiries", self.payload(f"deny-{uuid.uuid4().hex}", "BOOKING_HELP", self.other_booking_ref), self.customer_token)
        self.assertEqual(code, 404, denied)
        code, safari = request_json("POST", "/support/enquiries", self.payload(f"safari-{uuid.uuid4().hex}", "SAFARI_HELP", self.safari_ref), self.customer_token)
        self.assertEqual(code, 201, safari); self.remember(safari)

    def test_admin_can_read_queue_but_customer_cannot(self) -> None:
        code, created = request_json("POST", "/support/enquiries", self.payload(f"admin-view-{uuid.uuid4().hex}"))
        self.assertEqual(code, 201, created); self.remember(created)
        code, denied = request_json("GET", "/admin/support/enquiries", token=self.customer_token)
        self.assertEqual(code, 403, denied)
        code, queue = request_json("GET", "/admin/support/enquiries", token=self.admin_token)
        self.assertEqual(code, 200, queue)
        self.assertTrue({item["reference"] for item in queue["items"]}.intersection(self.references))

    def test_partner_context_and_validation(self) -> None:
        payload = self.payload(f"partner-{uuid.uuid4().hex}", "HOTEL_PARTNER")
        code, invalid = request_json("POST", "/support/enquiries", payload)
        self.assertEqual(code, 422, invalid)
        payload["property_name"] = "Test Hills Hotel"
        code, valid = request_json("POST", "/support/enquiries", payload)
        self.assertEqual(code, 201, valid); self.remember(valid)

    def test_contact_methods_come_from_server_configuration(self) -> None:
        with (
            patch.object(settings, "PUBLIC_SUPPORT_EMAIL", "help@travel.example"),
            patch.object(settings, "PUBLIC_WHATSAPP_NUMBER", "+919876543210"),
        ):
            code, config = request_json("GET", "/support/config")
        self.assertEqual(code, 200, config)
        self.assertEqual(config["email"], "help@travel.example")
        self.assertEqual(config["whatsapp_url"], "https://wa.me/919876543210")


if __name__ == "__main__":
    unittest.main(verbosity=2)
