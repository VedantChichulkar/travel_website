from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.slug import unique_slug
from app.models.destination import Destination, District
from app.models.discovery import DiscoveryStory
from app.models.discovery_content import DestinationFAQ, DestinationMedia, PlaceFAQ, PlaceMedia
from app.models.hotel import Hotel
from app.models.place import Interest, Place
from app.models.public_media import PublicMediaAsset
from app.models.user import User
from app.schemas.admin_discovery import (
    AdminDestinationList,
    AdminDestinationRead,
    AdminEntityMediaRead,
    AdminFAQRead,
    AdminInterestRead,
    AdminPlaceList,
    AdminPlaceRead,
    DestinationCreate,
    DestinationUpdate,
    DiscoveryReferenceData,
    DistrictOption,
    InterestOption,
    LifecycleAction,
    MediaUpdate,
    PlaceCreate,
    PlaceUpdate,
    PublicationImpact,
)
from app.services import audit_service, media_storage


def _not_found(label: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{label} not found")


def _lifecycle(item: Destination | Place) -> str:
    if item.is_active:
        return "PUBLISHED"
    return "UNPUBLISHED" if item.published_at else "DRAFT"


def _destination_read(item: Destination) -> AdminDestinationRead:
    return AdminDestinationRead(
        id=item.id,
        district_id=item.district_id,
        district_name=item.district.name,
        district_slug=item.district.slug,
        name=item.name,
        slug=item.slug,
        description=item.description,
        short_summary=item.short_summary,
        image_url=item.image_url,
        image_alt=item.image_alt,
        media_asset_id=item.media_asset_id,
        status=_lifecycle(item),
        content_source=item.content_source,
        admin_overridden=item.admin_overridden,
        version=item.version,
        public_path=f"/destinations/{item.district.slug}/{item.slug}",
        published_at=item.published_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        faqs=[_faq_read(value) for value in item.faqs],
        media=[_media_read(value) for value in item.media_items],
    )


def _place_read(item: Place) -> AdminPlaceRead:
    return AdminPlaceRead(
        id=item.id,
        district_id=item.district_id,
        district_name=item.district.name,
        district_slug=item.district.slug,
        destination_id=item.destination_id,
        destination_name=item.destination.name if item.destination else None,
        name=item.name,
        slug=item.slug,
        short_description=item.short_description,
        description=item.description,
        address=item.address,
        opening_hours=item.opening_hours,
        entry_fee_info=item.entry_fee_info,
        recommended_visit_duration=item.recommended_visit_duration,
        best_time_to_visit=item.best_time_to_visit,
        getting_there=item.getting_there,
        nearest_railway_station=item.nearest_railway_station,
        nearest_airport=item.nearest_airport,
        visitor_info_source=item.visitor_info_source,
        visitor_info_source_url=item.visitor_info_source_url,
        visitor_info_verified_at=item.visitor_info_verified_at,
        image_url=item.image_url,
        image_alt=item.image_alt,
        media_asset_id=item.media_asset_id,
        interests=[AdminInterestRead(id=value.id, name=value.name, slug=value.slug) for value in sorted(item.interests, key=lambda value: (value.display_order, value.name))],
        spiritual_tradition=item.spiritual_tradition,
        is_featured=item.is_featured,
        display_order=item.display_order,
        status=_lifecycle(item),
        content_source=item.content_source,
        admin_overridden=item.admin_overridden,
        version=item.version,
        public_path=f"/places/{item.district.slug}/{item.slug}",
        published_at=item.published_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        faqs=[_faq_read(value) for value in item.faqs],
        media=[_media_read(value) for value in item.media_items],
    )


def _faq_read(item: DestinationFAQ | PlaceFAQ) -> AdminFAQRead:
    return AdminFAQRead(id=item.id, question=item.question, answer=item.answer, display_order=item.display_order, is_active=item.is_active)


def _media_read(item: DestinationMedia | PlaceMedia) -> AdminEntityMediaRead:
    asset = item.asset
    return AdminEntityMediaRead(
        id=item.id, media_asset_id=asset.id, role=item.role, display_order=item.display_order,
        public_url=asset.public_url, alt_text=asset.alt_text, specificity=asset.specificity,
        status=asset.status, creator_owner=asset.creator_owner, source_name=asset.source_name,
        source_url=asset.source_url, usage_basis=asset.usage_basis,
        attribution_text=asset.attribution_text, rights_verified_at=asset.rights_verified_at,
    )


def _destination_query():
    return select(Destination).options(
        selectinload(Destination.district), selectinload(Destination.faqs),
        selectinload(Destination.media_items).selectinload(DestinationMedia.asset),
    )


def _place_query():
    return select(Place).options(
        selectinload(Place.district), selectinload(Place.destination), selectinload(Place.interests),
        selectinload(Place.faqs), selectinload(Place.media_items).selectinload(PlaceMedia.asset),
    )


def _replace_faqs(item: Destination | Place, values) -> None:
    faq_type = DestinationFAQ if isinstance(item, Destination) else PlaceFAQ
    item.faqs = [
        faq_type(question=value.question, answer=value.answer, display_order=value.display_order, is_active=value.is_active)
        for value in values
    ]


def reference_data(db: Session) -> DiscoveryReferenceData:
    districts = list(db.scalars(select(District).where(District.is_active.is_(True)).order_by(District.name)))
    interests = list(db.scalars(select(Interest).where(Interest.is_active.is_(True)).order_by(Interest.display_order, Interest.name)))
    from app.models.place import SpiritualTradition
    return DiscoveryReferenceData(
        districts=[DistrictOption(id=value.id, name=value.name, slug=value.slug, division=value.division) for value in districts],
        interests=[InterestOption(id=value.id, name=value.name, slug=value.slug, display_order=value.display_order) for value in interests],
        spiritual_traditions=list(SpiritualTradition),
    )


def _apply_filters(statement, model, *, query: str | None, lifecycle: str | None):
    if query:
        term = f"%{query.strip()}%"
        statement = statement.where(or_(model.name.ilike(term), model.slug.ilike(term)))
    if lifecycle == "PUBLISHED":
        statement = statement.where(model.is_active.is_(True))
    elif lifecycle == "DRAFT":
        statement = statement.where(model.is_active.is_(False), model.published_at.is_(None))
    elif lifecycle == "UNPUBLISHED":
        statement = statement.where(model.is_active.is_(False), model.published_at.is_not(None))
    return statement


def list_destinations(db: Session, *, query: str | None, lifecycle: str | None, district_id: int | None, limit: int, offset: int) -> AdminDestinationList:
    statement = _apply_filters(_destination_query(), Destination, query=query, lifecycle=lifecycle)
    if district_id:
        statement = statement.where(Destination.district_id == district_id)
    total = int(db.scalar(select(func.count()).select_from(statement.with_only_columns(Destination.id).order_by(None).subquery())) or 0)
    items = list(db.scalars(statement.order_by(Destination.updated_at.desc(), Destination.id.desc()).offset(offset).limit(limit)))
    return AdminDestinationList(items=[_destination_read(item) for item in items], total=total)


def list_places(db: Session, *, query: str | None, lifecycle: str | None, district_id: int | None, destination_id: int | None, interest_id: int | None, limit: int, offset: int) -> AdminPlaceList:
    statement = _apply_filters(_place_query(), Place, query=query, lifecycle=lifecycle)
    if district_id:
        statement = statement.where(Place.district_id == district_id)
    if destination_id:
        statement = statement.where(Place.destination_id == destination_id)
    if interest_id:
        statement = statement.join(Place.interests).where(Interest.id == interest_id)
    statement = statement.distinct()
    total = int(db.scalar(select(func.count()).select_from(statement.with_only_columns(Place.id).order_by(None).subquery())) or 0)
    items = list(db.scalars(statement.order_by(Place.updated_at.desc(), Place.id.desc()).offset(offset).limit(limit)).unique())
    return AdminPlaceList(items=[_place_read(item) for item in items], total=total)


def get_destination(db: Session, destination_id: int, *, lock: bool = False) -> Destination:
    statement = _destination_query().where(Destination.id == destination_id)
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise _not_found("Destination")
    return item


def get_place(db: Session, place_id: int, *, lock: bool = False) -> Place:
    statement = _place_query().where(Place.id == place_id)
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise _not_found("Place")
    return item


def _district(db: Session, district_id: int) -> District:
    item = db.get(District, district_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=422, detail="Select an active canonical district")
    return item


def _interests(db: Session, ids: list[int]) -> list[Interest]:
    values = list(db.scalars(select(Interest).where(Interest.id.in_(ids), Interest.is_active.is_(True)))) if ids else []
    if len(values) != len(ids):
        raise HTTPException(status_code=422, detail="One or more interests are invalid or inactive")
    return values


def _validate_destination_link(db: Session, district_id: int, destination_id: int | None) -> Destination | None:
    if destination_id is None:
        return None
    value = db.get(Destination, destination_id)
    if value is None or value.district_id != district_id:
        raise HTTPException(status_code=422, detail="Destination must belong to the selected district")
    return value


def _validate_tradition(interests: list[Interest], tradition) -> None:
    if tradition is not None and "sacred-spiritual" not in {value.slug for value in interests}:
        raise HTTPException(status_code=422, detail="Spiritual tradition is only valid for Sacred & Spiritual places")


def _validate_place_enrichment(data: PlaceCreate | PlaceUpdate) -> None:
    if data.visitor_info_verified_at and data.visitor_info_verified_at > date.today():
        raise HTTPException(status_code=422, detail="Visitor information verification date cannot be in the future")
    if data.visitor_info_source_url:
        parsed = urlparse(data.visitor_info_source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=422, detail="Visitor information source URL must be an absolute HTTP(S) URL")


def _check_version(item: Destination | Place, expected: int) -> None:
    if item.version != expected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This record changed after you opened it. Reload before saving.")


def create_destination(db: Session, actor: User, data: DestinationCreate) -> AdminDestinationRead:
    district = _district(db, data.district_id)
    item = Destination(
        district_id=district.id,
        name=data.name,
        slug=unique_slug(db, Destination, data.name, scope=(Destination.district_id == district.id,), max_length=160),
        description=data.description,
        short_summary=data.short_summary,
        is_active=False,
        content_source="ADMIN",
    )
    db.add(item)
    _replace_faqs(item, data.faqs)
    db.flush()
    audit_service.record(db, actor=actor, action="DESTINATION_CREATED", target_type="DESTINATION", target_id=item.id, reason="Created discovery destination draft", new_value={"name": item.name, "slug": item.slug, "district_id": district.id})
    db.commit()
    return _destination_read(get_destination(db, item.id))


def update_destination(db: Session, actor: User, destination_id: int, data: DestinationUpdate) -> AdminDestinationRead:
    item = get_destination(db, destination_id, lock=True)
    _check_version(item, data.expected_version)
    before = _destination_read(item).model_dump(mode="json")
    if "name" in data.model_fields_set:
        item.name = data.name
    for field in ("name", "description", "short_summary"):
        if field in data.model_fields_set:
            setattr(item, field, getattr(data, field))
    if "faqs" in data.model_fields_set:
        _replace_faqs(item, data.faqs or [])
    item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
    item.version += 1
    audit_service.record(db, actor=actor, action="DESTINATION_UPDATED", target_type="DESTINATION", target_id=item.id, reason="Updated discovery destination content", previous_value=before, new_value={"name": item.name, "version": item.version})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A destination with that name already exists in this district") from exc
    return _destination_read(get_destination(db, item.id))


def create_place(db: Session, actor: User, data: PlaceCreate) -> AdminPlaceRead:
    _validate_place_enrichment(data)
    district = _district(db, data.district_id)
    _validate_destination_link(db, district.id, data.destination_id)
    interests = _interests(db, data.interest_ids)
    _validate_tradition(interests, data.spiritual_tradition)
    item = Place(
        district_id=district.id,
        destination_id=data.destination_id,
        name=data.name,
        slug=unique_slug(db, Place, data.name, scope=(Place.district_id == district.id,), max_length=180),
        short_description=data.short_description,
        description=data.description,
        address=data.address,
        opening_hours=data.opening_hours,
        entry_fee_info=data.entry_fee_info,
        recommended_visit_duration=data.recommended_visit_duration,
        best_time_to_visit=data.best_time_to_visit,
        getting_there=data.getting_there,
        nearest_railway_station=data.nearest_railway_station,
        nearest_airport=data.nearest_airport,
        visitor_info_source=data.visitor_info_source,
        visitor_info_source_url=data.visitor_info_source_url,
        visitor_info_verified_at=data.visitor_info_verified_at,
        spiritual_tradition=data.spiritual_tradition,
        is_featured=data.is_featured,
        display_order=data.display_order,
        interests=interests,
        is_active=False,
        content_source="ADMIN",
    )
    db.add(item)
    _replace_faqs(item, data.faqs)
    db.flush()
    audit_service.record(db, actor=actor, action="PLACE_CREATED", target_type="PLACE", target_id=item.id, reason="Created discovery place draft", new_value={"name": item.name, "slug": item.slug, "district_id": district.id})
    db.commit()
    return _place_read(get_place(db, item.id))


def update_place(db: Session, actor: User, place_id: int, data: PlaceUpdate) -> AdminPlaceRead:
    _validate_place_enrichment(data)
    item = get_place(db, place_id, lock=True)
    _check_version(item, data.expected_version)
    before = _place_read(item).model_dump(mode="json")
    district_id = data.district_id if "district_id" in data.model_fields_set else item.district_id
    _district(db, district_id)
    destination_id = data.destination_id if "destination_id" in data.model_fields_set else item.destination_id
    _validate_destination_link(db, district_id, destination_id)
    interests = _interests(db, data.interest_ids) if "interest_ids" in data.model_fields_set else list(item.interests)
    tradition = data.spiritual_tradition if "spiritual_tradition" in data.model_fields_set else item.spiritual_tradition
    _validate_tradition(interests, tradition)
    if district_id != item.district_id:
        collision = db.scalar(select(Place.id).where(Place.district_id == district_id, Place.slug == item.slug, Place.id != item.id))
        if collision:
            raise HTTPException(status_code=409, detail="The stable slug already exists in the selected district")
    for field in (
        "name", "short_description", "description", "spiritual_tradition", "is_featured", "display_order",
        "address", "opening_hours", "entry_fee_info", "recommended_visit_duration", "best_time_to_visit",
        "getting_there", "nearest_railway_station", "nearest_airport", "visitor_info_source",
        "visitor_info_source_url", "visitor_info_verified_at",
    ):
        if field in data.model_fields_set:
            setattr(item, field, getattr(data, field))
    item.district_id = district_id
    item.destination_id = destination_id
    item.interests = interests
    if "faqs" in data.model_fields_set:
        _replace_faqs(item, data.faqs or [])
    item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
    item.version += 1
    audit_service.record(db, actor=actor, action="PLACE_UPDATED", target_type="PLACE", target_id=item.id, reason="Updated discovery place content", previous_value=before, new_value={"name": item.name, "version": item.version})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A place with that name already exists in this district") from exc
    return _place_read(get_place(db, item.id))


def _publication_ready(item: Destination | Place) -> None:
    missing: list[str] = []
    if not item.name.strip():
        missing.append("name")
    if not item.description or not item.description.strip():
        missing.append("description")
    if isinstance(item, Place):
        if not item.short_description or not item.short_description.strip():
            missing.append("short description")
        if not item.interests:
            missing.append("at least one interest")
    if missing:
        raise HTTPException(status_code=422, detail="Cannot publish until these fields are complete: " + ", ".join(missing))


def publish(db: Session, actor: User, entity_type: str, entity_id: int, data: LifecycleAction) -> PublicationImpact:
    item = get_destination(db, entity_id, lock=True) if entity_type == "DESTINATION" else get_place(db, entity_id, lock=True)
    _check_version(item, data.expected_version)
    _publication_ready(item)
    if isinstance(item, Place) and item.destination and not item.destination.is_active:
        raise HTTPException(status_code=422, detail="Publish the linked destination first or remove the link")
    item.is_active = True
    item.published_at = item.published_at or datetime.now(timezone.utc)
    item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
    item.version += 1
    audit_service.record(db, actor=actor, action=f"{entity_type}_PUBLISHED", target_type=entity_type, target_id=item.id, reason=data.reason, new_value={"status": "PUBLISHED", "version": item.version})
    db.commit()
    entity = _destination_read(get_destination(db, item.id)) if entity_type == "DESTINATION" else _place_read(get_place(db, item.id))
    return PublicationImpact(entity=entity)


def unpublish(db: Session, actor: User, entity_type: str, entity_id: int, data: LifecycleAction) -> PublicationImpact:
    item = get_destination(db, entity_id, lock=True) if entity_type == "DESTINATION" else get_place(db, entity_id, lock=True)
    _check_version(item, data.expected_version)
    affected: dict[str, int] = {}
    if isinstance(item, Destination):
        affected = {
            "linked_places": int(db.scalar(select(func.count(Place.id)).where(Place.destination_id == item.id, Place.is_active.is_(True))) or 0),
            "linked_hotels": int(db.scalar(select(func.count(Hotel.id)).where(Hotel.destination_id == item.id)) or 0),
            "linked_stories": len(item.discovery_stories),
        }
    else:
        affected = {"linked_stories": len(item.discovery_stories)}
    item.is_active = False
    item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
    item.version += 1
    audit_service.record(db, actor=actor, action=f"{entity_type}_UNPUBLISHED", target_type=entity_type, target_id=item.id, reason=data.reason, new_value={"status": "UNPUBLISHED", "version": item.version, "affected": affected})
    db.commit()
    entity = _destination_read(get_destination(db, item.id)) if entity_type == "DESTINATION" else _place_read(get_place(db, item.id))
    return PublicationImpact(entity=entity, affected=affected)


async def upload_media(
    db: Session,
    actor: User,
    *,
    entity_type: str,
    entity_id: int,
    file: UploadFile,
    alt_text: str,
    specificity: str,
    creator_owner: str,
    source_name: str,
    source_url: str | None,
    usage_basis: str,
    attribution_text: str | None,
    rights_verified_at: date,
    subject_match_confirmed: bool,
    role: str = "HERO",
    display_order: int = 0,
) -> PublicMediaAsset:
    entity_type = entity_type.upper()
    if entity_type not in {"DESTINATION", "PLACE"}:
        raise HTTPException(status_code=422, detail="Entity type must be DESTINATION or PLACE")
    item = get_destination(db, entity_id, lock=True) if entity_type == "DESTINATION" else get_place(db, entity_id, lock=True)
    for label, value in (("alt text", alt_text), ("creator/owner", creator_owner), ("source name", source_name), ("usage basis", usage_basis)):
        if not value.strip():
            raise HTTPException(status_code=422, detail=f"{label.title()} is required")
    if specificity not in {"SPECIFIC", "EDITORIAL", "FALLBACK"}:
        raise HTTPException(status_code=422, detail="Invalid media specificity")
    if role not in {"HERO", "GALLERY"} or display_order < 0:
        raise HTTPException(status_code=422, detail="Invalid media role or display order")
    if specificity == "SPECIFIC" and not subject_match_confirmed:
        raise HTTPException(status_code=422, detail="Confirm that specific media depicts the selected subject")
    if rights_verified_at > date.today():
        raise HTTPException(status_code=422, detail="Rights verification date cannot be in the future")
    if source_url:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=422, detail="Source URL must be an absolute HTTP(S) URL")
    public_url, storage_key, content_type, size_bytes, width, height = await media_storage.store_discovery_image(entity_type, entity_id, file)
    old_asset_id = item.media_asset_id if role == "HERO" else None
    asset = PublicMediaAsset(
        entity_type=entity_type,
        entity_id=entity_id,
        storage_key=storage_key,
        public_url=public_url,
        content_type=content_type,
        size_bytes=size_bytes,
        width=width,
        height=height,
        alt_text=alt_text.strip(),
        specificity=specificity,
        creator_owner=creator_owner.strip(),
        source_name=source_name.strip(),
        source_url=source_url.strip() if source_url else None,
        usage_basis=usage_basis.strip(),
        attribution_text=attribution_text.strip() if attribution_text else None,
        rights_verified_at=rights_verified_at,
        created_by_user_id=actor.id,
    )
    try:
        db.add(asset)
        db.flush()
        relation_type = DestinationMedia if isinstance(item, Destination) else PlaceMedia
        owner_field = "destination_id" if isinstance(item, Destination) else "place_id"
        relation = relation_type(media_asset_id=asset.id, role=role, display_order=display_order, **{owner_field: item.id})
        db.add(relation)
        if role == "HERO":
            for existing in item.media_items:
                if existing.role == "HERO":
                    db.delete(existing)
            item.media_asset_id = asset.id
            item.image_url = asset.public_url
            item.image_alt = asset.alt_text
        item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
        item.version += 1
        if role == "HERO" and old_asset_id:
            old = db.get(PublicMediaAsset, old_asset_id)
            if old:
                old.status = "RETIRED"
                old.retired_at = datetime.now(timezone.utc)
                old.replaced_by_asset_id = asset.id
                audit_service.record(db, actor=actor, action="MEDIA_RETIRED", target_type="PUBLIC_MEDIA", target_id=old.id, reason="Retired public media after verified replacement", new_value={"replaced_by_asset_id": asset.id})
        audit_service.record(db, actor=actor, action="MEDIA_REPLACED" if old_asset_id else "MEDIA_UPLOADED", target_type=entity_type, target_id=entity_id, reason="Updated public discovery media with verified rights metadata", previous_value={"media_asset_id": old_asset_id}, new_value={"media_asset_id": asset.id, "specificity": specificity, "role": role, "display_order": display_order})
        db.commit()
    except Exception:
        db.rollback()
        media_storage.delete_stored_file(storage_key)
        raise
    db.refresh(asset)
    return asset


def update_entity_media(db: Session, actor: User, *, entity_type: str, entity_id: int, relation_id: int, data: MediaUpdate):
    entity_type = entity_type.upper()
    item = get_destination(db, entity_id, lock=True) if entity_type == "DESTINATION" else get_place(db, entity_id, lock=True)
    _check_version(item, data.expected_version)
    relation_type = DestinationMedia if isinstance(item, Destination) else PlaceMedia
    owner_column = relation_type.destination_id if isinstance(item, Destination) else relation_type.place_id
    relation = db.scalar(select(relation_type).where(relation_type.id == relation_id, owner_column == item.id).options(selectinload(relation_type.asset)))
    if relation is None:
        raise _not_found("Media assignment")
    if relation.asset.entity_type != entity_type or relation.asset.entity_id != entity_id:
        raise HTTPException(status_code=409, detail="Media cannot be assigned across discovery entities")
    if data.role == "HERO":
        for existing in item.media_items:
            if existing.id != relation.id and existing.role == "HERO":
                existing.role = "GALLERY"
        item.media_asset_id = relation.asset.id
        item.image_url = relation.asset.public_url
        item.image_alt = data.alt_text.strip()
    elif item.media_asset_id == relation.asset.id:
        item.media_asset_id = None
        item.image_url = None
        item.image_alt = None
    relation.role = data.role
    relation.display_order = data.display_order
    relation.asset.alt_text = data.alt_text.strip()
    item.version += 1
    item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
    audit_service.record(db, actor=actor, action="MEDIA_ASSIGNMENT_UPDATED", target_type=entity_type, target_id=item.id, reason="Updated discovery media role, order, or alt text", new_value={"relation_id": relation.id, "role": relation.role, "display_order": relation.display_order})
    db.commit()
    return _destination_read(get_destination(db, item.id)) if isinstance(item, Destination) else _place_read(get_place(db, item.id))


def retire_entity_media(db: Session, actor: User, *, entity_type: str, entity_id: int, relation_id: int, expected_version: int):
    entity_type = entity_type.upper()
    item = get_destination(db, entity_id, lock=True) if entity_type == "DESTINATION" else get_place(db, entity_id, lock=True)
    _check_version(item, expected_version)
    relation_type = DestinationMedia if isinstance(item, Destination) else PlaceMedia
    owner_column = relation_type.destination_id if isinstance(item, Destination) else relation_type.place_id
    relation = db.scalar(select(relation_type).where(relation_type.id == relation_id, owner_column == item.id).options(selectinload(relation_type.asset)))
    if relation is None:
        raise _not_found("Media assignment")
    relation.asset.status = "RETIRED"
    relation.asset.retired_at = datetime.now(timezone.utc)
    if item.media_asset_id == relation.asset.id:
        item.media_asset_id = None
        item.image_url = None
        item.image_alt = None
    db.delete(relation)
    item.version += 1
    item.admin_overridden = item.content_source == "CURATED" or item.admin_overridden
    audit_service.record(db, actor=actor, action="MEDIA_RETIRED", target_type=entity_type, target_id=item.id, reason="Retired discovery media from entity", new_value={"media_asset_id": relation.media_asset_id})
    db.commit()
    return _destination_read(get_destination(db, item.id)) if isinstance(item, Destination) else _place_read(get_place(db, item.id))


def list_media(db: Session, *, status_value: str | None, limit: int) -> list[PublicMediaAsset]:
    statement = select(PublicMediaAsset)
    if status_value:
        statement = statement.where(PublicMediaAsset.status == status_value)
    return list(db.scalars(statement.order_by(PublicMediaAsset.created_at.desc(), PublicMediaAsset.id.desc()).limit(limit)))
