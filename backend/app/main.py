from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import router as api_v1_router

# Initialize logging configuration
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Travel Booking API Backend Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 routes under the /api/v1 prefix
app.include_router(api_v1_router, prefix="/api/v1")
