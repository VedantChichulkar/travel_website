from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.settlement import PayoutResponse
from app.services import payout_service


router = APIRouter()


@router.post("/webhook", response_model=PayoutResponse)
async def payout_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_payout_signature: str | None = Header(default=None),
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
):
    return payout_service.handle_callback(db, await request.body(), x_razorpay_signature or x_payout_signature, x_razorpay_event_id)
