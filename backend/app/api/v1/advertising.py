from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.permission import require_admin, require_advertiser_user, require_hotel_partner_only
from app.dependencies import get_db
from app.models.advertising import AdvertiserType, AdvertisingCampaignStatus, AdvertisingEventType, AdvertisingPlacement
from app.models.booking import PaymentStatus
from app.models.user import User
from app.schemas.advertising import AdvertiserProfileResponse, AdvertiserProfileUpsert, AdvertiserSuspendRequest, AdvertisingConfigResponse, AdvertisingEventRequest, AdvertisingEventResponse, CampaignCreate, CampaignResponse, CampaignReviewRequest, ExternalCampaignCreate, ExternalCampaignUpdate, PublicCampaignList
from app.schemas.booking import PaymentOrderResponse
from app.services import advertising_service
from app.core.config import settings


partner_router = APIRouter(dependencies=[Depends(require_hotel_partner_only)])
advertiser_router = APIRouter(dependencies=[Depends(require_advertiser_user)])
admin_router = APIRouter(dependencies=[Depends(require_admin)])
public_router = APIRouter()


@partner_router.get("/advertising/config", response_model=AdvertisingConfigResponse)
def config() -> AdvertisingConfigResponse:
    return AdvertisingConfigResponse(plans=advertising_service.configured_plans(), rotation_seconds=settings.ADVERTISING_ROTATION_SECONDS)


@partner_router.get("/advertising/campaigns", response_model=list[CampaignResponse])
def campaigns(db: Session = Depends(get_db), user: User = Depends(require_hotel_partner_only)):
    return advertising_service.list_partner(db, user)


@partner_router.post("/advertising/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db), user: User = Depends(require_hotel_partner_only)):
    return advertising_service.create(db, user, data)


@partner_router.post("/advertising/campaigns/{campaign_id}/creative", response_model=CampaignResponse)
async def upload_creative(campaign_id: int, file: UploadFile = File(...), alt_text: str | None = Form(default=None, max_length=255), db: Session = Depends(get_db), user: User = Depends(require_hotel_partner_only)):
    return await advertising_service.upload_creative(db, user, campaign_id, file, alt_text)


@partner_router.post("/advertising/campaigns/{campaign_id}/payment-order", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
def payment_order(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_hotel_partner_only)):
    return advertising_service.create_payment_order(db, user, campaign_id)


@partner_router.post("/advertising/campaigns/{campaign_id}/submit", response_model=CampaignResponse)
def submit(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_hotel_partner_only)):
    return advertising_service.submit(db, user, campaign_id)


@partner_router.post("/advertising/campaigns/{campaign_id}/cancel", response_model=CampaignResponse)
def cancel(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_hotel_partner_only)):
    return advertising_service.cancel(db, user, campaign_id)


@advertiser_router.get("/profile", response_model=AdvertiserProfileResponse)
def advertiser_profile(db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service._profile(db, user)


@advertiser_router.put("/profile", response_model=AdvertiserProfileResponse)
def save_advertiser_profile(data: AdvertiserProfileUpsert, db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.upsert_profile(db, user, data)


@advertiser_router.get("/config", response_model=AdvertisingConfigResponse)
def advertiser_config() -> AdvertisingConfigResponse:
    return AdvertisingConfigResponse(plans=advertising_service.configured_plans(), rotation_seconds=settings.ADVERTISING_ROTATION_SECONDS)


@advertiser_router.get("/campaigns", response_model=list[CampaignResponse])
def advertiser_campaigns(db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.list_external(db, user)


@advertiser_router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_external_campaign(data: ExternalCampaignCreate, db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.create_external(db, user, data)


@advertiser_router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
def update_external_campaign(campaign_id: int, data: ExternalCampaignUpdate, db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.update_external(db, user, campaign_id, data)


@advertiser_router.post("/campaigns/{campaign_id}/creative", response_model=CampaignResponse)
async def upload_external_creative(campaign_id: int, file: UploadFile = File(...), alt_text: str | None = Form(default=None, max_length=255), rights_confirmed: bool = Form(...), source: str | None = Form(default=None, max_length=255), db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return await advertising_service.upload_external_creative(db, user, campaign_id, file, alt_text, rights_confirmed, source)


@advertiser_router.post("/campaigns/{campaign_id}/payment-order", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
def external_payment_order(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.create_external_payment_order(db, user, campaign_id)


@advertiser_router.post("/campaigns/{campaign_id}/submit", response_model=CampaignResponse)
def submit_external_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.submit_external(db, user, campaign_id)


@advertiser_router.post("/campaigns/{campaign_id}/cancel", response_model=CampaignResponse)
def cancel_external_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_advertiser_user)):
    return advertising_service.cancel_external(db, user, campaign_id)


@admin_router.get("/advertising/campaigns", response_model=list[CampaignResponse])
def admin_campaigns(status_filter: AdvertisingCampaignStatus | None = Query(default=None, alias="status"), advertiser_type: AdvertiserType | None = None, payment_status: PaymentStatus | None = None, placement: AdvertisingPlacement | None = None, q: str | None = Query(default=None, max_length=160), db: Session = Depends(get_db)):
    return advertising_service.list_admin(db, status_filter, advertiser_type, payment_status, placement, q)


@admin_router.post("/advertising/campaigns/{campaign_id}/review", response_model=CampaignResponse)
def review(campaign_id: int, data: CampaignReviewRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return advertising_service.review(db, admin, campaign_id, data.action, data.reason)


@admin_router.post("/advertising/advertisers/{profile_id}/suspension", response_model=AdvertiserProfileResponse)
def advertiser_suspension(profile_id: int, data: AdvertiserSuspendRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return advertising_service.suspend_advertiser(db, admin, profile_id, data.suspended, data.reason)


@public_router.get("/ads", response_model=PublicCampaignList)
def public_ads(placement: AdvertisingPlacement, district_slug: str | None = None, destination_slug: str | None = None, db: Session = Depends(get_db)):
    return PublicCampaignList(items=advertising_service.public_campaigns(db, placement, district_slug, destination_slug), rotation_seconds=settings.ADVERTISING_ROTATION_SECONDS)


@public_router.post("/ads/{public_id}/impressions", response_model=AdvertisingEventResponse)
def impression(public_id: str, data: AdvertisingEventRequest, request: Request, x_forwarded_for: str | None = Header(default=None), db: Session = Depends(get_db)):
    fingerprint = f"{x_forwarded_for or (request.client.host if request.client else '')}:{request.headers.get('user-agent', '')}"
    return AdvertisingEventResponse(recorded=advertising_service.record_event(db, public_id, AdvertisingEventType.IMPRESSION, data.event_id, fingerprint))


@public_router.post("/ads/{public_id}/clicks", response_model=AdvertisingEventResponse)
def click(public_id: str, data: AdvertisingEventRequest, request: Request, x_forwarded_for: str | None = Header(default=None), db: Session = Depends(get_db)):
    fingerprint = f"{x_forwarded_for or (request.client.host if request.client else '')}:{request.headers.get('user-agent', '')}"
    return AdvertisingEventResponse(recorded=advertising_service.record_event(db, public_id, AdvertisingEventType.CLICK, data.event_id, fingerprint))


@public_router.get("/ads/{public_id}/click", response_class=RedirectResponse)
def click_redirect(public_id: str, request: Request, x_forwarded_for: str | None = Header(default=None), db: Session = Depends(get_db)):
    fingerprint = f"{x_forwarded_for or (request.client.host if request.client else '')}:{request.headers.get('user-agent', '')}"
    return RedirectResponse(advertising_service.click_destination(db, public_id, fingerprint), status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Referrer-Policy": "no-referrer"})
