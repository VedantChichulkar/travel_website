import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies import get_db
from app.api.v1 import (
    admin_bookings,
    admin_discovery,
    admin_control,
    admin_settlements,
    admin_reviews,
    admin_hotels,
    admin_verifications,
    advertising,
    auth,
    bookings,
    communications,
    destinations,
    discovery_stories,
    partner_hotels,
    places,
    payouts,
    public_hotels,
    users,
    safaris,
    support,
)

logger = logging.getLogger(__name__)
router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(partner_hotels.router, prefix="/partner", tags=["hotel-partner"])
router.include_router(admin_hotels.router, prefix="/admin", tags=["admin-hotel-management"])
router.include_router(admin_discovery.router, prefix="/admin", tags=["admin-discovery-management"])
router.include_router(admin_verifications.router, prefix="/admin", tags=["admin-hotel-verifications"])
router.include_router(public_hotels.router, prefix="/hotels", tags=["public-hotels"])
router.include_router(destinations.router, prefix="/destinations", tags=["public-destinations"])
router.include_router(places.places_router, prefix="/places", tags=["public-places"])
router.include_router(places.interests_router, prefix="/interests", tags=["public-interests"])
router.include_router(discovery_stories.router, prefix="/discovery-stories", tags=["public-discovery"])
router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
router.include_router(communications.router, prefix="/communications", tags=["communications"])
router.include_router(communications.admin_router, prefix="/admin", tags=["admin-communications"])
router.include_router(admin_bookings.router, prefix="/admin", tags=["admin-bookings"])
router.include_router(admin_control.router, prefix="/admin", tags=["admin-control-center"])
router.include_router(admin_settlements.router, prefix="/admin", tags=["admin-settlements"])
router.include_router(admin_reviews.router, prefix="/admin", tags=["admin-reviews"])
router.include_router(payouts.router, prefix="/payouts", tags=["payouts"])
router.include_router(advertising.partner_router, prefix="/partner", tags=["partner-advertising"])
router.include_router(advertising.advertiser_router, prefix="/advertiser", tags=["external-advertising"])
router.include_router(advertising.admin_router, prefix="/admin", tags=["admin-advertising"])
router.include_router(advertising.public_router, tags=["public-advertising"])
router.include_router(safaris.public_router, tags=["public-safaris"])
router.include_router(safaris.customer_router, tags=["customer-safaris"])
router.include_router(safaris.admin_router, prefix="/admin", tags=["admin-safari-operations"])
router.include_router(support.public_router, tags=["public-support"])
router.include_router(support.admin_router, prefix="/admin", tags=["admin-support"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Report API health after a live, lightweight database query."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connectivity check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": settings.PROJECT_NAME,
                "database": "disconnected",
            },
        )

    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "database": "connected",
    }


@router.get("/health/live")
def liveness():
    """Process-only probe for container orchestration."""
    return {"status": "ok", "service": settings.PROJECT_NAME}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe that fails closed when MySQL is unavailable."""
    return health_check(db)
