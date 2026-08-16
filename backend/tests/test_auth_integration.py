import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid

from sqlalchemy import delete

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user


BASE_URL = os.getenv("AUTH_TEST_BASE_URL", "http://127.0.0.1:8000/api/v1")


def request_json(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, object]]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def request_form(path: str, payload: dict[str, str]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


class AuthenticationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        suffix = uuid.uuid4().hex[:10]
        digits = str(uuid.uuid4().int)[-9:]
        cls.password = "StrongPass123"
        cls.user_email = f"auth-user-{suffix}@example.com"
        cls.admin_email = f"auth-admin-{suffix}@example.com"
        cls.other_email = f"auth-other-{suffix}@example.com"
        cls.user_phone = f"+919{digits}"
        cls.admin_phone = f"+918{digits}"
        cls.other_phone = f"+917{digits}"
        cls.emails = [cls.user_email, cls.admin_email, cls.other_email]

        with SessionLocal() as db:
            db.execute(delete(User).where(User.email.in_(cls.emails)))
            db.commit()
            create_user(
                db,
                full_name="Auth Test Admin",
                email=cls.admin_email,
                phone=cls.admin_phone,
                password_hash=hash_password(cls.password),
                role=UserRole.ADMIN,
            )

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email.in_(cls.emails)))
            db.commit()

    def test_authentication_flow(self) -> None:
        status_code, registered = request_json(
            "POST",
            "/auth/register",
            {
                "full_name": "Auth Test User",
                "email": self.user_email,
                "phone": self.user_phone,
                "password": self.password,
            },
        )
        self.assertEqual(status_code, 201, registered)
        self.assertEqual(registered["role"], "USER")
        self.assertNotIn("password", registered)
        self.assertNotIn("password_hash", registered)

        status_code, body = request_json(
            "POST",
            "/auth/register",
            {
                "full_name": "Duplicate Email",
                "email": self.user_email,
                "phone": self.other_phone,
                "password": self.password,
            },
        )
        self.assertEqual(status_code, 409, body)

        status_code, body = request_json(
            "POST",
            "/auth/register",
            {
                "full_name": "Duplicate Phone",
                "email": self.other_email,
                "phone": self.user_phone,
                "password": self.password,
            },
        )
        self.assertEqual(status_code, 409, body)

        status_code, login = request_json(
            "POST",
            "/auth/login",
            {"email": self.user_email, "password": self.password},
        )
        self.assertEqual(status_code, 200, login)
        access_token = str(login["access_token"])
        refresh_token = str(login["refresh_token"])

        status_code, oauth2_login = request_form(
            "/auth/token",
            {
                "username": self.user_email,
                "password": self.password,
                "grant_type": "password",
            },
        )
        self.assertEqual(status_code, 200, oauth2_login)
        self.assertEqual(oauth2_login["token_type"], "bearer")
        oauth2_access_token = str(oauth2_login["access_token"])

        status_code, body = request_form(
            "/auth/token",
            {
                "username": self.user_email,
                "password": "WrongPassword123",
                "grant_type": "password",
            },
        )
        self.assertEqual(status_code, 401, body)

        status_code, body = request_json(
            "POST",
            "/auth/login",
            {"email": self.user_email, "password": "WrongPassword123"},
        )
        self.assertEqual(status_code, 401, body)

        status_code, body = request_json("GET", "/users/me")
        self.assertEqual(status_code, 401, body)

        status_code, current_user = request_json("GET", "/users/me", token=oauth2_access_token)
        self.assertEqual(status_code, 200, current_user)
        self.assertEqual(current_user["email"], self.user_email)

        status_code, body = request_json("GET", "/admin/test", token=oauth2_access_token)
        self.assertEqual(status_code, 403, body)

        status_code, admin_login = request_json(
            "POST",
            "/auth/login",
            {"email": self.admin_email, "password": self.password},
        )
        self.assertEqual(status_code, 200, admin_login)
        status_code, body = request_json(
            "GET",
            "/admin/test",
            token=str(admin_login["access_token"]),
        )
        self.assertEqual(status_code, 200, body)

        status_code, refreshed = request_json(
            "POST",
            "/auth/refresh",
            {"refresh_token": refresh_token},
        )
        self.assertEqual(status_code, 200, refreshed)
        self.assertIn("access_token", refreshed)

        status_code, body = request_json(
            "POST",
            "/auth/refresh",
            {"refresh_token": access_token},
        )
        self.assertEqual(status_code, 401, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
