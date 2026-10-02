"""Validation and idempotent upsert for the operator-run curated Place dataset."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.slug import slugify
from app.data.places.types import CuratedPlace
from app.models.destination import Destination, District
from app.models.place import Interest, Place, SpiritualTradition
from app.services import place_service


CURATED_MANAGED_FIELDS = (
    "name",
    "district relationship",
    "destination relationship",
    "short_description",
    "description",
    "image_url",
    "spiritual_tradition",
    "is_active",
    "is_featured",
    "display_order",
    "interest classifications",
)


class CuratedPlaceValidationError(ValueError):
    """Raised before writes when reviewed Place data cannot be resolved safely."""


@dataclass(frozen=True)
class SeedReport:
    created: int
    updated: int
    unchanged: int
    failed: int
    total_places: int
    places_by_interest: dict[str, int]
    places_by_district: dict[str, int]
    spiritual_representation: dict[str, int]

    def lines(self) -> list[str]:
        return [
            f"created={self.created} updated={self.updated} unchanged={self.unchanged} failed={self.failed}",
            f"total_places={self.total_places}",
            "places_by_interest=" + _format_counts(self.places_by_interest),
            "places_by_district=" + _format_counts(self.places_by_district),
            "spiritual_representation=" + _format_counts(self.spiritual_representation),
        ]


@dataclass(frozen=True)
class _ResolvedPlace:
    record: CuratedPlace
    slug: str
    district: District
    destination: Destination | None
    interests: tuple[Interest, ...]
    spiritual_tradition: SpiritualTradition | None


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}:{value}" for key, value in counts.items()) or "none"


def _fail(index: int, record: CuratedPlace, message: str) -> CuratedPlaceValidationError:
    label = record.name.strip() or f"record #{index + 1}"
    return CuratedPlaceValidationError(f"{label}: {message}")


def _validate_source(index: int, record: CuratedPlace) -> None:
    if not record.sources:
        raise _fail(index, record, "at least one authoritative source is required")
    for source in record.sources:
        if not source.source_name.strip():
            raise _fail(index, record, "source_name cannot be empty")
        parsed = urlparse(source.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise _fail(index, record, f"malformed source URL: {source.source_url!r}")
        if not isinstance(source.source_last_verified_at, date):
            raise _fail(index, record, "source_last_verified_at must be a date")
        if source.source_last_verified_at > date.today():
            raise _fail(index, record, "source_last_verified_at cannot be in the future")


def validate_curated_places(db: Session, records: tuple[CuratedPlace, ...]) -> tuple[_ResolvedPlace, ...]:
    """Resolve every reference and reject the complete batch before any writes."""
    districts = {item.slug: item for item in db.scalars(select(District))}
    interests = {item.slug: item for item in db.scalars(select(Interest))}
    destinations = {
        (item.district_id, item.slug): item
        for item in db.scalars(select(Destination))
    }
    seen: set[tuple[str, str]] = set()
    resolved: list[_ResolvedPlace] = []

    for index, record in enumerate(records):
        name = record.name.strip()
        if not name:
            raise _fail(index, record, "name is required")
        if len(name) > 160:
            raise _fail(index, record, "name exceeds 160 characters")
        if not record.short_description.strip() or not record.description.strip():
            raise _fail(index, record, "short_description and description are required")
        if len(record.short_description) > 500:
            raise _fail(index, record, "short_description exceeds 500 characters")
        if not isinstance(record.is_active, bool) or not isinstance(record.is_featured, bool):
            raise _fail(index, record, "visibility fields must be boolean")
        if isinstance(record.display_order, bool) or not isinstance(record.display_order, int) or record.display_order < 0:
            raise _fail(index, record, "display_order must be a non-negative integer")
        if record.image_url is not None and len(record.image_url) > 2048:
            raise _fail(index, record, "image_url exceeds 2048 characters")
        _validate_source(index, record)

        district_slug = record.district_slug.strip().lower()
        district = districts.get(district_slug)
        if district is None:
            raise _fail(index, record, f"unknown district slug {district_slug!r}")

        canonical_slug = record.slug.strip().lower() if record.slug else slugify(name, max_length=180)
        if slugify(canonical_slug, max_length=180) != canonical_slug:
            raise _fail(index, record, f"invalid canonical slug {record.slug!r}")
        identity = (district_slug, canonical_slug)
        if identity in seen:
            raise _fail(index, record, f"duplicate curated Place identity {district_slug}/{canonical_slug}")
        seen.add(identity)

        destination = None
        if record.destination_slug:
            destination_slug = record.destination_slug.strip().lower()
            destination = destinations.get((district.id, destination_slug))
            if destination is None:
                other = next((item for (district_id, slug), item in destinations.items() if slug == destination_slug and district_id != district.id), None)
                if other is not None:
                    raise _fail(index, record, f"destination {destination_slug!r} belongs to a different district")
                raise _fail(index, record, f"unknown destination slug {destination_slug!r} in district {district_slug!r}")

        if not record.interest_slugs:
            raise _fail(index, record, "at least one Interest is required")
        if len(set(record.interest_slugs)) != len(record.interest_slugs):
            raise _fail(index, record, "duplicate Interest slugs are not allowed")
        resolved_interests: list[Interest] = []
        for raw_slug in record.interest_slugs:
            interest_slug = raw_slug.strip().lower()
            interest = interests.get(interest_slug)
            if interest is None:
                raise _fail(index, record, f"unknown Interest slug {interest_slug!r}")
            resolved_interests.append(interest)

        tradition = None
        if record.spiritual_tradition is not None:
            try:
                tradition = SpiritualTradition(record.spiritual_tradition)
            except ValueError as error:
                raise _fail(index, record, f"invalid spiritual tradition {record.spiritual_tradition!r}") from error

        resolved.append(
            _ResolvedPlace(
                record=record,
                slug=canonical_slug,
                district=district,
                destination=destination,
                interests=tuple(resolved_interests),
                spiritual_tradition=tradition,
            )
        )
    return tuple(resolved)


def seed_curated_places(db: Session, records: tuple[CuratedPlace, ...]) -> SeedReport:
    """Atomically-ready upsert; the caller controls commit or rollback."""
    resolved = validate_curated_places(db, records)
    created = updated = unchanged = 0

    for item in resolved:
        record = item.record
        place = db.scalar(
            select(Place)
            .where(Place.district_id == item.district.id, Place.slug == item.slug)
            .options(selectinload(Place.interests))
        )
        if place is None:
            place_service.create_place(
                db,
                district=item.district,
                destination=item.destination,
                name=record.name,
                interests=list(item.interests),
                short_description=record.short_description,
                description=record.description,
                image_url=record.image_url,
                spiritual_tradition=item.spiritual_tradition,
                is_active=record.is_active,
                is_featured=record.is_featured,
                display_order=record.display_order,
            )
            created += 1
            continue

        # Admin-owned records and curated records intentionally changed by an
        # administrator are never reset by an idempotent dataset rerun.
        if place.content_source == "ADMIN" or place.admin_overridden:
            unchanged += 1
            continue

        changed = False
        managed_values = {
            "name": record.name,
            "destination_id": item.destination.id if item.destination else None,
            "short_description": record.short_description,
            "description": record.description,
            "image_url": record.image_url,
            "spiritual_tradition": item.spiritual_tradition,
            "is_active": record.is_active,
            "is_featured": record.is_featured,
            "display_order": record.display_order,
        }
        for field, value in managed_values.items():
            if getattr(place, field) != value:
                setattr(place, field, value)
                changed = True
        if {interest.id for interest in place.interests} != {interest.id for interest in item.interests}:
            place.interests = list(item.interests)
            changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1

    db.flush()
    return _build_report(db, created=created, updated=updated, unchanged=unchanged)


def _build_report(db: Session, *, created: int, updated: int, unchanged: int) -> SeedReport:
    places = list(
        db.scalars(
            select(Place).options(selectinload(Place.district), selectinload(Place.interests))
        ).unique()
    )
    by_interest: Counter[str] = Counter()
    by_district: Counter[str] = Counter()
    by_tradition: Counter[str] = Counter()
    for place in places:
        by_district[place.district.slug] += 1
        for interest in place.interests:
            by_interest[interest.slug] += 1
        by_tradition[place.spiritual_tradition.value if place.spiritual_tradition else "UNCLASSIFIED"] += 1
    return SeedReport(
        created=created,
        updated=updated,
        unchanged=unchanged,
        failed=0,
        total_places=len(places),
        places_by_interest=dict(sorted(by_interest.items())),
        places_by_district=dict(sorted(by_district.items())),
        spiritual_representation=dict(sorted(by_tradition.items())),
    )
