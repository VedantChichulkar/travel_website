from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.models.settlement import SettlementStatus
from app.models.user import User
from app.schemas.settlement import SettlementAdjustmentRequest, SettlementHoldRequest, SettlementProcessingRequest, SettlementResponse
from app.schemas.admin_control import SettlementReleaseRequest
from app.services import payout_service, settlement_service


router = APIRouter()


@router.get("/settlements", response_model=list[SettlementResponse])
def list_settlements(settlement_status: SettlementStatus | None = None, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return settlement_service.list_admin(db, settlement_status)


@router.get("/settlements/{settlement_id}", response_model=SettlementResponse)
def get_settlement(settlement_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return settlement_service.get_admin(db, settlement_id)


@router.post("/settlements/refresh", response_model=list[SettlementResponse])
def refresh_settlements(data: SettlementProcessingRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return settlement_service.refresh_due_settlements(db, admin=admin, reason=data.reason)


@router.post("/settlements/{settlement_id}/hold", response_model=SettlementResponse)
def hold_settlement(settlement_id: int, data: SettlementHoldRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return settlement_service.hold(db, admin, settlement_id, data.reason)


@router.post("/settlements/{settlement_id}/release", response_model=SettlementResponse)
def release_settlement(settlement_id: int, data: SettlementReleaseRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return settlement_service.release(db, admin, settlement_id, data.reason)


@router.post("/settlements/{settlement_id}/process", response_model=SettlementResponse)
def process_settlement(settlement_id: int, data: SettlementProcessingRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return payout_service.initiate(db, settlement_id, admin=admin, reason=data.reason)


@router.post("/settlements/{settlement_id}/reconcile", response_model=SettlementResponse)
def reconcile_settlement(settlement_id: int, data: SettlementProcessingRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    item = settlement_service.get_admin(db, settlement_id)
    if item.payout is None:
        return payout_service.initiate(db, settlement_id, admin=admin, reason=data.reason)
    payout_service.reconcile(db, item.payout.id, admin=admin, reason=data.reason)
    return settlement_service.get_admin(db, settlement_id)


@router.post("/settlements/{settlement_id}/retry", response_model=SettlementResponse)
def retry_settlement_payout(settlement_id: int, data: SettlementProcessingRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return payout_service.retry_submission(db, settlement_id, admin=admin, reason=data.reason)


@router.post("/settlements/{settlement_id}/adjustments", response_model=SettlementResponse)
def adjust_settlement(settlement_id: int, data: SettlementAdjustmentRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return settlement_service.add_adjustment(db, admin, settlement_id, data.kind, data.amount, data.reason)
