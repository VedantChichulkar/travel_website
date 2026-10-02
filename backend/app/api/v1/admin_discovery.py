from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.models.user import User
from app.schemas.admin_discovery import (
    AdminDestinationList,
    AdminDestinationRead,
    AdminPlaceList,
    AdminPlaceRead,
    DestinationCreate,
    DestinationUpdate,
    DiscoveryReferenceData,
    LifecycleAction,
    MediaUpdate,
    PlaceCreate,
    PlaceUpdate,
    PublicMediaRead,
    PublicationImpact,
)
from app.services import admin_discovery_service


router = APIRouter(prefix="/discovery", dependencies=[Depends(require_admin)])


@router.get("/reference", response_model=DiscoveryReferenceData)
def reference(db: Session = Depends(get_db)):
    return admin_discovery_service.reference_data(db)


@router.get("/destinations", response_model=AdminDestinationList)
def destinations(
    query: str | None = Query(None, max_length=160),
    lifecycle: Literal["DRAFT", "PUBLISHED", "UNPUBLISHED"] | None = None,
    district_id: int | None = None,
    limit: int = Query(100, ge=1, le=250),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return admin_discovery_service.list_destinations(db, query=query, lifecycle=lifecycle, district_id=district_id, limit=limit, offset=offset)


@router.post("/destinations", response_model=AdminDestinationRead, status_code=status.HTTP_201_CREATED)
def create_destination(data: DestinationCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.create_destination(db, admin, data)


@router.get("/destinations/{destination_id}", response_model=AdminDestinationRead)
def destination(destination_id: int, db: Session = Depends(get_db)):
    return admin_discovery_service._destination_read(admin_discovery_service.get_destination(db, destination_id))


@router.patch("/destinations/{destination_id}", response_model=AdminDestinationRead)
def update_destination(destination_id: int, data: DestinationUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.update_destination(db, admin, destination_id, data)


@router.post("/destinations/{destination_id}/publish", response_model=PublicationImpact)
def publish_destination(destination_id: int, data: LifecycleAction, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.publish(db, admin, "DESTINATION", destination_id, data)


@router.post("/destinations/{destination_id}/unpublish", response_model=PublicationImpact)
def unpublish_destination(destination_id: int, data: LifecycleAction, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.unpublish(db, admin, "DESTINATION", destination_id, data)


@router.get("/places", response_model=AdminPlaceList)
def places(
    query: str | None = Query(None, max_length=160),
    lifecycle: Literal["DRAFT", "PUBLISHED", "UNPUBLISHED"] | None = None,
    district_id: int | None = None,
    destination_id: int | None = None,
    interest_id: int | None = None,
    limit: int = Query(100, ge=1, le=250),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return admin_discovery_service.list_places(db, query=query, lifecycle=lifecycle, district_id=district_id, destination_id=destination_id, interest_id=interest_id, limit=limit, offset=offset)


@router.post("/places", response_model=AdminPlaceRead, status_code=status.HTTP_201_CREATED)
def create_place(data: PlaceCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.create_place(db, admin, data)


@router.get("/places/{place_id}", response_model=AdminPlaceRead)
def place(place_id: int, db: Session = Depends(get_db)):
    return admin_discovery_service._place_read(admin_discovery_service.get_place(db, place_id))


@router.patch("/places/{place_id}", response_model=AdminPlaceRead)
def update_place(place_id: int, data: PlaceUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.update_place(db, admin, place_id, data)


@router.post("/places/{place_id}/publish", response_model=PublicationImpact)
def publish_place(place_id: int, data: LifecycleAction, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.publish(db, admin, "PLACE", place_id, data)


@router.post("/places/{place_id}/unpublish", response_model=PublicationImpact)
def unpublish_place(place_id: int, data: LifecycleAction, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_discovery_service.unpublish(db, admin, "PLACE", place_id, data)


@router.get("/media", response_model=list[PublicMediaRead])
def media(status_value: Literal["ACTIVE", "RETIRED"] | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return admin_discovery_service.list_media(db, status_value=status_value, limit=limit)


@router.post("/media/{entity_type}/{entity_id}", response_model=PublicMediaRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    entity_type: Literal["DESTINATION", "PLACE"],
    entity_id: int,
    file: UploadFile = File(...),
    alt_text: str = Form(..., min_length=5, max_length=300),
    specificity: Literal["SPECIFIC", "EDITORIAL", "FALLBACK"] = Form(...),
    creator_owner: str = Form(..., min_length=2, max_length=200),
    source_name: str = Form(..., min_length=2, max_length=200),
    source_url: str | None = Form(None, max_length=2048),
    usage_basis: str = Form(..., min_length=3, max_length=200),
    attribution_text: str | None = Form(None, max_length=500),
    rights_verified_at: date = Form(...),
    subject_match_confirmed: bool = Form(False),
    role: Literal["HERO", "GALLERY"] = Form("HERO"),
    display_order: int = Form(0, ge=0, le=100_000),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return await admin_discovery_service.upload_media(
        db,
        admin,
        entity_type=entity_type,
        entity_id=entity_id,
        file=file,
        alt_text=alt_text,
        specificity=specificity,
        creator_owner=creator_owner,
        source_name=source_name,
        source_url=source_url,
        usage_basis=usage_basis,
        attribution_text=attribution_text,
        rights_verified_at=rights_verified_at,
        subject_match_confirmed=subject_match_confirmed,
        role=role,
        display_order=display_order,
    )


@router.patch("/media/{entity_type}/{entity_id}/{relation_id}", response_model=AdminDestinationRead | AdminPlaceRead)
def update_media(
    entity_type: Literal["DESTINATION", "PLACE"], entity_id: int, relation_id: int, data: MediaUpdate,
    db: Session = Depends(get_db), admin: User = Depends(require_admin),
):
    return admin_discovery_service.update_entity_media(db, admin, entity_type=entity_type, entity_id=entity_id, relation_id=relation_id, data=data)


@router.delete("/media/{entity_type}/{entity_id}/{relation_id}", response_model=AdminDestinationRead | AdminPlaceRead)
def retire_media(
    entity_type: Literal["DESTINATION", "PLACE"], entity_id: int, relation_id: int,
    expected_version: int = Query(ge=1), db: Session = Depends(get_db), admin: User = Depends(require_admin),
):
    return admin_discovery_service.retire_entity_media(db, admin, entity_type=entity_type, entity_id=entity_id, relation_id=relation_id, expected_version=expected_version)
