from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.models.booking import BookingStatus, CancellationStatus, PaymentReconciliationStatus, PaymentStatus, RefundStatus
from app.models.hotel import HotelStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.admin_control import AdminBookingRead, AdminCancellationRead, AdminDisputeRead, AdminHotelStatusUpdate, AdminIssueRead, AdminNotificationRead, AdminOverview, AdminPaymentRead, AdminRefundRead, AdminUserRead, AdminUserStatusUpdate, AuditLogRead
from app.schemas.hotel import HotelResponse
from app.schemas.booking import AdminPaymentReconciliationDetail, AdminRefundDetail, ReconciliationActionRequest, ReconciliationActionType, RefundActionRequest, RefundActionType
from app.services import admin_control_service, audit_service, cancellation_service, payment_reconciliation_service, payment_service, refund_execution_service


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/control/overview", response_model=AdminOverview)
def overview(db: Session = Depends(get_db)):
    return admin_control_service.overview(db)


@router.get("/control/users", response_model=list[AdminUserRead])
def users(role: UserRole | None = None, user_status: UserStatus | None = None, search: str | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return admin_control_service.users(db, role=role, user_status=user_status, search=search, limit=limit)


@router.patch("/control/users/{user_id}/status", response_model=AdminUserRead)
def update_user_status(user_id: int, data: AdminUserStatusUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_control_service.update_user_status(db, admin, user_id, data.status, data.reason)


@router.patch("/control/hotels/{hotel_id}/status", response_model=HotelResponse)
def update_hotel_status(hotel_id: int, data: AdminHotelStatusUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return admin_control_service.update_hotel_status(db, admin, hotel_id, data.status, data.reason)


@router.get("/control/bookings", response_model=list[AdminBookingRead])
def bookings(booking_status: BookingStatus | None = None, hotel_id: int | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return admin_control_service.bookings(db, booking_status=booking_status, hotel_id=hotel_id, limit=limit)


@router.get("/control/payments", response_model=list[AdminPaymentRead])
def payments(payment_status: PaymentStatus | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return admin_control_service.payments(db, payment_status=payment_status, limit=limit)


@router.get("/control/payments/{payment_id}", response_model=AdminPaymentReconciliationDetail)
def payment_detail(payment_id: int, db: Session = Depends(get_db)):
    return payment_service.admin_detail(db, payment_id)


@router.post("/control/payments/{payment_id}/reconciliation", response_model=AdminPaymentReconciliationDetail)
def reconcile_payment(payment_id: int, data: ReconciliationActionRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if data.action == ReconciliationActionType.RETRY_CONFIRMATION:
        payment_reconciliation_service.attempt_confirmation(db, payment_id, admin=admin, reason=data.reason)
    else:
        outcome = PaymentReconciliationStatus.REFUND_REQUIRED if data.action == ReconciliationActionType.REFUND_REQUIRED else PaymentReconciliationStatus.MANUAL_REVIEW
        payment_reconciliation_service.set_outcome(db, payment_id, admin, outcome, data.reason)
    return payment_service.admin_detail(db, payment_id)


@router.get("/control/cancellations", response_model=list[AdminCancellationRead])
def cancellations(cancellation_status: CancellationStatus | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return admin_control_service.cancellations(db, cancellation_status=cancellation_status, limit=limit)


@router.get("/control/refunds", response_model=list[AdminRefundRead])
def refunds(refund_status: RefundStatus | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return admin_control_service.refunds(db, refund_status=refund_status, limit=limit)


@router.get("/control/refunds/{refund_id}", response_model=AdminRefundDetail)
def refund_detail(refund_id: int, db: Session = Depends(get_db)):
    return refund_execution_service.admin_detail(db, refund_id)


@router.post("/control/refunds/{refund_id}/action", response_model=AdminRefundDetail)
def refund_action(refund_id: int, data: RefundActionRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if data.action == RefundActionType.RETRY:
        refund_execution_service.submit_refund(db, refund_id, admin=admin, reason=data.reason)
    elif data.action == RefundActionType.RECONCILE:
        refund_execution_service.reconcile_refund(db, refund_id, admin=admin, reason=data.reason)
    else:
        refund_execution_service.require_manual_review(db, refund_id, admin=admin, reason=data.reason)
    return refund_execution_service.admin_detail(db, refund_id)


@router.get("/control/no-shows", response_model=list[AdminIssueRead])
def no_shows(db: Session = Depends(get_db)):
    return admin_control_service.no_shows(db)


@router.get("/control/hotel-failures", response_model=list[AdminIssueRead])
def hotel_failures(db: Session = Depends(get_db)):
    return admin_control_service.hotel_failures(db)


@router.get("/control/disputes", response_model=list[AdminDisputeRead])
def disputes(db: Session = Depends(get_db)):
    return admin_control_service.disputes(db)


@router.get("/control/notifications", response_model=list[AdminNotificationRead])
def notifications(db: Session = Depends(get_db)):
    return admin_control_service.notifications(db)


@router.get("/control/audit", response_model=list[AuditLogRead])
def audit(action: str | None = None, target_type: str | None = None, actor_user_id: int | None = None, limit: int = Query(200, ge=1, le=500), db: Session = Depends(get_db)):
    return audit_service.list_logs(db, action=action, target_type=target_type, actor_user_id=actor_user_id, limit=limit)
