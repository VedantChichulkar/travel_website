import unittest
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, PropertyType, RoomType
from app.models.review import Review, ReviewChallenge, ReviewChallengeReason, ReviewChallengeStatus, ReviewModerationEvent, ReviewModerationStatus, ReviewResponse, ReviewRiskLevel
from app.models.user import User, UserRole
from app.schemas.review import ModerationAction, ReviewChallengeCreate, ReviewCreate
from app.services import review_service


class ReviewIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        with SessionLocal() as db:
            customer = User(full_name="Verified Guest", email=f"review-guest-{suffix}@example.com", phone=f"+919{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.CUSTOMER)
            other_customer = User(full_name="Other Guest", email=f"review-other-guest-{suffix}@example.com", phone=f"+918{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.CUSTOMER)
            partner = User(full_name="Review Partner", email=f"review-partner-{suffix}@example.com", phone=f"+917{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            other_partner = User(full_name="Other Review Partner", email=f"review-other-partner-{suffix}@example.com", phone=f"+916{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.HOTEL_PARTNER)
            admin = User(full_name="Review Admin", email=f"review-admin-{suffix}@example.com", phone=f"+915{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password("StrongPass123"), role=UserRole.ADMIN)
            db.add_all([customer, other_customer, partner, other_partner, admin]); db.flush()
            hotel = Hotel(name="Reviewed Hotel", slug=f"reviewed-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=partner.id, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="1 Review Road", city="Mumbai", state="Maharashtra", country="India", postal_code="400001", check_in_time=time(14), check_out_time=time(11))
            other_hotel = Hotel(name="Other Reviewed Hotel", slug=f"reviewed-other-{suffix}", property_type=PropertyType.HOTEL, star_rating=Decimal("4"), status=HotelStatus.ACTIVE, partner_id=other_partner.id, partner_booking_gateway_status=BookingGatewayStatus.ACTIVE, address_line1="2 Review Road", city="Mumbai", state="Maharashtra", country="India", postal_code="400002", check_in_time=time(14), check_out_time=time(11))
            db.add_all([hotel, other_hotel]); db.flush()
            room = RoomType(hotel_id=hotel.id, name="Review Room", max_adults=2, max_children=0, max_guests=2, bed_type="King", bed_count=1, base_price=Decimal("1000"), currency="INR", total_rooms=2, is_active=True)
            db.add(room); db.flush()
            cls.customer_id, cls.other_customer_id, cls.partner_id, cls.other_partner_id, cls.admin_id = customer.id, other_customer.id, partner.id, other_partner.id, admin.id
            cls.hotel_id, cls.other_hotel_id, cls.room_id = hotel.id, other_hotel.id, room.id
            db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            booking_ids = list(db.scalars(select(Booking.id).where(Booking.user_id.in_([cls.customer_id, cls.other_customer_id]))))
            review_ids = list(db.scalars(select(Review.id).where(Review.booking_id.in_(booking_ids)))) if booking_ids else []
            if review_ids:
                db.execute(delete(ReviewModerationEvent).where(ReviewModerationEvent.review_id.in_(review_ids)))
                db.execute(delete(ReviewChallenge).where(ReviewChallenge.review_id.in_(review_ids)))
                db.execute(delete(ReviewResponse).where(ReviewResponse.review_id.in_(review_ids)))
                db.execute(delete(Review).where(Review.id.in_(review_ids)))
            if booking_ids:
                db.execute(delete(Booking).where(Booking.id.in_(booking_ids)))
            db.execute(delete(RoomType).where(RoomType.id == cls.room_id))
            db.execute(delete(Hotel).where(Hotel.id.in_([cls.hotel_id, cls.other_hotel_id])))
            db.execute(delete(User).where(User.id.in_([cls.customer_id, cls.other_customer_id, cls.partner_id, cls.other_partner_id, cls.admin_id])))
            db.commit()

    def _booking(self, db, status: BookingStatus = BookingStatus.CHECKED_OUT) -> Booking:
        booking = Booking(booking_reference=f"VYR-REV-{uuid.uuid4().hex[:12].upper()}", user_id=self.customer_id, hotel_id=self.hotel_id, room_type_id=self.room_id, check_in=date(2026, 8, 1), check_out=date(2026, 8, 2), rooms=1, adults=1, children=0, nights=1, currency="INR", subtotal=Decimal("1000"), taxes=Decimal("120"), platform_fee=Decimal("0"), discount=Decimal("0"), total_amount=Decimal("1120"), room_snapshot={}, price_snapshot={}, policy_snapshot={}, status=status, payment_status=PaymentStatus.PAID, checked_out_at=datetime(2026, 8, 2, 11, tzinfo=timezone.utc) if status == BookingStatus.CHECKED_OUT else None)
        db.add(booking); db.commit(); db.refresh(booking)
        return booking

    def _data(self, text: str = "The room was comfortable and the staff were helpful.", overall: int = 4) -> ReviewCreate:
        return ReviewCreate(overall_rating=overall, cleanliness_rating=4, service_rating=4, location_rating=5, room_quality_rating=4, value_rating=4, review_text=text)

    def test_eligible_ineligible_duplicate_and_customer_isolation(self) -> None:
        with SessionLocal() as db:
            customer, other, partner = db.get(User, self.customer_id), db.get(User, self.other_customer_id), db.get(User, self.partner_id)
            incomplete = self._booking(db, BookingStatus.CONFIRMED)
            with self.assertRaises(HTTPException) as forbidden:
                review_service.create_review(db, partner, incomplete.id, self._data())
            self.assertEqual(forbidden.exception.status_code, 403)
            with self.assertRaises(HTTPException) as ineligible:
                review_service.create_review(db, customer, incomplete.id, self._data())
            self.assertEqual(ineligible.exception.status_code, 409)
            completed = self._booking(db)
            with self.assertRaises(HTTPException) as hidden:
                review_service.create_review(db, other, completed.id, self._data())
            self.assertEqual(hidden.exception.status_code, 404)
            review = review_service.create_review(db, customer, completed.id, self._data())
            self.assertTrue(review.verified_stay)
            self.assertEqual(review.moderation_status, ReviewModerationStatus.PUBLISHED)
            with self.assertRaises(HTTPException) as duplicate:
                review_service.create_review(db, customer, completed.id, self._data())
            self.assertEqual(duplicate.exception.status_code, 409)

    def test_normal_negative_is_published_and_high_risk_is_moderated(self) -> None:
        with SessionLocal() as db:
            customer, admin = db.get(User, self.customer_id), db.get(User, self.admin_id)
            negative = review_service.create_review(db, customer, self._booking(db).id, self._data("The service was slow and the room was noisy throughout the night.", 1))
            self.assertEqual(negative.moderation_status, ReviewModerationStatus.PUBLISHED)
            risky = review_service.create_review(db, customer, self._booking(db).id, self._data("Contact me at guest@example.com because this includes personal information."))
            self.assertEqual(risky.risk_level, ReviewRiskLevel.HIGH)
            self.assertEqual(risky.moderation_status, ReviewModerationStatus.PENDING_REVIEW)
            public_ids = [item.id for item in review_service.list_public(db, self.hotel_id)]
            self.assertIn(negative.id, public_ids)
            self.assertNotIn(risky.id, public_ids)
            self.assertNotIn(risky.id, [item.id for item in review_service.list_partner(db, db.get(User, self.partner_id))])
            queue_ids = [item.id for item in review_service.list_admin_queue(db)]
            self.assertIn(risky.id, queue_ids)
            published = review_service.moderate(db, admin, risky.id, ModerationAction.PUBLISH, "Personal information reviewed and content approved")
            self.assertEqual(published.moderation_status, ReviewModerationStatus.PUBLISHED)

    def test_hotel_response_tenant_isolation_and_customer_content_immutability(self) -> None:
        with SessionLocal() as db:
            customer, partner, other_partner = db.get(User, self.customer_id), db.get(User, self.partner_id), db.get(User, self.other_partner_id)
            review = review_service.create_review(db, customer, self._booking(db).id, self._data())
            with self.assertRaises(HTTPException) as hidden:
                review_service.respond(db, other_partner, review.id, "This response must not be accepted.")
            self.assertEqual(hidden.exception.status_code, 404)
            responded = review_service.respond(db, partner, review.id, "Thank you for staying with us.")
            self.assertEqual(responded.hotel_response.responded_by_user_id, self.partner_id)
            with self.assertRaises(HTTPException):
                review_service.respond(db, partner, review.id, "Replacement response")
            responded.review_text = "Hotel attempted to rewrite the guest review."
            with self.assertRaises(ValueError):
                db.commit()
            db.rollback()

    def test_challenge_and_admin_moderation(self) -> None:
        with SessionLocal() as db:
            customer, partner, other_partner, admin = db.get(User, self.customer_id), db.get(User, self.partner_id), db.get(User, self.other_partner_id), db.get(User, self.admin_id)
            review = review_service.create_review(db, customer, self._booking(db).id, self._data("The stay was acceptable but the listing showed the wrong tower."))
            with self.assertRaises(HTTPException):
                review_service.challenge(db, other_partner, review.id, ReviewChallengeCreate(reason=ReviewChallengeReason.WRONG_PROPERTY, details="This booking does not belong to this property."))
            challenged = review_service.challenge(db, partner, review.id, ReviewChallengeCreate(reason=ReviewChallengeReason.WRONG_PROPERTY, details="The review describes a different tower and room type."))
            self.assertEqual(challenged.challenge.status, ReviewChallengeStatus.OPEN)
            self.assertEqual(challenged.moderation_status, ReviewModerationStatus.PUBLISHED)
            self.assertIn(review.id, [item.id for item in review_service.list_public(db, self.hotel_id)])
            with self.assertRaises(HTTPException) as forbidden:
                review_service.moderate(db, partner, review.id, ModerationAction.REJECT, "Partner cannot moderate")
            self.assertEqual(forbidden.exception.status_code, 403)
            moderated = review_service.moderate(db, admin, review.id, ModerationAction.REJECT, "Booking evidence confirms the wrong property was described")
            self.assertEqual(moderated.moderation_status, ReviewModerationStatus.REJECTED)
            self.assertEqual(moderated.challenge.status, ReviewChallengeStatus.UPHELD)
            self.assertNotIn(review.id, [item.id for item in review_service.list_public(db, self.hotel_id)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
