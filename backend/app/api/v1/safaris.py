from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permission import require_admin, require_customer
from app.dependencies import get_db
from app.models.safari import SafariDocumentKind, SafariRequestStatus
from app.models.user import User
from app.schemas.booking import PaymentOrderResponse
from app.schemas.safari import AlternativeSelection, AvailabilityDecision, AvailabilityRequestCreate, BookingFailureInput, ConfirmationInput, PricingInput, SafariConfigurationUpdate, SafariDocumentResponse, SafariOperationalNoticeCreate, SafariOperationalNoticeResponse, SafariOperationalNoticeUpdate, SafariPublic, SafariRequestResponse, TravellerSubmission
from app.services import private_document_storage, safari_service

public_router = APIRouter()
customer_router = APIRouter(dependencies=[Depends(require_customer)])
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@public_router.get("/safaris", response_model=list[SafariPublic])
def list_safaris(db: Session = Depends(get_db)): return safari_service.list_public(db)


@public_router.get("/safaris/{slug}", response_model=SafariPublic)
def get_safari(slug: str, db: Session = Depends(get_db)): return safari_service.get_public(db, slug)


@customer_router.post("/safaris/{slug}/requests", response_model=SafariRequestResponse, status_code=status.HTTP_201_CREATED)
def request_availability(slug: str, data: AvailabilityRequestCreate, db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.create_request(db, user, slug, data)


@customer_router.get("/account/safaris", response_model=list[SafariRequestResponse])
def my_safaris(db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.list_customer(db, user)


@customer_router.get("/account/safaris/{request_id}", response_model=SafariRequestResponse)
def my_safari(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.get_customer(db, user, request_id)


@customer_router.post("/account/safaris/{request_id}/alternative", response_model=SafariRequestResponse)
def select_alternative(request_id: int, data: AlternativeSelection, db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.select_alternative(db, user, request_id, data.alternative_id)


@customer_router.put("/account/safaris/{request_id}/travellers", response_model=SafariRequestResponse)
def save_travellers(request_id: int, data: TravellerSubmission, db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.save_travellers(db, user, request_id, data)


@customer_router.post("/account/safaris/{request_id}/travellers/submit", response_model=SafariRequestResponse)
def submit_travellers(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.submit_travellers(db, user, request_id)


@customer_router.post("/account/safaris/{request_id}/travellers/{traveller_id}/documents", response_model=SafariDocumentResponse, status_code=status.HTTP_201_CREATED)
async def traveller_document(request_id: int, traveller_id: int, file: UploadFile = File(...), document_type: str = Form(..., min_length=1, max_length=100), db: Session = Depends(get_db), user: User = Depends(require_customer)):
    return await safari_service.upload_document(db, user, request_id, traveller_id, document_type, SafariDocumentKind.TRAVELLER, file)


@customer_router.post("/account/safaris/{request_id}/payment-order", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
def payment_order(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_customer)): return safari_service.create_payment_order(db, user, request_id)


@customer_router.get("/account/safaris/{request_id}/documents/{document_id}", response_class=StreamingResponse)
def customer_document(request_id: int, document_id: int, db: Session = Depends(get_db), user: User = Depends(require_customer)):
    document = safari_service.document_path(db, user, request_id, document_id)
    return private_document_storage.download_response(document.storage_key, filename=document.original_name, content_type=document.content_type)


@admin_router.get("/safari-operations", response_model=list[SafariRequestResponse])
def safari_queue(status_filter: SafariRequestStatus | None = Query(default=None, alias="status"), overdue: bool = False, db: Session = Depends(get_db)): return safari_service.list_admin(db, status_filter, overdue)


@admin_router.patch("/safaris/{safari_id}/configuration", response_model=SafariPublic)
def safari_configuration(safari_id: int, data: SafariConfigurationUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.update_configuration(db, admin, safari_id, data)


@admin_router.get("/safari-notices", response_model=list[SafariOperationalNoticeResponse])
def safari_notices(db: Session = Depends(get_db)): return safari_service.list_notices(db)


@admin_router.post("/safari-notices", response_model=SafariOperationalNoticeResponse, status_code=status.HTTP_201_CREATED)
def create_safari_notice(data: SafariOperationalNoticeCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.create_notice(db, admin, data)


@admin_router.patch("/safari-notices/{notice_id}", response_model=SafariOperationalNoticeResponse)
def update_safari_notice(notice_id: int, data: SafariOperationalNoticeUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.update_notice(db, admin, notice_id, data)


@admin_router.post("/safari-operations/{request_id}/availability", response_model=SafariRequestResponse)
def availability(request_id: int, data: AvailabilityDecision, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.availability_decision(db, admin, request_id, data)


@admin_router.post("/safari-operations/{request_id}/pricing", response_model=SafariRequestResponse)
def pricing(request_id: int, data: PricingInput, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.set_pricing(db, admin, request_id, data)


@admin_router.post("/safari-operations/{request_id}/confirmation-documents", response_model=SafariDocumentResponse, status_code=status.HTTP_201_CREATED)
async def confirmation_document(request_id: int, file: UploadFile = File(...), document_type: str = Form(default="permit", max_length=100), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return await safari_service.upload_document(db, admin, request_id, None, document_type, SafariDocumentKind.CONFIRMATION, file, admin=True)


@admin_router.post("/safari-operations/{request_id}/confirm", response_model=SafariRequestResponse)
def confirm(request_id: int, data: ConfirmationInput, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.confirm(db, admin, request_id, data)


@admin_router.post("/safari-operations/{request_id}/fail", response_model=SafariRequestResponse)
def fail(request_id: int, data: BookingFailureInput, db: Session = Depends(get_db), admin: User = Depends(require_admin)): return safari_service.fail_booking(db, admin, request_id, data.reason)


@admin_router.get("/safari-operations/{request_id}/documents/{document_id}", response_class=StreamingResponse)
def admin_document(request_id: int, document_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    document = safari_service.document_path(db, admin, request_id, document_id, admin=True)
    return private_document_storage.download_response(document.storage_key, filename=document.original_name, content_type=document.content_type)
