import unittest
from datetime import date, datetime, time, timezone
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.datastructures import Headers

from app.core.permission import require_admin, require_hotel_partner_only
from app.database import Base
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.audit import AuditLog
from app.models.hotel import Amenity, Hotel, HotelStatus, PropertyType, RoomType, RoomTypeStatus, RoomTypeVersion
from app.models.user import User, UserRole, UserStatus
from app.schemas.hotel import (
    MealAddOnOption,
    PartnerRoomTypeCreate,
    PartnerRoomTypeUpdate,
    RoomImageCreate,
    RoomTypeReviewRequest,
)
from app.services import partner_room_service


class TestPartnerRoomTypes(unittest.TestCase):
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

        # Seed amenities
        self.wifi = Amenity(name="Free Wi-Fi", slug="free-wifi", category="Internet", is_active=True)
        self.ac = Amenity(name="Air Conditioning", slug="air-conditioning", category="Climate", is_active=True)
        self.inactive_amenity = Amenity(name="Helipad", slug="helipad", category="Luxury", is_active=False)
        self.db.add_all([self.wifi, self.ac, self.inactive_amenity])
        self.db.commit()

        # Seed users
        self.admin = self._create_user("admin@platform.test", UserRole.ADMIN, "+919000000001")
        self.partner_a = self._create_user("partner_a@hotel.test", UserRole.HOTEL_PARTNER, "+919000000002")
        self.partner_b = self._create_user("partner_b@hotel.test", UserRole.HOTEL_PARTNER, "+919000000003")
        self.customer = self._create_user("customer@guest.test", UserRole.CUSTOMER, "+919000000004")

        # Seed hotels
        self.hotel_a = self._create_hotel(self.partner_a.id, "Grand Palace Mumbai", "grand-palace-mumbai")
        self.hotel_b = self._create_hotel(self.partner_b.id, "Ocean View Goa", "ocean-view-goa")

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _create_user(self, email: str, role: UserRole, phone: str) -> User:
        user = User(
            email=email,
            password_hash="hashed_pw_test",
            full_name=f"User {email}",
            role=role,
            status=UserStatus.ACTIVE,
            phone=phone,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_hotel(self, partner_id: int, name: str, slug: str) -> Hotel:
        hotel = Hotel(
            name=name,
            slug=slug,
            property_type=PropertyType.HOTEL,
            address_line1="123 Marine Drive",
            city="Mumbai",
            district="Mumbai",
            state="Maharashtra",
            country="India",
            postal_code="400001",
            check_in_time=time(14, 0),
            check_out_time=time(11, 0),
            partner_id=partner_id,
            status=HotelStatus.ACTIVE,
        )
        self.db.add(hotel)
        self.db.commit()
        self.db.refresh(hotel)
        return hotel

    def _valid_room_input(self, name: str = "Deluxe Sea View") -> PartnerRoomTypeCreate:
        return PartnerRoomTypeCreate(
            name=name,
            description="Spacious room with king bed and balcony.",
            max_adults=2,
            max_children=1,
            max_guests=3,
            bed_type="King Bed",
            bed_count=1,
            room_size_sqm=Decimal("35.50"),
            base_price=Decimal("4500.00"),
            currency="INR",
            total_rooms=10,
            extra_bed_rules="Rollaway bed available for child at INR 800/night",
            meal_add_on_options=[
                MealAddOnOption(name="Buffet Breakfast", price=Decimal("450.00"), currency="INR"),
                MealAddOnOption(name="Half Board (Dinner + Breakfast)", price=Decimal("1200.00"), currency="INR"),
            ],
            amenity_ids=[self.wifi.id, self.ac.id],
        )

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Tenant Isolation & Authorization
    # ──────────────────────────────────────────────────────────────────────────

    def test_customer_forbidden_from_partner_endpoints(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            require_hotel_partner_only(self.customer)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_partner_forbidden_from_admin_review(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            require_admin(self.partner_a)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_tenant_isolation_partner_cannot_access_other_hotel_rooms(self) -> None:
        # Partner A creates a room
        room_a = partner_room_service.create_partner_room(
            self.db, self.partner_a, self._valid_room_input("Suite Alpha")
        )

        # Partner B tries to get Partner A's room -> 404
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.get_partner_room(self.db, self.partner_b, room_a.id)
        self.assertEqual(ctx.exception.status_code, 404)

        # Partner B tries to update Partner A's room -> 404
        with self.assertRaises(HTTPException) as ctx:
            update_data = PartnerRoomTypeUpdate(**self._valid_room_input("Hacked Suite").model_dump())
            partner_room_service.update_partner_room(self.db, self.partner_b, room_a.id, update_data)
        self.assertEqual(ctx.exception.status_code, 404)

        # Partner B tries to delete Partner A's room -> 404
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.delete_partner_room(self.db, self.partner_b, room_a.id)
        self.assertEqual(ctx.exception.status_code, 404)

        # Partner B tries to submit Partner A's room -> 404
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.submit_partner_room(self.db, self.partner_b, room_a.id)
        self.assertEqual(ctx.exception.status_code, 404)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. CRUD & Validation
    # ──────────────────────────────────────────────────────────────────────────

    def test_create_room_type_as_draft(self) -> None:
        data = self._valid_room_input("Executive King Room")
        room = partner_room_service.create_partner_room(self.db, self.partner_a, data)

        self.assertEqual(room.name, "Executive King Room")
        self.assertEqual(room.status, RoomTypeStatus.DRAFT)
        self.assertEqual(room.bed_type, "King Bed")
        self.assertEqual(room.bed_count, 1)
        self.assertEqual(room.max_adults, 2)
        self.assertEqual(room.max_children, 1)
        self.assertEqual(room.max_guests, 3)
        self.assertEqual(room.base_price, Decimal("4500.00"))
        self.assertEqual(len(room.amenities), 2)
        self.assertEqual(len(room.meal_add_on_options), 2)
        self.assertIn("Rollaway bed", room.extra_bed_rules)
        self.assertEqual(room.version, 1)

    def test_duplicate_name_conflict(self) -> None:
        partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Standard Room"))
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Standard Room"))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_cannot_assign_inactive_amenity(self) -> None:
        invalid_data = self._valid_room_input("Luxury Suite")
        invalid_data.amenity_ids.append(self.inactive_amenity.id)
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.create_partner_room(self.db, self.partner_a, invalid_data)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_update_room_type(self) -> None:
        room = partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Original Room"))
        update_data = PartnerRoomTypeUpdate(
            name="Updated Deluxe Room",
            description="Updated description with more details.",
            max_adults=3,
            max_children=1,
            max_guests=4,
            bed_type="Queen Bed",
            bed_count=2,
            room_size_sqm=Decimal("42.00"),
            base_price=Decimal("5200.00"),
            currency="INR",
            total_rooms=15,
            extra_bed_rules="No extra bed allowed",
            meal_add_on_options=[
                MealAddOnOption(name="All Inclusive", price=Decimal("2000.00"), currency="INR"),
            ],
            amenity_ids=[self.wifi.id],
        )
        updated = partner_room_service.update_partner_room(self.db, self.partner_a, room.id, update_data)
        self.assertEqual(updated.name, "Updated Deluxe Room")
        self.assertEqual(updated.base_price, Decimal("5200.00"))
        self.assertEqual(len(updated.amenities), 1)
        self.assertEqual(len(updated.meal_add_on_options), 1)

    def test_delete_room_type_without_bookings(self) -> None:
        room = partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Temp Room"))
        partner_room_service.delete_partner_room(self.db, self.partner_a, room.id)
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.get_partner_room(self.db, self.partner_a, room.id)
        self.assertEqual(ctx.exception.status_code, 404)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Submission, Validation & Admin Review Flow
    # ──────────────────────────────────────────────────────────────────────────

    def test_submit_requires_description_and_image(self) -> None:
        # Create room without description
        data = self._valid_room_input("Incomplete Room")
        data.description = None
        room = partner_room_service.create_partner_room(self.db, self.partner_a, data)

        # Submit should fail: description missing
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.submit_partner_room(self.db, self.partner_a, room.id)
        self.assertEqual(ctx.exception.status_code, 422)

        # Add description, but no image yet
        update_data = PartnerRoomTypeUpdate(**data.model_dump())
        update_data.description = "A well-described room."
        room = partner_room_service.update_partner_room(self.db, self.partner_a, room.id, update_data)

        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.submit_partner_room(self.db, self.partner_a, room.id)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("image", ctx.exception.detail.lower())

        # Add image
        partner_room_service.add_partner_room_image(
            self.db,
            self.partner_a,
            room.id,
            RoomImageCreate(image_url="https://images.unsplash.com/photo-room.jpg", alt_text="Room photo", is_cover=True),
        )

        # Submit should now succeed -> PENDING
        submitted = partner_room_service.submit_partner_room(self.db, self.partner_a, room.id)
        self.assertEqual(submitted.status, RoomTypeStatus.PENDING)

    def test_admin_review_flow_and_partner_cannot_self_approve(self) -> None:
        room = partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Reviewable Room"))
        partner_room_service.add_partner_room_image(
            self.db,
            self.partner_a,
            room.id,
            RoomImageCreate(image_url="https://example.com/room.jpg", is_cover=True),
        )
        partner_room_service.submit_partner_room(self.db, self.partner_a, room.id)

        # 1. Admin requests changes with feedback notes
        review_req = RoomTypeReviewRequest(
            action=RoomTypeStatus.NEEDS_CHANGES,
            review_notes="Please provide higher resolution photos and clarify extra-bed pricing.",
        )
        reviewed = partner_room_service.review_room(self.db, self.admin, room.id, review_req)
        self.assertEqual(reviewed.status, RoomTypeStatus.NEEDS_CHANGES)
        self.assertEqual(reviewed.review_notes, "Please provide higher resolution photos and clarify extra-bed pricing.")
        audit = self.db.scalar(select(AuditLog).where(AuditLog.action == "ROOM_TYPE_REVIEWED", AuditLog.target_id == str(room.id)))
        self.assertIsNotNone(audit)
        self.assertEqual(audit.previous_value["status"], RoomTypeStatus.PENDING.value)
        self.assertEqual(audit.new_value["status"], RoomTypeStatus.NEEDS_CHANGES.value)
        queue = partner_room_service.list_admin_review_queue(self.db, RoomTypeStatus.NEEDS_CHANGES)
        self.assertIn(room.id, [item.id for item in queue])

        # 2. Partner edits to address changes -> status resets to DRAFT
        update_data = PartnerRoomTypeUpdate(
            **{**self._valid_room_input("Reviewable Room").model_dump(), "extra_bed_rules": "Extra bed INR 500 flat"}
        )
        partner_edit = partner_room_service.update_partner_room(self.db, self.partner_a, room.id, update_data)
        self.assertEqual(partner_edit.status, RoomTypeStatus.DRAFT)
        self.assertIsNone(partner_edit.review_notes)

        # Partner resubmits -> PENDING
        partner_room_service.submit_partner_room(self.db, self.partner_a, room.id)

        # 3. Admin approves
        approved = partner_room_service.review_room(
            self.db, self.admin, room.id, RoomTypeReviewRequest(action=RoomTypeStatus.APPROVED)
        )
        self.assertEqual(approved.status, RoomTypeStatus.APPROVED)

        # 4. Admin marks bookable
        bookable = partner_room_service.review_room(
            self.db, self.admin, room.id, RoomTypeReviewRequest(action=RoomTypeStatus.BOOKABLE)
        )
        self.assertEqual(bookable.status, RoomTypeStatus.BOOKABLE)

        # 5. Any partner edit on bookable room resets to DRAFT (partner cannot self-approve)
        re_edited = partner_room_service.update_partner_room(self.db, self.partner_a, room.id, update_data)
        self.assertEqual(re_edited.status, RoomTypeStatus.DRAFT)

    def test_cannot_mark_bookable_without_prior_approval(self) -> None:
        room = partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Draft Room"))
        # Room is in DRAFT, admin attempts to make directly BOOKABLE -> 422
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.review_room(
                self.db, self.admin, room.id, RoomTypeReviewRequest(action=RoomTypeStatus.BOOKABLE)
            )
        self.assertEqual(ctx.exception.status_code, 422)

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Versioning & Snapshots on Confirmed Bookings
    # ──────────────────────────────────────────────────────────────────────────

    def test_versioning_and_snapshot_when_confirmed_booking_exists(self) -> None:
        room = partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Presidential Suite"))
        partner_room_service.add_partner_room_image(
            self.db,
            self.partner_a,
            room.id,
            RoomImageCreate(image_url="https://example.com/suite.jpg", is_cover=True),
        )
        self.assertEqual(room.version, 1)

        # Simulate a confirmed booking on this room type
        confirmed_booking = Booking(
            booking_reference="BK-TEST-CONFIRMED-001",
            user_id=self.customer.id,
            hotel_id=self.hotel_a.id,
            room_type_id=room.id,
            check_in=date(2026, 10, 1),
            check_out=date(2026, 10, 5),
            rooms=1,
            adults=2,
            children=0,
            nights=4,
            currency="INR",
            subtotal=Decimal("18000.00"),
            taxes=Decimal("2160.00"),
            platform_fee=Decimal("200.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("20360.00"),
            status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
        )
        self.db.add(confirmed_booking)
        self.db.commit()

        # Partner edits the room's base price and name
        update_data = PartnerRoomTypeUpdate(
            name="Presidential Suite Renovated",
            description="Now fully renovated with jacuzzi.",
            max_adults=2,
            max_children=2,
            max_guests=4,
            bed_type="King Bed",
            bed_count=1,
            room_size_sqm=Decimal("55.00"),
            base_price=Decimal("9500.00"),  # Higher price
            currency="INR",
            total_rooms=10,
            extra_bed_rules="Free extra bed for toddlers",
            meal_add_on_options=[],
            amenity_ids=[self.wifi.id, self.ac.id],
        )
        updated = partner_room_service.update_partner_room(self.db, self.partner_a, room.id, update_data)

        # Version must increment to 2
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.base_price, Decimal("9500.00"))

        # Check that a snapshot was created in room_type_versions for version 1
        version_entry = self.db.query(RoomTypeVersion).filter_by(room_type_id=room.id, version=1).first()
        self.assertIsNotNone(version_entry)
        self.assertEqual(version_entry.reason, "partner_edit_after_confirmed_booking")
        self.assertEqual(version_entry.snapshot["name"], "Presidential Suite")
        self.assertEqual(version_entry.snapshot["base_price"], "4500.00")
        self.assertEqual(len(version_entry.snapshot["images"]), 1)

    def test_cannot_delete_room_type_with_confirmed_bookings(self) -> None:
        room = partner_room_service.create_partner_room(self.db, self.partner_a, self._valid_room_input("Booked Room"))
        booking = Booking(
            booking_reference="BK-TEST-CONFIRMED-002",
            user_id=self.customer.id,
            hotel_id=self.hotel_a.id,
            room_type_id=room.id,
            check_in=date(2026, 11, 1),
            check_out=date(2026, 11, 3),
            rooms=1,
            adults=2,
            children=0,
            nights=2,
            currency="INR",
            subtotal=Decimal("9000.00"),
            taxes=Decimal("1080.00"),
            platform_fee=Decimal("100.00"),
            discount=Decimal("0.00"),
            total_amount=Decimal("10180.00"),
            status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
        )
        self.db.add(booking)
        self.db.commit()

        # Attempt to delete should raise 400
        with self.assertRaises(HTTPException) as ctx:
            partner_room_service.delete_partner_room(self.db, self.partner_a, room.id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("confirmed bookings", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
