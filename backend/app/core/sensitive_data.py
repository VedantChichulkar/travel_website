"""Encryption and masking helpers for narrowly scoped sensitive fields."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import String, Text, TypeDecorator

from app.core.config import settings


PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    material = settings.DATA_ENCRYPTION_KEY or f"development-only:{settings.SECRET_KEY}"
    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_sensitive(value: str | None) -> str | None:
    if not value or value.startswith(PREFIX):
        return value
    return PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_sensitive(value: str | None) -> str | None:
    if not value or not value.startswith(PREFIX):
        # Transitional support for rows created before the encryption migration.
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Sensitive value cannot be decrypted with the configured key") from exc


class EncryptedString(TypeDecorator[str]):
    """Application-level encryption; ciphertext is all the database can observe."""

    impl = String
    cache_ok = True

    def __init__(self, length: int = 1024, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        del dialect
        return encrypt_sensitive(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        del dialect
        return decrypt_sensitive(value)


class EncryptedText(TypeDecorator[str]):
    """Encrypted text for sensitive values that can exceed VARCHAR limits."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        del dialect
        return encrypt_sensitive(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        del dialect
        return decrypt_sensitive(value)


def mask_tail(value: str | None, visible: int = 4) -> str | None:
    if not value:
        return None
    tail = value[-visible:]
    return f"{'*' * max(4, len(value) - visible)}{tail}"
