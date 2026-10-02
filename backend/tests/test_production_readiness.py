import logging
import unittest

from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging_config import SensitiveDataFilter


class ProductionReadinessTests(unittest.TestCase):
    def _production_settings(self, **overrides):
        values = {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "mysql+pymysql://app:password@db.example.com/travel_platform",
            "SECRET_KEY": "jwt-secret-that-is-longer-than-thirty-two-characters",
            "PAYMENT_WEBHOOK_SECRET": "payment-secret-that-is-longer-than-thirty-two-characters",
            "CORS_ORIGINS": ["https://www.example.com", "https://admin.example.com"],
            "TRUSTED_HOSTS": ["api.example.com"],
            "APP_BASE_URL": "https://www.example.com",
            "EMAIL_VERIFICATION_REQUIRED": True,
            "DATA_ENCRYPTION_KEY": "dedicated-encryption-key-that-is-long-enough",
            "PRIVATE_DOCUMENT_MODE": "s3",
            "PRIVATE_DOCUMENT_S3_BUCKET": "travel-platform-private-documents",
            "PRIVATE_DOCUMENT_S3_REGION": "ap-south-1",
            "MEDIA_BASE_URL": "https://api.example.com",
            "AUTH_COOKIE_SECURE": True,
            "LOG_FORMAT": "json",
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_valid_production_configuration(self) -> None:
        configured = self._production_settings()
        self.assertEqual(configured.ENVIRONMENT, "production")
        self.assertTrue(configured.MEDIA_ROOT.is_absolute())

    def test_production_configuration_rejects_unsafe_values(self) -> None:
        unsafe = (
            {"SECRET_KEY": "short"},
            {"DEBUG": True},
            {"PAYMENT_WEBHOOK_SECRET": "short"},
            {"CORS_ORIGINS": ["*"]},
            {"TRUSTED_HOSTS": ["*"]},
            {"MEDIA_BASE_URL": "http://api.example.com"},
            {"DATABASE_URL": "sqlite:///production.db"},
            {"PRIVATE_DOCUMENT_MODE": "local"},
            {"PRIVATE_DOCUMENT_S3_BUCKET": ""},
            {"PRIVATE_DOCUMENT_S3_ENDPOINT_URL": "http://storage.example.com"},
            {"PRIVATE_DOCUMENT_S3_ENCRYPTION": "aws:kms", "PRIVATE_DOCUMENT_S3_KMS_KEY_ID": ""},
            {"AUTH_COOKIE_SECURE": False},
            {"LOG_FORMAT": "text"},
        )
        for override in unsafe:
            with self.subTest(override=override), self.assertRaises(ValidationError):
                self._production_settings(**override)

    def test_razorpay_live_configuration_is_explicit_and_complete(self) -> None:
        configured = self._production_settings(
            PAYMENT_PROVIDER="RAZORPAY", PAYMENT_MODE="live",
            RAZORPAY_KEY_ID="rzp_live_examplekey", RAZORPAY_KEY_SECRET="server-secret",
            RAZORPAY_WEBHOOK_SECRET="webhook-secret-that-is-longer-than-thirty-two-characters",
            FINANCIAL_COMPLETION_ENABLED=True,
        )
        self.assertEqual(configured.PAYMENT_MODE, "live")
        for override in (
            {"RAZORPAY_KEY_ID": "rzp_test_wrongmode"},
            {"RAZORPAY_KEY_SECRET": ""},
            {"RAZORPAY_WEBHOOK_SECRET": ""},
            {"FINANCIAL_COMPLETION_ENABLED": False},
        ):
            with self.subTest(override=override), self.assertRaises(ValidationError):
                values = {"PAYMENT_PROVIDER": "RAZORPAY", "PAYMENT_MODE": "live", "RAZORPAY_KEY_ID": "rzp_live_examplekey", "RAZORPAY_KEY_SECRET": "server-secret", "RAZORPAY_WEBHOOK_SECRET": "webhook-secret-that-is-longer-than-thirty-two-characters", "FINANCIAL_COMPLETION_ENABLED": True}
                values.update(override)
                self._production_settings(**values)

    def test_razorpay_test_keys_cannot_enable_live_mode(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, ENVIRONMENT="development", DATABASE_URL="sqlite:///test.db", SECRET_KEY="x" * 32,
                     PAYMENT_PROVIDER="RAZORPAY", PAYMENT_MODE="live", RAZORPAY_KEY_ID="rzp_live_example",
                     RAZORPAY_KEY_SECRET="secret", RAZORPAY_WEBHOOK_SECRET="webhook")

    def test_razorpayx_live_configuration_is_explicit_and_isolated(self) -> None:
        configured = self._production_settings(
            PAYOUT_PROVIDER="RAZORPAYX", PAYOUT_MODE="live", PAYOUT_EXECUTION_ENABLED=True,
            RAZORPAYX_KEY_ID="rzp_live_payoutkey", RAZORPAYX_KEY_SECRET="payout-server-secret",
            RAZORPAYX_WEBHOOK_SECRET="payout-webhook-secret-longer-than-thirty-two-characters",
            RAZORPAYX_ACCOUNT_NUMBER="production-debit-identifier",
        )
        self.assertEqual(configured.PAYOUT_MODE, "live")
        for override in (
            {"PAYOUT_EXECUTION_ENABLED": False},
            {"RAZORPAYX_KEY_ID": "rzp_test_wrongmode"},
            {"RAZORPAYX_KEY_SECRET": ""},
            {"RAZORPAYX_WEBHOOK_SECRET": "short"},
            {"RAZORPAYX_ACCOUNT_NUMBER": ""},
            {"RAZORPAYX_API_BASE_URL": "http://api.razorpay.com/v1"},
        ):
            values = {
                "PAYOUT_PROVIDER": "RAZORPAYX", "PAYOUT_MODE": "live", "PAYOUT_EXECUTION_ENABLED": True,
                "RAZORPAYX_KEY_ID": "rzp_live_payoutkey", "RAZORPAYX_KEY_SECRET": "payout-server-secret",
                "RAZORPAYX_WEBHOOK_SECRET": "payout-webhook-secret-longer-than-thirty-two-characters",
                "RAZORPAYX_ACCOUNT_NUMBER": "production-debit-identifier",
            }
            values.update(override)
            with self.subTest(override=override), self.assertRaises(ValidationError):
                self._production_settings(**values)

    def test_sensitive_log_filter_redacts_credentials(self) -> None:
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "Bearer abc.def token=visible mysql+pymysql://app:password@db/travel_platform", (), None)
        SensitiveDataFilter().filter(record)
        message = record.getMessage()
        self.assertNotIn("abc.def", message)
        self.assertNotIn("visible", message)
        self.assertNotIn(":password@", message)


if __name__ == "__main__":
    unittest.main()
