import asyncio
import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid

from sqlalchemy import delete
from app.main import app
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user


BASE_URL = os.getenv("AUTH_TEST_BASE_URL")
API_PREFIX = "/api/v1"


def _asgi_request(method: str, path: str, body: bytes | None, headers: dict[str, str]) -> tuple[int, bytes, list[tuple[bytes, bytes]]]:
    """Exercise the real ASGI stack without a separately managed web server."""
    parsed = urllib.parse.urlsplit(f"{API_PREFIX}{path}")
    response_status = 500
    response_body = bytearray()
    response_headers: list[tuple[bytes, bytes]] = []
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body or b"", "more_body": False}

    async def send(message):
        nonlocal response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("ascii"),
        "query_string": parsed.query.encode("ascii"),
        "root_path": "",
        "headers": [(key.lower().encode("ascii"), value.encode("latin-1")) for key, value in {"host": "testserver", **headers}.items()],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "state": {},
    }
    asyncio.run(app(scope, receive, send))
    return response_status, bytes(response_body), response_headers


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

    if BASE_URL is None:
        status_code, response_body, _ = _asgi_request(method, path, body, headers)
        return status_code, json.loads(response_body) if response_body else {}

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, json.loads(body) if body else {}


def request_form(path: str, payload: dict[str, str]) -> tuple[int, dict[str, object]]:
    if BASE_URL is None:
        body = urllib.parse.urlencode(payload).encode("utf-8")
        status_code, response_body, _ = _asgi_request("POST", path, body, {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
        return status_code, json.loads(response_body) if response_body else {}

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
            body = response.read()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, json.loads(body) if body else {}


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
        self.assertEqual(registered["role"], "CUSTOMER")
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
            {"email": self.user_email, "password": self.password, "portal": "CUSTOMER"},
        )
        self.assertEqual(status_code, 200, login)
        access_token = str(login["access_token"])
        self.assertNotIn("refresh_token", login)

        if BASE_URL is None:
            login_payload = json.dumps({"email": self.user_email, "password": self.password, "portal": "CUSTOMER"}).encode("utf-8")
            cookie_status, _, cookie_headers = _asgi_request(
                "POST",
                "/auth/login",
                login_payload,
                {"Accept": "application/json", "Content-Type": "application/json"},
            )
            self.assertEqual(cookie_status, 200)
            set_cookie = next(value.decode("latin-1") for key, value in cookie_headers if key.lower() == b"set-cookie")
            self.assertIn("HttpOnly", set_cookie)
            self.assertIn("SameSite=lax", set_cookie)
            cookie = set_cookie.split(";", 1)[0]
            refresh_status, refresh_body, _ = _asgi_request(
                "POST",
                "/auth/refresh",
                b"{}",
                {"Accept": "application/json", "Content-Type": "application/json", "Cookie": cookie},
            )
            self.assertEqual(refresh_status, 200, refresh_body)

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
        refresh_token = str(oauth2_login["refresh_token"])

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

        status_code, body = request_json("GET", "/admin/control/overview", token=oauth2_access_token)
        self.assertEqual(status_code, 403, body)

        status_code, admin_login = request_json(
            "POST",
            "/auth/login",
            {"email": self.admin_email, "password": self.password, "portal": "ADMIN"},
        )
        self.assertEqual(status_code, 200, admin_login)
        status_code, body = request_json(
            "GET",
            "/admin/control/overview",
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
