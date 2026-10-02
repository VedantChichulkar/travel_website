import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.permission import require_admin, require_customer, require_hotel_partner
from app.core.security import hash_password
from app.database import Base
from app.models.user import User, UserRole, UserStatus
from app.repositories.user_repository import create_user
from app.services.auth_service import authenticate_user


class RolePortalAuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.SessionLocal()
        self.password = "StrongPassword123"
        self.customer = self._user("customer@example.com", "+919000000201", UserRole.CUSTOMER)
        self.partner = self._user("partner@example.com", "+919000000202", UserRole.HOTEL_PARTNER)
        self.admin = self._user("admin@example.com", "+919000000203", UserRole.ADMIN)

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def _user(self, email: str, phone: str, role: UserRole) -> User:
        return create_user(
            self.db,
            full_name=f"{role.value.title()} Account",
            email=email,
            phone=phone,
            password_hash=hash_password(self.password),
            role=role,
            status=UserStatus.ACTIVE,
        )

    def test_each_role_can_use_its_own_portal(self) -> None:
        cases = (
            (self.customer, UserRole.CUSTOMER),
            (self.partner, UserRole.HOTEL_PARTNER),
            (self.admin, UserRole.ADMIN),
        )
        for user, portal in cases:
            with self.subTest(portal=portal.value):
                authenticated = authenticate_user(self.db, user.email, self.password, portal=portal)
                self.assertEqual(authenticated.id, user.id)

    def test_wrong_portals_are_rejected_before_tokens_can_be_created(self) -> None:
        cases = (
            (self.customer, UserRole.HOTEL_PARTNER, "CUSTOMER", "/login"),
            (self.customer, UserRole.ADMIN, "CUSTOMER", "/login"),
            (self.partner, UserRole.CUSTOMER, "HOTEL_PARTNER", "/partner/login"),
            (self.partner, UserRole.ADMIN, "HOTEL_PARTNER", "/partner/login"),
            (self.admin, UserRole.CUSTOMER, "ADMIN", "/admin/login"),
            (self.admin, UserRole.HOTEL_PARTNER, "ADMIN", "/admin/login"),
        )
        for user, portal, account_role, portal_path in cases:
            with self.subTest(user=user.email, portal=portal.value):
                with self.assertRaises(HTTPException) as raised:
                    authenticate_user(self.db, user.email, self.password, portal=portal)
                self.assertEqual(raised.exception.status_code, 403)
                self.assertEqual(raised.exception.detail["code"], "WRONG_PORTAL")
                self.assertEqual(raised.exception.detail["account_role"], account_role)
                self.assertEqual(raised.exception.detail["portal_path"], portal_path)

    def test_server_side_role_guards_reject_cross_portal_access(self) -> None:
        self.assertEqual(require_customer(self.customer).id, self.customer.id)
        self.assertEqual(require_hotel_partner(self.partner).id, self.partner.id)
        self.assertEqual(require_admin(self.admin).id, self.admin.id)
        for guard, user in (
            (require_customer, self.partner),
            (require_customer, self.admin),
            (require_hotel_partner, self.customer),
            (require_hotel_partner, self.admin),
            (require_admin, self.customer),
            (require_admin, self.partner),
        ):
            with self.subTest(guard=guard.__name__, role=user.role.value):
                with self.assertRaises(HTTPException) as raised:
                    guard(user)
                self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
