from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.destination import Destination, District
from app.models.discovery_content import DestinationMedia, PlaceMedia
from app.models.place import Place


def get_district(db: Session, district_id: int) -> District | None:
    return db.get(District, district_id)


def get_district_by_slug(db: Session, slug: str, *, active_only: bool = True) -> District | None:
    statement = select(District).where(District.slug == slug.strip().lower())
    if active_only:
        statement = statement.where(District.is_active.is_(True))
    return db.scalar(statement)


def get_district_by_identity(db: Session, value: str, *, active_only: bool = True) -> District | None:
    normalized = value.strip().lower()
    statement = select(District).where(
        or_(District.slug == normalized, func.lower(District.name) == normalized)
    )
    if active_only:
        statement = statement.where(District.is_active.is_(True))
    return db.scalar(statement)


def list_districts(db: Session, *, query: str | None = None) -> list[District]:
    statement = select(District).where(District.is_active.is_(True))
    if query:
        term = f"%{query.strip()}%"
        statement = statement.where(
            or_(District.name.ilike(term), District.slug.ilike(term), District.division.ilike(term))
        )
    return list(db.scalars(statement.order_by(District.name)))


def list_destinations(db: Session, district_id: int) -> list[Destination]:
    return list(
        db.scalars(
            select(Destination)
            .where(Destination.district_id == district_id, Destination.is_active.is_(True))
            .options(selectinload(Destination.district))
            .options(selectinload(Destination.media_asset))
            .order_by(Destination.name)
        )
    )


def get_destination_by_identity(
    db: Session, district_id: int, value: str, *, active_only: bool = True
) -> Destination | None:
    normalized = value.strip().lower()
    statement = select(Destination).where(
        Destination.district_id == district_id,
        or_(Destination.slug == normalized, func.lower(Destination.name) == normalized),
    ).options(
        selectinload(Destination.district), selectinload(Destination.media_asset),
        selectinload(Destination.faqs),
        selectinload(Destination.media_items).selectinload(DestinationMedia.asset),
        selectinload(Destination.places).selectinload(Place.district),
        selectinload(Destination.places).selectinload(Place.destination),
        selectinload(Destination.places).selectinload(Place.interests),
        selectinload(Destination.places).selectinload(Place.media_asset),
    )
    if active_only:
        statement = statement.where(Destination.is_active.is_(True))
    return db.scalar(statement)


def find_destinations(db: Session, value: str) -> list[Destination]:
    normalized = value.strip().lower()
    return list(
        db.scalars(
            select(Destination)
            .join(District)
            .where(
                Destination.is_active.is_(True),
                District.is_active.is_(True),
                or_(Destination.slug == normalized, func.lower(Destination.name) == normalized),
            )
            .options(selectinload(Destination.district))
            .order_by(District.name, Destination.name)
        )
    )


def search(
    db: Session, query: str, *, limit: int, include_places: bool = False
) -> tuple[list[District], list[Destination], list[Place]]:
    term = f"%{query.strip()}%"
    districts = list(
        db.scalars(
            select(District)
            .where(District.is_active.is_(True), or_(District.name.ilike(term), District.slug.ilike(term)))
            .order_by(District.name)
            .limit(limit)
        )
    )
    remaining = max(0, limit - len(districts))
    destinations = list(
        db.scalars(
            select(Destination)
            .join(District)
            .where(
                Destination.is_active.is_(True),
                District.is_active.is_(True),
                or_(Destination.name.ilike(term), Destination.slug.ilike(term)),
            )
            .options(selectinload(Destination.district))
            .order_by(Destination.name)
            .limit(remaining)
        )
    )
    remaining = max(0, remaining - len(destinations))
    places = []
    if include_places and remaining:
        places = list(
            db.scalars(
                select(Place)
                .join(District)
                .where(
                    Place.is_active.is_(True),
                    District.is_active.is_(True),
                    or_(Place.name.ilike(term), Place.slug.ilike(term)),
                    or_(
                        Place.destination_id.is_(None),
                        Place.destination.has(Destination.is_active.is_(True)),
                    ),
                )
                .options(
                    selectinload(Place.district),
                    selectinload(Place.destination),
                )
                .order_by(Place.name)
                .limit(remaining)
            )
        )
    return districts, destinations, places
