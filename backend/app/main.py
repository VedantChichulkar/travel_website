import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import router as api_v1_router
from app.services import operations_scheduler

# Initialize logging configuration
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = asyncio.Event()
    task = asyncio.create_task(operations_scheduler.run(stop)) if settings.OPERATIONS_SCHEDULER_ENABLED else None
    logger.info(
        "Maharashtra Tourist Places API starting environment=%s payment_mode=%s scheduler_enabled=%s",
        settings.ENVIRONMENT,
        settings.PAYMENT_MODE,
        settings.OPERATIONS_SCHEDULER_ENABLED,
    )
    try:
        yield
    finally:
        stop.set()
        if task:
            await task
        logger.info("Maharashtra Tourist Places API stopped")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Travel Booking API Backend Service",
    version="1.0.0",
    debug=settings.DEBUG,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    lifespan=lifespan,
)
settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount(settings.MEDIA_URL, StaticFiles(directory=settings.MEDIA_ROOT), name="uploads")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Vayora-Signature"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Include v1 routes under the /api/v1 prefix
app.include_router(api_v1_router, prefix="/api/v1")
