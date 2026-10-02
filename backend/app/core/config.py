from pathlib import Path
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "travel-booking-api"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)
    BOOKING_TAX_RATE: Decimal = Decimal("0.12")
    BOOKING_PLATFORM_FEE: Decimal = Decimal("0.00")
    INVENTORY_HOLD_MINUTES: int = 15
    BOOKING_REQUEST_TTL_HOURS: int = Field(default=24, ge=1, le=168)
    INVENTORY_FRESHNESS_HOURS: int = 24
    # Gateway credentials are intentionally server-only.  The current adapter
    # uses a signed provider callback contract and never accepts a browser
    # supplied payment outcome.
    PAYMENT_PROVIDER: str = "VAYORA_GATEWAY"
    PAYMENT_MODE: Literal["disabled", "sandbox", "test", "live"] = "sandbox"
    PAYMENT_WEBHOOK_SECRET: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_API_BASE_URL: str = "https://api.razorpay.com/v1"
    PAYMENT_PROVIDER_TIMEOUT_SECONDS: int = Field(default=10, ge=2, le=30)
    PAYMENT_ORDER_TTL_MINUTES: int = Field(default=15, ge=1, le=60)
    VERIFICATION_FEE_AMOUNT: Decimal = Field(default=Decimal("2500.00"), gt=Decimal("0"))
    VERIFICATION_FEE_CURRENCY: str = Field(default="INR", min_length=3, max_length=3)
    PAYMENT_RECONCILIATION_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    PAYMENT_RECONCILIATION_BACKOFF_MINUTES: int = Field(default=5, ge=1, le=1440)
    REFUND_RECONCILIATION_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    REFUND_RECONCILIATION_BACKOFF_MINUTES: int = Field(default=15, ge=1, le=1440)
    FINANCIAL_COMPLETION_ENABLED: bool = False
    AUTO_CHECKOUT_GRACE_HOURS: int = 4
    NO_SHOW_REMINDER_HOURS: int = 2
    NO_SHOW_FALLBACK_HOURS: int = 6
    NO_SHOW_REMINDER_OPPORTUNITY_MINUTES: int = 60
    OPERATIONS_SCHEDULER_ENABLED: bool = True
    OPERATIONS_SCHEDULER_INTERVAL_SECONDS: int = Field(default=300, ge=30)
    SETTLEMENT_ELIGIBILITY_DAYS: int = 7
    VAYORA_COMMISSION_RATE: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("1"))
    VAYORA_COMMISSION_RULE: str = Field(default="STANDARD_CONFIGURED_RATE", min_length=3, max_length=120)
    PAYOUT_PROVIDER: str = ""
    PAYOUT_MODE: Literal["disabled", "sandbox", "test", "live"] = "disabled"
    PAYOUT_WEBHOOK_SECRET: str = ""
    PAYOUT_EXECUTION_ENABLED: bool = False
    PAYOUT_AUTO_INITIATE: bool = False
    PAYOUT_PROVIDER_TIMEOUT_SECONDS: int = Field(default=10, ge=2, le=30)
    PAYOUT_RECONCILIATION_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    PAYOUT_RECONCILIATION_BACKOFF_MINUTES: int = Field(default=15, ge=1, le=1440)
    RAZORPAYX_KEY_ID: str = ""
    RAZORPAYX_KEY_SECRET: str = ""
    RAZORPAYX_WEBHOOK_SECRET: str = ""
    RAZORPAYX_ACCOUNT_NUMBER: str = ""
    RAZORPAYX_API_BASE_URL: str = "https://api.razorpay.com/v1"
    RAZORPAYX_PAYOUT_MODE: Literal["IMPS", "NEFT", "RTGS"] = "IMPS"
    RAZORPAYX_PAYOUT_PURPOSE: str = Field(default="payout", min_length=2, max_length=30)
    RAZORPAYX_PAYOUT_NARRATION: str = Field(default="Maharashtra Tourist Places", min_length=3, max_length=30, pattern=r"^[A-Za-z0-9 ]+$")
    RAZORPAYX_MIN_PAYOUT_AMOUNT: Decimal = Field(default=Decimal("1.00"), gt=Decimal("0"))
    NOTIFICATION_MODE: Literal["disabled", "sandbox"] = "disabled"
    NOTIFICATION_EMAIL_PROVIDER: str = ""
    NOTIFICATION_SMS_PROVIDER: str = ""
    NOTIFICATION_WHATSAPP_PROVIDER: str = ""
    NOTIFICATION_RETRY_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    NOTIFICATION_RETRY_BACKOFF_MINUTES: int = Field(default=5, ge=1, le=1440)
    APP_BASE_URL: str = "http://localhost:3000"
    EMAIL_VERIFICATION_REQUIRED: bool = False
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = Field(default=24, ge=1, le=168)
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=120)
    AUTH_LOGIN_RATE_LIMIT: int = Field(default=10, ge=1, le=100)
    AUTH_REGISTER_RATE_LIMIT: int = Field(default=10, ge=1, le=100)
    AUTH_RECOVERY_RATE_LIMIT: int = Field(default=5, ge=1, le=50)
    SUPPORT_ENQUIRY_RATE_LIMIT: int = Field(default=10, ge=1, le=100)
    PUBLIC_SUPPORT_EMAIL: str = ""
    PUBLIC_WHATSAPP_NUMBER: str = ""
    DATA_ENCRYPTION_KEY: str = ""
    MEDIA_ROOT: Path = BACKEND_DIR / "uploads"
    MEDIA_URL: str = "/uploads"
    MEDIA_BASE_URL: str = "http://localhost:8000"
    HOTEL_IMAGE_MAX_BYTES: int = 8 * 1024 * 1024
    DISCOVERY_IMAGE_MAX_BYTES: int = 8 * 1024 * 1024
    DISCOVERY_IMAGE_MAX_PIXELS: int = 30_000_000
    ADVERTISING_PLANS_JSON: str = '[{"code":"HOME_7D","name":"Homepage banner - 7 days","placement":"HOMEPAGE_BANNER","amount":"5000.00","currency":"INR","duration_days":7},{"code":"DEST_7D","name":"Destination promotion - 7 days","placement":"DESTINATION_PROMOTION","amount":"3000.00","currency":"INR","duration_days":7}]'
    ADVERTISING_ROTATION_SECONDS: int = Field(default=5, ge=2, le=60)
    ADVERTISING_EVENT_DEDUPE_SECONDS: int = Field(default=60, ge=10, le=3600)
    SAFARI_RESPONSE_TARGET_MINUTES: int = Field(default=60, ge=5, le=1440)
    PRIVATE_DOCUMENT_MODE: Literal["disabled", "local", "s3"] = "local"
    PRIVATE_DOCUMENT_ROOT: Path = BACKEND_DIR / "private_uploads"
    PRIVATE_DOCUMENT_MAX_BYTES: int = Field(default=10 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    PRIVATE_DOCUMENT_S3_BUCKET: str = ""
    PRIVATE_DOCUMENT_S3_REGION: str = ""
    PRIVATE_DOCUMENT_S3_ENDPOINT_URL: str = ""
    PRIVATE_DOCUMENT_S3_ACCESS_KEY_ID: str = ""
    PRIVATE_DOCUMENT_S3_SECRET_ACCESS_KEY: str = ""
    PRIVATE_DOCUMENT_S3_ADDRESSING_STYLE: Literal["auto", "virtual", "path"] = "auto"
    PRIVATE_DOCUMENT_S3_ENCRYPTION: Literal["AES256", "aws:kms"] = "AES256"
    PRIVATE_DOCUMENT_S3_KMS_KEY_ID: str = ""
    PRIVATE_DOCUMENT_CONNECT_TIMEOUT_SECONDS: int = Field(default=3, ge=1, le=15)
    PRIVATE_DOCUMENT_READ_TIMEOUT_SECONDS: int = Field(default=15, ge=2, le=60)
    PRIVATE_DOCUMENT_DELETE_MAX_ATTEMPTS: int = Field(default=8, ge=1, le=30)
    PRIVATE_DOCUMENT_DELETE_BACKOFF_MINUTES: int = Field(default=30, ge=1, le=1440)
    PRIVATE_DOCUMENT_REPLACEMENT_RETENTION_DAYS: int = Field(default=0, ge=0, le=3650)
    AUTH_COOKIE_NAME: str = "vayora_refresh"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict"] = "lax"
    AUTH_COOKIE_DOMAIN: str | None = None
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "text"

    # CORS configuration origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    TRUSTED_HOSTS: list[str] = ["localhost", "127.0.0.1", "testserver"]

    @model_validator(mode="after")
    def validate_deployment(self):
        if not self.MEDIA_ROOT.is_absolute():
            self.MEDIA_ROOT = (BACKEND_DIR / self.MEDIA_ROOT).resolve()
        if not self.PRIVATE_DOCUMENT_ROOT.is_absolute():
            self.PRIVATE_DOCUMENT_ROOT = (BACKEND_DIR / self.PRIVATE_DOCUMENT_ROOT).resolve()
        if self.ENVIRONMENT != "production":
            self._validate_payment_provider()
            self._validate_payout_provider()
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be disabled in production")

        weak_secrets = {
            "your-super-secret-key-change-in-production",
            "replace-with-a-long-gateway-webhook-secret",
        }
        if len(self.SECRET_KEY) < 32 or self.SECRET_KEY in weak_secrets:
            raise ValueError("SECRET_KEY must be a unique production secret of at least 32 characters")
        self._validate_payment_provider()
        webhook_secret = self.RAZORPAY_WEBHOOK_SECRET if self.PAYMENT_PROVIDER == "RAZORPAY" else self.PAYMENT_WEBHOOK_SECRET
        if self.PAYMENT_MODE != "disabled" and (len(webhook_secret) < 32 or webhook_secret in weak_secrets):
            raise ValueError("The configured payment webhook secret must be a dedicated secret of at least 32 characters")
        if webhook_secret == self.SECRET_KEY:
            raise ValueError("The payment webhook secret must differ from SECRET_KEY")
        if not self.DATABASE_URL.startswith("mysql+pymysql://"):
            raise ValueError("Production DATABASE_URL must use the supported MySQL PyMySQL driver")
        if not self.CORS_ORIGINS or any(origin == "*" or not origin.startswith("https://") for origin in self.CORS_ORIGINS):
            raise ValueError("Production CORS_ORIGINS must contain explicit HTTPS origins")
        if not self.TRUSTED_HOSTS or "*" in self.TRUSTED_HOSTS:
            raise ValueError("Production TRUSTED_HOSTS must contain explicit hostnames")
        if not self.MEDIA_BASE_URL.startswith("https://"):
            raise ValueError("Production MEDIA_BASE_URL must use HTTPS")
        if not self.AUTH_COOKIE_SECURE:
            raise ValueError("Production refresh cookies must be Secure")
        if not self.EMAIL_VERIFICATION_REQUIRED:
            raise ValueError("Production must require email verification")
        if not self.APP_BASE_URL.startswith("https://"):
            raise ValueError("Production APP_BASE_URL must use HTTPS")
        if len(self.DATA_ENCRYPTION_KEY) < 32 or self.DATA_ENCRYPTION_KEY == self.SECRET_KEY:
            raise ValueError("DATA_ENCRYPTION_KEY must be a dedicated production secret of at least 32 characters")
        self._validate_private_document_storage()
        if self.LOG_FORMAT != "json":
            raise ValueError("Production logging must use structured JSON")
        self._validate_payout_provider()
        if self.NOTIFICATION_MODE != "disabled":
            raise ValueError("Sandbox notification delivery must remain disabled in production")
        return self

    def _validate_private_document_storage(self) -> None:
        if self.PRIVATE_DOCUMENT_MODE != "s3":
            raise ValueError("Production private documents require PRIVATE_DOCUMENT_MODE=s3")
        if not self.PRIVATE_DOCUMENT_S3_BUCKET.strip() or not self.PRIVATE_DOCUMENT_S3_REGION.strip():
            raise ValueError("S3 private document storage requires a bucket and region")
        if bool(self.PRIVATE_DOCUMENT_S3_ACCESS_KEY_ID) != bool(self.PRIVATE_DOCUMENT_S3_SECRET_ACCESS_KEY):
            raise ValueError("S3 access key id and secret must be configured together")
        if self.PRIVATE_DOCUMENT_S3_ENDPOINT_URL and not self.PRIVATE_DOCUMENT_S3_ENDPOINT_URL.startswith("https://"):
            raise ValueError("S3-compatible private storage endpoints must use HTTPS")
        if self.PRIVATE_DOCUMENT_S3_ENCRYPTION == "aws:kms" and not self.PRIVATE_DOCUMENT_S3_KMS_KEY_ID.strip():
            raise ValueError("SSE-KMS private storage requires PRIVATE_DOCUMENT_S3_KMS_KEY_ID")

    def _validate_payment_provider(self) -> None:
        if self.PAYMENT_PROVIDER == "VAYORA_GATEWAY":
            if self.PAYMENT_MODE not in ("disabled", "sandbox"):
                raise ValueError("VAYORA_GATEWAY is available only in sandbox mode")
            return
        if self.PAYMENT_PROVIDER != "RAZORPAY":
            if self.PAYMENT_MODE != "disabled":
                raise ValueError("Configured payment provider adapter is unavailable")
            return
        if self.PAYMENT_MODE not in ("test", "live"):
            raise ValueError("RAZORPAY requires PAYMENT_MODE=test or PAYMENT_MODE=live")
        required = (self.RAZORPAY_KEY_ID, self.RAZORPAY_KEY_SECRET, self.RAZORPAY_WEBHOOK_SECRET)
        if not all(value.strip() for value in required):
            raise ValueError("Razorpay key id, key secret, and webhook secret are required")
        expected_prefix = "rzp_test_" if self.PAYMENT_MODE == "test" else "rzp_live_"
        if not self.RAZORPAY_KEY_ID.startswith(expected_prefix):
            raise ValueError(f"Razorpay {self.PAYMENT_MODE} mode requires a {expected_prefix} key id")
        if self.PAYMENT_MODE == "live" and self.ENVIRONMENT != "production":
            raise ValueError("Razorpay live mode is allowed only in the production environment")
        if self.PAYMENT_MODE == "live" and not self.FINANCIAL_COMPLETION_ENABLED:
            raise ValueError("Live payment and refund execution requires FINANCIAL_COMPLETION_ENABLED=true")

    def _validate_payout_provider(self) -> None:
        if self.PAYOUT_MODE == "disabled":
            if self.PAYOUT_AUTO_INITIATE:
                raise ValueError("Automatic payouts cannot run while payouts are disabled")
            return
        if self.PAYOUT_MODE == "sandbox":
            if self.PAYOUT_PROVIDER != "VAYORA_PAYOUT_SANDBOX":
                raise ValueError("Sandbox payouts require the VAYORA_PAYOUT_SANDBOX adapter")
            if self.ENVIRONMENT == "production":
                raise ValueError("Sandbox payouts cannot run in production")
            return
        if self.PAYOUT_PROVIDER != "RAZORPAYX":
            raise ValueError("RazorpayX is the only configured real payout provider")
        if not self.PAYOUT_EXECUTION_ENABLED:
            raise ValueError("Real payout mode requires PAYOUT_EXECUTION_ENABLED=true")
        required = (self.RAZORPAYX_KEY_ID, self.RAZORPAYX_KEY_SECRET, self.RAZORPAYX_WEBHOOK_SECRET, self.RAZORPAYX_ACCOUNT_NUMBER)
        if not all(value.strip() for value in required):
            raise ValueError("RazorpayX key id, secret, webhook secret, and debit account identifier are required")
        expected_prefix = "rzp_test_" if self.PAYOUT_MODE == "test" else "rzp_live_"
        if not self.RAZORPAYX_KEY_ID.startswith(expected_prefix):
            raise ValueError(f"RazorpayX {self.PAYOUT_MODE} mode requires a {expected_prefix} key id")
        if not self.RAZORPAYX_API_BASE_URL.startswith("https://"):
            raise ValueError("RazorpayX API base URL must use HTTPS")
        if len(self.RAZORPAYX_WEBHOOK_SECRET) < 32:
            raise ValueError("RazorpayX webhook secret must be at least 32 characters")
        if self.RAZORPAYX_WEBHOOK_SECRET in (self.SECRET_KEY, self.RAZORPAYX_KEY_SECRET, self.RAZORPAY_WEBHOOK_SECRET):
            raise ValueError("RazorpayX webhook secret must be dedicated")
        if self.PAYOUT_MODE == "live" and self.ENVIRONMENT != "production":
            raise ValueError("RazorpayX live payouts are allowed only in production")
        if self.PAYOUT_MODE == "test" and self.ENVIRONMENT == "production":
            raise ValueError("RazorpayX test payouts cannot run in production")

settings = Settings()  # type: ignore[call-arg]
