import hashlib
import hmac
import json
import unittest
from decimal import Decimal
from unittest.mock import patch

from app.core.config import settings
from app.services.payout_provider import PayoutDestination, ProviderOutcomeUnknown, RazorpayXPayoutProvider


class _Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return json.dumps(self.payload).encode()


class RazorpayXPayoutProviderTests(unittest.TestCase):
    def setUp(self):
        names = (
            "RAZORPAYX_KEY_ID", "RAZORPAYX_KEY_SECRET", "RAZORPAYX_WEBHOOK_SECRET", "RAZORPAYX_ACCOUNT_NUMBER",
            "RAZORPAYX_PAYOUT_MODE", "RAZORPAYX_PAYOUT_PURPOSE", "RAZORPAYX_PAYOUT_NARRATION",
        )
        self.values = {name: getattr(settings, name) for name in names}
        settings.RAZORPAYX_KEY_ID = "rzp_test_payout"
        settings.RAZORPAYX_KEY_SECRET = "payout-secret"
        settings.RAZORPAYX_WEBHOOK_SECRET = "payout-webhook-secret"
        settings.RAZORPAYX_ACCOUNT_NUMBER = "test-account"
        settings.RAZORPAYX_PAYOUT_MODE = "IMPS"
        settings.RAZORPAYX_PAYOUT_PURPOSE = "payout"
        settings.RAZORPAYX_PAYOUT_NARRATION = "Maharashtra Tourist Places"
        self.provider = RazorpayXPayoutProvider()
        self.destination = PayoutDestination("hotel-verification:7", "Test Hotel", "123456789012", "HDFC0001234", "a" * 64)

    def tearDown(self):
        for name, value in self.values.items(): setattr(settings, name, value)

    @patch("app.services.payout_provider.urlopen")
    def test_composite_payout_uses_authoritative_destination_and_idempotency(self, mocked):
        mocked.return_value = _Response({
            "id": "pout_1", "status": "processing", "amount": 108000, "currency": "INR",
            "fund_account_id": "fa_1", "fund_account": {"contact": {"id": "cont_1"}}, "utr": None,
        })
        result = self.provider.create_payout(destination=self.destination, amount=Decimal("1080.00"), currency="INR", idempotency_key="settlement-7-v1")
        request = mocked.call_args.args[0]
        sent = json.loads(request.data)
        self.assertEqual(sent["amount"], 108000)
        self.assertEqual(sent["fund_account"]["bank_account"]["account_number"], "123456789012")
        self.assertEqual(sent["reference_id"], "settlement-7-v1")
        self.assertIn("x-payout-idempotency", {key.lower(): value for key, value in request.header_items()})
        self.assertEqual((result.provider_payout_id, result.provider_fund_account_id, result.provider_contact_id), ("pout_1", "fa_1", "cont_1"))

    @patch("app.services.payout_provider.urlopen")
    def test_stable_reference_lookup_recovers_uncertain_submission(self, mocked):
        mocked.return_value = _Response({"items": [{"id": "pout_1", "reference_id": "settlement-7-v1", "status": "processed", "amount": 108000, "currency": "INR", "utr": "BANK123"}]})
        result = self.provider.find_payout_by_reference("settlement-7-v1")
        self.assertIsNotNone(result)
        self.assertEqual((result.status, result.utr), ("processed", "BANK123"))

    def test_webhook_hmac_and_payload_parsing_use_raw_body(self):
        payload = json.dumps({"event": "payout.reversed", "payload": {"payout": {"entity": {"id": "pout_1", "status": "reversed", "amount": 108000, "currency": "INR", "utr": "BANK123", "failure_reason": "Bank returned funds"}}}}, separators=(",", ":")).encode()
        signature = hmac.new(b"payout-webhook-secret", payload, hashlib.sha256).hexdigest()
        self.assertTrue(self.provider.verify_payout_callback(payload, signature))
        self.assertFalse(self.provider.verify_payout_callback(payload + b" ", signature))
        event = self.provider.parse_payout_callback(payload, "evt_1")
        self.assertEqual((event.event_id, event.status, event.amount), ("evt_1", "reversed", Decimal("1080.00")))

    @patch("app.services.payout_provider.urlopen", side_effect=TimeoutError())
    def test_mutating_timeout_is_uncertain(self, _):
        with self.assertRaises(ProviderOutcomeUnknown):
            self.provider.create_payout(destination=self.destination, amount=Decimal("1080.00"), currency="INR", idempotency_key="settlement-7-v1")

    @patch("app.services.payout_provider.urlopen")
    def test_malformed_success_response_is_uncertain(self, mocked):
        mocked.return_value = _Response({"status": "processing", "amount": 108000, "currency": "INR"})
        with self.assertRaises(ProviderOutcomeUnknown):
            self.provider.create_payout(destination=self.destination, amount=Decimal("1080.00"), currency="INR", idempotency_key="settlement-7-v1")


if __name__ == "__main__": unittest.main()
