"""Shared URL-slug normalization and collision handling."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session


_SEPARATOR = re.compile(r"[^a-z0-9]+")


def slugify(value: str, *, max_length: int = 140) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip())
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SEPARATOR.sub("-", ascii_value).strip("-")
    slug = slug[:max_length].rstrip("-")
    if not slug:
        raise ValueError("A URL-safe slug cannot be generated from this name")
    return slug


def unique_slug(
    db: Session,
    model,
    value: str,
    *,
    scope=(),
    max_length: int = 140,
) -> str:
    base = slugify(value, max_length=max_length)
    candidate = base
    counter = 2
    while db.scalar(select(model.id).where(model.slug == candidate, *scope)) is not None:
        suffix = f"-{counter}"
        candidate = f"{base[:max_length - len(suffix)].rstrip('-')}{suffix}"
        counter += 1
    return candidate
