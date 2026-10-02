from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.models.hotel_verification import VerificationStatus
from app.models.user import User
from app.schemas.hotel_verification import (
    AdminVerificationDetailResponse,
    AdminVerificationListItem,
    HotelVerificationResponse,
    ReviewActionType,
    VerificationReviewRequest,
)
from app.services import admin_verification_service, private_document_storage


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/verifications",
    response_model=list[AdminVerificationListItem],
    summary="List hotel verification applications",
)
def list_verifications(
    status: VerificationStatus | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[AdminVerificationListItem]:
    return admin_verification_service.list_verification_requests(
        db,
        status_filter=status,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/verifications/{verification_id}",
    response_model=AdminVerificationDetailResponse,
    summary="Get verification application detail with property and partner records",
)
def get_verification(
    verification_id: int,
    db: Session = Depends(get_db),
) -> AdminVerificationDetailResponse:
    return admin_verification_service.get_verification_detail(db, verification_id)


@router.post(
    "/verifications/{verification_id}/review",
    response_model=HotelVerificationResponse,
    summary="Process an admin decision (Approve, Reject, Request Info) on verification",
)
def review_verification(
    verification_id: int,
    data: VerificationReviewRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> HotelVerificationResponse:
    return admin_verification_service.review_verification(
        db,
        admin_user=current_admin,
        verification_id=verification_id,
        review_data=data,
    )


@router.post(
    "/verifications/{verification_id}/approve",
    response_model=HotelVerificationResponse,
    summary="Approve hotel verification and activate property",
)
def approve_verification(
    verification_id: int,
    notes: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> HotelVerificationResponse:
    review_req = VerificationReviewRequest(
        action=ReviewActionType.APPROVE,
        admin_notes=notes,
    )
    return admin_verification_service.review_verification(
        db,
        admin_user=current_admin,
        verification_id=verification_id,
        review_data=review_req,
    )


@router.post(
    "/verifications/{verification_id}/reject",
    response_model=HotelVerificationResponse,
    summary="Reject hotel verification",
)
def reject_verification(
    verification_id: int,
    reason: str = Query(..., min_length=2),
    notes: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> HotelVerificationResponse:
    review_req = VerificationReviewRequest(
        action=ReviewActionType.REJECT,
        rejection_reason=reason,
        admin_notes=notes,
    )
    return admin_verification_service.review_verification(
        db,
        admin_user=current_admin,
        verification_id=verification_id,
        review_data=review_req,
    )


@router.post(
    "/verifications/{verification_id}/request-info",
    response_model=HotelVerificationResponse,
    summary="Request additional information from partner",
)
def request_additional_info(
    verification_id: int,
    notes: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> HotelVerificationResponse:
    review_req = VerificationReviewRequest(
        action=ReviewActionType.REQUEST_INFO,
        admin_notes=notes,
    )
    return admin_verification_service.review_verification(
        db,
        admin_user=current_admin,
        verification_id=verification_id,
        review_data=review_req,
    )


@router.post(
    "/verifications/{verification_id}/request-changes",
    response_model=HotelVerificationResponse,
    summary="Request verification application changes without invalidating payment",
)
def request_changes(
    verification_id: int,
    reason: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> HotelVerificationResponse:
    return admin_verification_service.review_verification(
        db,
        admin_user=current_admin,
        verification_id=verification_id,
        review_data=VerificationReviewRequest(action=ReviewActionType.REQUEST_CHANGES, admin_notes=reason),
    )


@router.get("/verifications/{verification_id}/document", response_class=StreamingResponse)
def download_verification_document(verification_id: int, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)) -> StreamingResponse:
    verification = admin_verification_service.get_verification_document(db, current_admin, verification_id)
    return private_document_storage.download_response(verification.document_storage_key, filename=verification.document_original_name or "verification-document", content_type=verification.document_content_type or "application/octet-stream")
