import hashlib
import hmac
import json
import unittest
from decimal import Decimal
from unittest.mock import patch

from app.core.config import settings
from app.services.payment_provider import ProviderOutcomeUnknown, RazorpayProvider


class _Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return json.dumps(self.payload).encode()


class RazorpayProviderTests(unittest.TestCase):
    def setUp(self):
        self.values = {name: getattr(settings, name) for name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET")}
        settings.RAZORPAY_KEY_ID = "rzp_test_public"
        settings.RAZORPAY_KEY_SECRET = "server-secret"
        settings.RAZORPAY_WEBHOOK_SECRET = "webhook-secret"
        self.provider = RazorpayProvider()

    def tearDown(self):
        for name, value in self.values.items(): setattr(settings, name, value)

    @patch("app.services.payment_provider.urlopen")
    def test_order_creation_uses_subunits_and_authoritative_financials(self, mocked):
        mocked.return_value = _Response({"id": "order_123", "status": "created", "amount": 125050, "currency": "INR"})
        result = self.provider.create_order(amount=Decimal("1250.50"), currency="INR", booking_reference="VYO-123")
        self.assertEqual(result.provider_order_id, "order_123")
        sent = json.loads(mocked.call_args.args[0].data)
        self.assertEqual(sent["amount"], 125050)
        self.assertRegex(sent["receipt"], r"^VYO-123-[0-9a-f]{12}$")
        self.assertEqual(sent["notes"]["vayora_reference"], "VYO-123")

    def test_checkout_and_webhook_signatures_use_constant_time_hmac_contract(self):
        checkout = hmac.new(b"server-secret", b"order_1|pay_1", hashlib.sha256).hexdigest()
        self.assertTrue(self.provider.verify_checkout_signature(provider_order_id="order_1", provider_payment_id="pay_1", signature=checkout))
        self.assertFalse(self.provider.verify_checkout_signature(provider_order_id="order_1", provider_payment_id="pay_forged", signature=checkout))
        body = b'{"event":"payment.captured"}'
        webhook = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(self.provider.verify_callback(body, webhook))
        self.assertFalse(self.provider.verify_callback(body + b" ", webhook))

    @patch("app.services.payment_provider.urlopen")
    def test_payment_lookup_preserves_order_amount_currency_and_capture(self, mocked):
        mocked.return_value = _Response({"id": "pay_1", "order_id": "order_1", "status": "captured", "amount": 9900, "currency": "INR"})
        result = self.provider.fetch_payment("pay_1")
        self.assertEqual((result.provider_order_id, result.status, result.amount), ("order_1", "captured", Decimal("99.00")))

    @patch("app.services.payment_provider.urlopen")
    def test_refund_submission_has_stable_receipt_and_is_not_marked_complete_early(self, mocked):
        mocked.return_value = _Response({"id": "rfnd_1", "status": "pending", "amount": 2500, "currency": "INR"})
        result = self.provider.create_refund(provider_payment_id="pay_1", amount=Decimal("25.00"), currency="INR", idempotency_key="refund-42")
        self.assertEqual(result.status, "pending")
        sent = json.loads(mocked.call_args.args[0].data)
        self.assertEqual(sent["receipt"], "refund-42")
        self.assertEqual(sent["amount"], 2500)

    @patch("app.services.payment_provider.urlopen", side_effect=TimeoutError())
    def test_mutating_timeout_is_uncertain_not_safe_success(self, _):
        with self.assertRaises(ProviderOutcomeUnknown):
            self.provider.create_refund(provider_payment_id="pay_1", amount=Decimal("25.00"), currency="INR", idempotency_key="refund-42")


if __name__ == "__main__": unittest.main()
