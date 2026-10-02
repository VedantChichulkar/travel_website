from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.discovery_story import PublicDiscoveryStoryDetail, PublicDiscoveryStoryList
from app.services import discovery_story_service


router = APIRouter()


@router.get("", response_model=PublicDiscoveryStoryList)
def list_discovery_stories(
    interest: str | None = Query(default=None, min_length=2, max_length=160),
    district: str | None = Query(default=None, min_length=2, max_length=140),
    q: str | None = Query(default=None, min_length=2, max_length=100),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return discovery_story_service.list_stories(
        db, interest=interest, district=district, query=q, limit=limit
    )


@router.get("/{story_slug}", response_model=PublicDiscoveryStoryDetail)
def get_discovery_story(story_slug: str, db: Session = Depends(get_db)):
    return discovery_story_service.get_story(db, story_slug)
