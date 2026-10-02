import logging
import logging.config
import json
import re
from datetime import datetime, timezone

from app.core.config import settings


class SensitiveDataFilter(logging.Filter):
    """Best-effort guard against common credentials entering application logs."""

    _patterns = (
        (re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~-]+"), "Bearer [REDACTED]"),
        (re.compile(r"(?i)(password|secret|token)=([^&\s]+)"), r"\1=[REDACTED]"),
        (re.compile(r"(?i)(mysql\+pymysql://[^:\s]+:)[^@\s]+@"), r"\1[REDACTED]@"),
    )

    @classmethod
    def redact(cls, value: str) -> str:
        message = value
        for pattern, replacement in cls._patterns:
            message = pattern.sub(replacement, message)
        return message

    def filter(self, record: logging.LogRecord) -> bool:
        message = self.redact(record.getMessage())
        record.msg = message
        record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    """Emit one machine-readable event without serializing arbitrary record data."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = SensitiveDataFilter.redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=True)

def setup_logging() -> None:
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "text": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "access": {
                "format": "%(asctime)s - %(levelname)s - %(message)s",
            },
            "json": {
                "()": JsonFormatter,
            },
        },
        "handlers": {
            "console": {
                "formatter": settings.LOG_FORMAT,
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["sensitive_data"],
            },
        },
        "filters": {
            "sensitive_data": {
                "()": SensitiveDataFilter,
            },
        },
        "loggers": {
            "root": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
            },
            "uvicorn.error": {
                "level": settings.LOG_LEVEL,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(logging_config)
