from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.models.user import User
from app.schemas.booking import BookingListResponse, BookingResponse, CancellationResponse, HotelCausedCancellationRequest, ManualRefundDecisionRequest
from app.services import booking_service, cancellation_service


router = APIRouter()


@router.get("/bookings", response_model=BookingListResponse)
def list_bookings(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return booking_service.list_all_bookings(db)


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return booking_service.get_booking(db, current_user, booking_id)


@router.post("/bookings/{booking_id}/hotel-caused-cancellation", response_model=CancellationResponse, status_code=201)
def hotel_caused_cancellation(booking_id: int, data: HotelCausedCancellationRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return cancellation_service.create_hotel_caused_cancellation(db, current_user, booking_id, data.reason)


@router.post("/cancellations/{cancellation_id}/manual-refund", response_model=CancellationResponse)
def decide_manual_refund(cancellation_id: int, data: ManualRefundDecisionRequest, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return cancellation_service.approve_manual_refund(db, current_user, cancellation_id, data.approved_amount, data.note)
