from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.models.user import User
from app.schemas.review import AdminReview, ReviewModerationRequest
from app.services import review_service


router = APIRouter()


@router.get("/reviews/moderation", response_model=list[AdminReview])
def moderation_queue(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return review_service.list_admin_queue(db)


@router.post("/reviews/{review_id}/moderate", response_model=AdminReview)
def moderate_review(review_id: int, data: ReviewModerationRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return review_service.moderate(db, admin, review_id, data.action, data.note)
