import unittest
from datetime import datetime, timezone
from pydantic import ValidationError

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_phone,
    update_last_login,
)
from app.services.auth_service import authenticate_user, register_user
from app.schemas.user import UserCreate, UserResponse


class TestUsersEntityUnit(unittest.TestCase):
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

    def test_user_creation_and_defaults(self) -> None:
        raw_password = "SecurePassword123"
        hashed = hash_password(raw_password)

        user = create_user(
            self.db,
            full_name="Priya Sharma",
            email="Priya.Sharma@Example.COM",
            phone="+919876543210",
            password_hash=hashed,
            role=UserRole.CUSTOMER,
        )

        self.assertIsNotNone(user.id)
        self.assertEqual(user.full_name, "Priya Sharma")
        # Email must be normalized to lowercase
        self.assertEqual(user.email, "priya.sharma@example.com")
        self.assertEqual(user.phone, "+919876543210")
        self.assertEqual(user.role, UserRole.CUSTOMER)
        self.assertEqual(user.status, UserStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.is_phone_verified)
        self.assertIsNone(user.last_login_at)
        self.assertTrue(verify_password(raw_password, user.password_hash))

    def test_email_case_insensitivity_lookup(self) -> None:
        create_user(
            self.db,
            full_name="Rohan Joshi",
            email="rohan.joshi@example.com",
            phone="+919876543211",
            password_hash=hash_password("StrongPassword123"),
            role=UserRole.CUSTOMER,
        )

        user_upper = get_user_by_email(self.db, "ROHAN.JOSHI@EXAMPLE.COM")
        self.assertIsNotNone(user_upper)
        self.assertEqual(user_upper.email, "rohan.joshi@example.com")

    def test_register_user_service_success(self) -> None:
        data = UserCreate(
            full_name="Anil Patil",
            email="anil.patil@example.com",
            phone="+919876543212",
            password="ValidPassword999",
            role=UserRole.CUSTOMER,
        )
        user = register_user(self.db, data)
        self.assertEqual(user.email, "anil.patil@example.com")
        self.assertEqual(user.role, UserRole.CUSTOMER)
        self.assertEqual(user.status, UserStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.is_phone_verified)
        self.assertIsNone(user.last_login_at)

        # Ensure UserResponse serialization works and excludes password_hash
        response_model = UserResponse.model_validate(user)
        dumped = response_model.model_dump()
        self.assertNotIn("password_hash", dumped)
        self.assertNotIn("password", dumped)
        self.assertEqual(dumped["role"], UserRole.CUSTOMER)

    def test_schema_rejects_admin_role_on_public_registration(self) -> None:
        with self.assertRaises(ValidationError):
            UserCreate(
                full_name="Malicious User",
                email="hacker@example.com",
                phone="+919876543213",
                password="Password123",
                role=UserRole.ADMIN,
            )

    def test_schema_phone_validation_e164(self) -> None:
        # Invalid phone format should fail
        with self.assertRaises(ValidationError):
            UserCreate(
                full_name="Test User",
                email="test@example.com",
                phone="12345",
                password="Password123",
            )

    def test_schema_password_complexity_validation(self) -> None:
        # No number
        with self.assertRaises(ValidationError):
            UserCreate(
                full_name="Test User",
                email="test@example.com",
                phone="+919876543214",
                password="OnlyLettersNoNumber",
            )
        # No uppercase
        with self.assertRaises(ValidationError):
            UserCreate(
                full_name="Test User",
                email="test@example.com",
                phone="+919876543214",
                password="nouppercase123",
            )
        # Too short (<8 chars)
        with self.assertRaises(ValidationError):
            UserCreate(
                full_name="Test User",
                email="test@example.com",
                phone="+919876543214",
                password="Sh1",
            )

    def test_duplicate_email_conflict(self) -> None:
        data1 = UserCreate(
            full_name="First User",
            email="same.email@example.com",
            phone="+919876543215",
            password="Password123",
        )
        register_user(self.db, data1)

        data2 = UserCreate(
            full_name="Second User",
            email="SAME.EMAIL@example.com",
            phone="+919876543216",
            password="Password123",
        )
        with self.assertRaises(HTTPException) as ctx:
            register_user(self.db, data2)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_duplicate_phone_conflict(self) -> None:
        data1 = UserCreate(
            full_name="First User",
            email="first@example.com",
            phone="+919876543217",
            password="Password123",
        )
        register_user(self.db, data1)

        data2 = UserCreate(
            full_name="Second User",
            email="second@example.com",
            phone="+919876543217",
            password="Password123",
        )
        with self.assertRaises(HTTPException) as ctx:
            register_user(self.db, data2)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_authenticate_success_and_last_login_updated(self) -> None:
        data = UserCreate(
            full_name="Suresh Deshmukh",
            email="suresh@example.com",
            phone="+919876543218",
            password="CorrectPassword1",
        )
        registered = register_user(self.db, data)
        self.assertIsNone(registered.last_login_at)

        authenticated = authenticate_user(self.db, "SURESH@EXAMPLE.COM", "CorrectPassword1")
        self.assertEqual(authenticated.id, registered.id)
        self.assertIsNotNone(authenticated.last_login_at)

    def test_authenticate_invalid_password(self) -> None:
        data = UserCreate(
            full_name="Kavita R",
            email="kavita@example.com",
            phone="+919876543219",
            password="CorrectPassword1",
        )
        register_user(self.db, data)

        with self.assertRaises(HTTPException) as ctx:
            authenticate_user(self.db, "kavita@example.com", "WrongPassword999")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_suspended_or_inactive_user_cannot_authenticate(self) -> None:
        create_user(
            self.db,
            full_name="Suspended Partner",
            email="suspended@example.com",
            phone="+919876543220",
            password_hash=hash_password("PartnerPassword1"),
            role=UserRole.HOTEL_PARTNER,
            status=UserStatus.SUSPENDED,
            is_active=False,
        )

        with self.assertRaises(HTTPException) as ctx:
            authenticate_user(self.db, "suspended@example.com", "PartnerPassword1")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Account is inactive or suspended", ctx.exception.detail)

    def test_token_generation_and_payload(self) -> None:
        user = create_user(
            self.db,
            full_name="Hotel Manager",
            email="manager@hotel.example",
            phone="+919876543221",
            password_hash=hash_password("ManagerPassword1"),
            role=UserRole.HOTEL_PARTNER,
        )

        access_token = create_access_token(user, "unit-test-session")
        refresh_token = create_refresh_token(user, "unit-test-session")

        access_payload = decode_token(access_token)
        self.assertEqual(access_payload["sub"], str(user.id))
        self.assertEqual(access_payload["role"], "HOTEL_PARTNER")
        self.assertEqual(access_payload["type"], "access")

        refresh_payload = decode_token(refresh_token)
        self.assertEqual(refresh_payload["sub"], str(user.id))
        self.assertEqual(refresh_payload["type"], "refresh")


if __name__ == "__main__":
    unittest.main(verbosity=2)
