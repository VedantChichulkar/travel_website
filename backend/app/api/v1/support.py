from datetime import timedelta

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permission import require_admin
from app.dependencies import get_db, get_optional_user
from app.models.user import User
from app.schemas.support import AdminSupportEnquiry, AdminSupportEnquiryList, PublicContactConfig, SupportEnquiryCreate, SupportEnquiryReceipt
from app.services import auth_security_service, support_service


public_router = APIRouter()
admin_router = APIRouter()


@public_router.get("/support/config", response_model=PublicContactConfig)
def get_contact_config():
    return support_service.contact_config()


@public_router.post("/support/enquiries", response_model=SupportEnquiryReceipt, status_code=status.HTTP_201_CREATED)
def create_enquiry(
    data: SupportEnquiryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    existing = support_service.find_by_idempotency(db, data.idempotency_key)
    if existing:
        return support_service.receipt(existing)
    client = request.client.host if request.client else "unknown"
    auth_security_service.check_rate_limit(
        db, scope="support-enquiry", identifier=f"{client}:{str(data.email).lower()}",
        maximum=settings.SUPPORT_ENQUIRY_RATE_LIMIT, window=timedelta(hours=1),
    )
    return support_service.receipt(support_service.create_enquiry(db, data, current_user))


@admin_router.get("/support/enquiries", response_model=AdminSupportEnquiryList)
def list_enquiries(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    items = support_service.admin_list(db)
    return AdminSupportEnquiryList(items=[support_service.admin_view(item) for item in items], total=len(items))


@admin_router.get("/support/enquiries/{reference}", response_model=AdminSupportEnquiry)
def get_enquiry(reference: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return support_service.admin_view(support_service.admin_get(db, reference))
