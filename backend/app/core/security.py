from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import hashlib
from jose import jwt

from app.core.config import settings
from app.models.user import User, UserRole


ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("password must not exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(user: User, token_type: TokenType, expires_delta: timedelta, session_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "role": user.role.value,
        "type": token_type,
        "sid": session_id,
        "ver": user.auth_version,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user: User, session_id: str) -> str:
    return _create_token(
        user,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        session_id,
    )


def create_refresh_token(user: User, session_id: str) -> str:
    return _create_token(
        user,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        session_id,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
