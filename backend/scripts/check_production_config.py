"""Validate production settings without printing secrets or connection URLs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


if settings.ENVIRONMENT != "production":
    raise SystemExit("ENVIRONMENT must be production")

print(
    "Production configuration valid: "
    f"payment_mode={settings.PAYMENT_MODE}, "
    f"financial_completion_enabled={settings.FINANCIAL_COMPLETION_ENABLED}, "
    f"scheduler_enabled={settings.OPERATIONS_SCHEDULER_ENABLED}, "
    f"log_format={settings.LOG_FORMAT}"
)
