import unittest
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.communication import ConversationAdminAccess, ConversationKind, Notification, NotificationChannel, NotificationEventType, NotificationJob, NotificationJobStatus
from app.models.hotel import Hotel, HotelStatus, PropertyType, RoomType
from app.models.user import User, UserRole
from app.schemas.communication import ConversationCreate
from app.services import communication_service, notification_service
from app.services.notification_provider import DeliveryResult


class FakeNotificationProvider:
    name = "TEST_NOTIFICATION_PROVIDER"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[NotificationChannel, str]] = []

    def send(self, *, channel, recipient, title, body, idempotency_key):
        del recipient, title, body
        self.calls.append((channel, idempotency_key))
        if self.fail:
            raise RuntimeError("secret-bearing provider failure must not be persisted")
        return DeliveryResult(provider_message_id=f"message-{len(self.calls)}")


class CommunicationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        self.customer = User(full_name="Guest One", email="guest@example.com", phone="+919000000001", password_hash="unused", role=UserRole.CUSTOMER)
        self.other_customer = User(full_name="Guest Two", email="other@example.com", phone="+919000000002", password_hash="unused", role=UserRole.CUSTOMER)
        self.partner = User(full_name="Partner One", email="partner@example.com", phone="+919000000003", password_hash="unused", role=UserRole.HOTEL_PARTNER)
        self.other_partner = User(full_name="Partner Two", email="partner2@example.com", phone="+919000000004", password_hash="unused", role=UserRole.HOTEL_PARTNER)
        self.admin = User(full_name="Admin", email="admin@example.com", phone="+919000000005", password_hash="unused", role=UserRole.ADMIN)
        self.db.add_all([self.customer, self.other_customer, self.partner, self.other_partner, self.admin]); self.db.flush()
        self.hotel = Hotel(name="Gateway Hotel", slug="gateway-hotel", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=self.partner.id, address_line1="1 Main Road", city="Pune", state="Maharashtra", country="India", postal_code="411001", check_in_time=time(14), check_out_time=time(11))
        self.other_hotel = Hotel(name="Other Hotel", slug="other-hotel", property_type=PropertyType.HOTEL, star_rating=Decimal("3"), status=HotelStatus.ACTIVE, partner_id=self.other_partner.id, address_line1="2 Main Road", city="Pune", state="Maharashtra", country="India", postal_code="411002", check_in_time=time(14), check_out_time=time(11))
        self.db.add_all([self.hotel, self.other_hotel]); self.db.flush()
        room = RoomType(hotel_id=self.hotel.id, name="Deluxe", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("1000"), currency="INR", total_rooms=2)
        self.db.add(room); self.db.flush()
        self.booking = Booking(booking_reference="VYO-COMM-1", user_id=self.customer.id, hotel_id=self.hotel.id, room_type_id=room.id, check_in=date(2026, 10, 1), check_out=date(2026, 10, 2), rooms=1, adults=1, children=0, nights=1, currency="INR", subtotal=Decimal("1000"), taxes=Decimal("120"), platform_fee=Decimal("0"), discount=Decimal("0"), total_amount=Decimal("1120"), room_snapshot={}, price_snapshot={}, policy_snapshot={}, status=BookingStatus.CONFIRMED, payment_status=PaymentStatus.PAID)
        self.db.add(self.booking); self.db.commit()

    def tearDown(self) -> None:
        self.db.close(); Base.metadata.drop_all(self.engine); self.engine.dispose()

    def _conversation(self):
        return communication_service.create_conversation(self.db, self.customer, ConversationCreate(booking_id=self.booking.id, subject="Arrival details", message="Can I arrive after 8pm?"))

    def test_customer_message_hotel_reply_and_booking_link(self) -> None:
        conversation = self._conversation()
        self.assertEqual(conversation.booking_id, self.booking.id)
        self.assertEqual(conversation.kind, ConversationKind.BOOKING)
        self.assertEqual(conversation.messages[0].body, "Can I arrive after 8pm?")
        replied = communication_service.send_message(self.db, self.partner, conversation.id, "Yes, the desk is open.")
        self.assertEqual(len(replied.messages), 2)
        self.assertEqual(replied.messages[-1].sender_user_id, self.partner.id)
        hotel_notice = self.db.scalar(select(Notification).where(Notification.recipient_user_id == self.partner.id, Notification.event_type == NotificationEventType.MESSAGE_RECEIVED))
        customer_notice = self.db.scalar(select(Notification).where(Notification.recipient_user_id == self.customer.id, Notification.event_type == NotificationEventType.MESSAGE_RECEIVED))
        self.assertIsNotNone(hotel_notice)
        self.assertIsNotNone(customer_notice)
        self.assertNotIn("desk is open", customer_notice.body.lower())

    def test_pre_booking_inquiry_is_supported(self) -> None:
        item = communication_service.create_conversation(self.db, self.customer, ConversationCreate(hotel_id=self.hotel.id, subject="Parking question", message="Is secure parking available?"))
        self.assertIsNone(item.booking_id)
        self.assertEqual(item.kind, ConversationKind.PRE_BOOKING)

    def test_cross_tenant_conversation_access_returns_not_found(self) -> None:
        conversation = self._conversation()
        for actor in (self.other_customer, self.other_partner):
            with self.subTest(actor=actor.role.value):
                with self.assertRaises(HTTPException) as raised:
                    communication_service.get_conversation(self.db, actor, conversation.id)
                self.assertEqual(raised.exception.status_code, 404)

    def test_unread_and_read_state(self) -> None:
        conversation = self._conversation()
        partner_view = communication_service.get_conversation(self.db, self.partner, conversation.id)
        self.assertEqual(communication_service.unread_count(partner_view, self.partner.id), 1)
        partner_view = communication_service.mark_read(self.db, self.partner, conversation.id)
        self.assertEqual(communication_service.unread_count(partner_view, self.partner.id), 0)
        communication_service.send_message(self.db, self.partner, conversation.id, "Confirmed.")
        customer_view = communication_service.get_conversation(self.db, self.customer, conversation.id)
        self.assertEqual(communication_service.unread_count(customer_view, self.customer.id), 1)
        customer_view = communication_service.mark_read(self.db, self.customer, conversation.id)
        self.assertEqual(communication_service.unread_count(customer_view, self.customer.id), 0)

    def test_admin_inspection_requires_reason_and_is_audited(self) -> None:
        conversation = self._conversation()
        communication_service.admin_inspect(self.db, self.admin, conversation.id, "Reviewing an active booking dispute")
        access = self.db.scalar(select(ConversationAdminAccess).where(ConversationAdminAccess.conversation_id == conversation.id))
        self.assertEqual(access.admin_user_id, self.admin.id)

    def test_notification_deduplication_unread_and_provider_fallback(self) -> None:
        first = notification_service.create(self.db, recipient_user_id=self.customer.id, event_type=NotificationEventType.BOOKING_CONFIRMATION, dedupe_key="booking:confirmed:1", title="Booking confirmed", body="Your stay is confirmed.")
        second = notification_service.create(self.db, recipient_user_id=self.customer.id, event_type=NotificationEventType.BOOKING_CONFIRMATION, dedupe_key="booking:confirmed:1", title="Booking confirmed", body="Duplicate callback.")
        self.db.commit()
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.db.scalar(select(func.count(Notification.id))), 1)
        items, unread = notification_service.list_for_user(self.db, self.customer)
        self.assertEqual(unread, 1)
        self.assertEqual(len(items[0].jobs), 3)
        self.assertTrue(all(job.status == NotificationJobStatus.PROVIDER_UNAVAILABLE for job in items[0].jobs))
        notification_service.mark_read(self.db, self.customer, first.id)
        self.assertEqual(notification_service.list_for_user(self.db, self.customer)[1], 0)

    def test_provider_failure_retry_and_worker_idempotency(self) -> None:
        provider = FakeNotificationProvider(fail=True)

        def configured_name(channel: NotificationChannel) -> str | None:
            return provider.name if channel == NotificationChannel.EMAIL else None

        now = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
        with patch("app.services.notification_provider.configured_name", side_effect=configured_name), patch("app.services.notification_provider.configured_provider", return_value=provider):
            notice = notification_service.create(
                self.db, recipient_user_id=self.customer.id,
                event_type=NotificationEventType.BOOKING_CONFIRMATION,
                dedupe_key="delivery-retry:booking:1", title="Booking confirmed",
                body="Your booking is confirmed.", commit=True,
            )
            email_job = next(job for job in notice.jobs if job.channel == NotificationChannel.EMAIL)
            self.assertEqual(email_job.status, NotificationJobStatus.PENDING)
            email_job.next_retry_at = now
            self.db.commit()
            self.assertEqual(notification_service.run_due(self.db, now=now), 1)
            self.db.refresh(email_job)
            self.assertEqual(email_job.status, NotificationJobStatus.FAILED)
            self.assertEqual(email_job.attempts, 1)
            self.assertNotIn("secret-bearing", email_job.last_error)
            self.assertEqual(notification_service.list_for_user(self.db, self.customer)[1], 1)

            provider.fail = False
            retry_at = email_job.next_retry_at
            self.assertIsNotNone(retry_at)
            self.assertEqual(notification_service.run_due(self.db, now=retry_at + timedelta(seconds=1)), 1)
            self.db.refresh(email_job)
            self.assertEqual(email_job.status, NotificationJobStatus.SENT)
            self.assertIsNotNone(email_job.sent_at)
            self.assertEqual(notification_service.run_due(self.db, now=retry_at + timedelta(minutes=30)), 0)
            self.assertEqual(len(provider.calls), 2)

    def test_booking_recipient_isolation_and_external_job_uniqueness(self) -> None:
        notices = notification_service.for_booking(
            self.db, self.booking, event_type=NotificationEventType.CHECK_IN,
            event_key=str(self.booking.id), title="Checked in", body="Check-in was recorded.",
        )
        notification_service.for_booking(
            self.db, self.booking, event_type=NotificationEventType.CHECK_IN,
            event_key=str(self.booking.id), title="Duplicate", body="Duplicate worker retry.",
        )
        self.db.commit()
        self.assertEqual({item.recipient_user_id for item in notices}, {self.customer.id, self.partner.id})
        self.assertEqual(self.db.scalar(select(func.count(Notification.id)).where(Notification.event_type == NotificationEventType.CHECK_IN)), 2)
        self.assertEqual(self.db.scalar(select(func.count(NotificationJob.id)).select_from(NotificationJob).join(Notification).where(Notification.event_type == NotificationEventType.CHECK_IN)), 6)
        self.assertEqual(notification_service.list_for_user(self.db, self.other_customer)[0], [])
        self.assertEqual(notification_service.list_for_user(self.db, self.other_partner)[0], [])


if __name__ == "__main__":
    unittest.main()
