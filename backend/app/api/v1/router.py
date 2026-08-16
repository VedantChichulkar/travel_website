import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies import get_db
from app.api.v1 import admin, auth, users

logger = logging.getLogger(__name__)
router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])


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
