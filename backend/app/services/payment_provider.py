"""Provider-neutral payment boundary and concrete gateway adapters."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderOrder:
    provider_order_id: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class ProviderPayment:
    provider_payment_id: str
    provider_order_id: str
    status: str
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class ProviderRefund:
    provider_refund_id: str
    status: str
    amount: Decimal
    currency: str


class ProviderOutcomeUnknown(RuntimeError):
    """A mutating provider request may have succeeded remotely."""


class PaymentProvider(Protocol):
    name: str

    def create_order(self, *, amount: Decimal, currency: str, booking_reference: str) -> ProviderOrder: ...
    def verify_callback(self, payload: bytes, signature: str | None) -> bool: ...
    def verify_checkout_signature(self, *, provider_order_id: str, provider_payment_id: str, signature: str) -> bool: ...
    def fetch_payment(self, provider_payment_id: str) -> ProviderPayment: ...
    def fetch_payment_status(self, provider_payment_id: str) -> str: ...
    def fetch_captured_order_payment(self, provider_order_id: str) -> ProviderPayment | None: ...
    def create_refund(self, *, provider_payment_id: str, amount: Decimal, currency: str, idempotency_key: str) -> ProviderRefund: ...
    def fetch_refund_status(self, provider_refund_id: str) -> str: ...
    def verify_refund_webhook(self, payload: bytes, signature: str | None) -> bool: ...


class SandboxHmacProvider:
    name = "VAYORA_GATEWAY"

    def create_order(self, *, amount: Decimal, currency: str, booking_reference: str) -> ProviderOrder:
        return ProviderOrder(f"vyo_{secrets.token_urlsafe(18)}", amount, currency)

    def verify_callback(self, payload: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        secret = (settings.PAYMENT_WEBHOOK_SECRET or settings.SECRET_KEY).encode()
        return hmac.compare_digest(hmac.new(secret, payload, hashlib.sha256).hexdigest(), signature)

    def verify_checkout_signature(self, *, provider_order_id: str, provider_payment_id: str, signature: str) -> bool:
        return False

    def fetch_payment(self, provider_payment_id: str) -> ProviderPayment:
        raise HTTPException(status_code=501, detail="Sandbox provider does not expose payment lookup")

    def fetch_payment_status(self, provider_payment_id: str) -> str:
        return self.fetch_payment(provider_payment_id).status

    def fetch_captured_order_payment(self, provider_order_id: str) -> ProviderPayment | None:
        return None

    def create_refund(self, *, provider_payment_id: str, amount: Decimal, currency: str, idempotency_key: str) -> ProviderRefund:
        return ProviderRefund(f"vyr_{secrets.token_urlsafe(18)}", "pending", amount, currency)

    def fetch_refund_status(self, provider_refund_id: str) -> str:
        return "pending"

    def verify_refund_webhook(self, payload: bytes, signature: str | None) -> bool:
        return self.verify_callback(payload, signature)


class RazorpayProvider:
    """Razorpay Orders, Payments and Refunds adapter with bounded HTTP calls."""

    name = "RAZORPAY"

    @staticmethod
    def _subunits(amount: Decimal) -> int:
        return int(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)

    @staticmethod
    def _amount(value: object) -> Decimal:
        return (Decimal(str(value)) / 100).quantize(Decimal("0.01"))

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
        credentials = base64.b64encode(f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()).decode()
        request = Request(f"{settings.RAZORPAY_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}", data=body, method=method, headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=settings.PAYMENT_PROVIDER_TIMEOUT_SECONDS) as response:  # noqa: S310 - configured Razorpay HTTPS endpoint
                parsed = json.loads(response.read().decode())
        except HTTPError as exc:
            description = "Provider rejected the request"
            try:
                description = str(json.loads(exc.read().decode()).get("error", {}).get("description") or description)
            except (ValueError, AttributeError, UnicodeDecodeError):
                pass
            logger.warning("Razorpay API request rejected", extra={"provider": self.name, "operation": path.split("?")[0], "http_status": exc.code})
            raise HTTPException(status_code=502, detail=description[:200]) from exc
        except (TimeoutError, URLError, OSError) as exc:
            logger.warning("Razorpay API request outcome unavailable", extra={"provider": self.name, "operation": path.split("?")[0]})
            if method == "POST":
                raise ProviderOutcomeUnknown("Provider request outcome is unknown") from exc
            raise HTTPException(status_code=503, detail="Payment provider is temporarily unavailable") from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=502, detail="Payment provider returned an invalid response") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=502, detail="Payment provider returned an invalid response")
        return parsed

    def create_order(self, *, amount: Decimal, currency: str, booking_reference: str) -> ProviderOrder:
        currency = currency.upper()
        # Razorpay requires a unique receipt. Keep the domain reference in notes and
        # add an attempt suffix so a failed/cancelled checkout can be retried safely.
        receipt = f"{booking_reference[:27]}-{secrets.token_hex(6)}"
        response = self._request("POST", "orders", {"amount": self._subunits(amount), "currency": currency, "receipt": receipt, "notes": {"vayora_reference": booking_reference[:256]}})
        returned_amount, returned_currency = self._amount(response.get("amount", 0)), str(response.get("currency", "")).upper()
        if response.get("status") != "created" or not response.get("id") or returned_amount != amount or returned_currency != currency:
            raise HTTPException(status_code=502, detail="Provider did not create a matching payment order")
        return ProviderOrder(str(response["id"]), returned_amount, returned_currency)

    def verify_callback(self, payload: bytes, signature: str | None) -> bool:
        if not signature or not settings.RAZORPAY_WEBHOOK_SECRET:
            return False
        expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_checkout_signature(self, *, provider_order_id: str, provider_payment_id: str, signature: str) -> bool:
        if not signature:
            return False
        expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{provider_order_id}|{provider_payment_id}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def fetch_payment(self, provider_payment_id: str) -> ProviderPayment:
        response = self._request("GET", f"payments/{quote(provider_payment_id, safe='')}")
        return ProviderPayment(str(response.get("id", "")), str(response.get("order_id", "")), str(response.get("status", "unknown")).lower(), self._amount(response.get("amount", 0)), str(response.get("currency", "")).upper())

    def fetch_payment_status(self, provider_payment_id: str) -> str:
        return self.fetch_payment(provider_payment_id).status

    def fetch_captured_order_payment(self, provider_order_id: str) -> ProviderPayment | None:
        response = self._request("GET", f"orders/{quote(provider_order_id, safe='')}/payments")
        items = response.get("items", [])
        if not isinstance(items, list):
            return None
        for raw in items:
            if isinstance(raw, dict) and raw.get("status") == "captured":
                return ProviderPayment(str(raw.get("id", "")), str(raw.get("order_id", "")), "captured", self._amount(raw.get("amount", 0)), str(raw.get("currency", "")).upper())
        return None

    @staticmethod
    def _refund_state(value: str) -> str:
        return {"processed": "completed", "pending": "pending", "failed": "failed"}.get(value.lower(), "unknown")

    def _find_refund_by_receipt(self, provider_payment_id: str, receipt: str) -> ProviderRefund | None:
        response = self._request("GET", f"payments/{quote(provider_payment_id, safe='')}/refunds")
        items = response.get("items", [])
        if not isinstance(items, list):
            return None
        for raw in items:
            if isinstance(raw, dict) and raw.get("receipt") == receipt:
                return ProviderRefund(str(raw.get("id", "")), self._refund_state(str(raw.get("status", ""))), self._amount(raw.get("amount", 0)), str(raw.get("currency", "")).upper())
        return None

    def create_refund(self, *, provider_payment_id: str, amount: Decimal, currency: str, idempotency_key: str) -> ProviderRefund:
        receipt = idempotency_key[:40]
        try:
            response = self._request("POST", f"payments/{quote(provider_payment_id, safe='')}/refund", {"amount": self._subunits(amount), "speed": "normal", "receipt": receipt, "notes": {"vayora_refund_key": idempotency_key[:256]}})
        except HTTPException:
            existing = self._find_refund_by_receipt(provider_payment_id, receipt)
            if existing:
                return existing
            raise
        result = ProviderRefund(str(response.get("id", "")), self._refund_state(str(response.get("status", ""))), self._amount(response.get("amount", 0)), str(response.get("currency", "")).upper())
        if not result.provider_refund_id:
            raise HTTPException(status_code=502, detail="Provider returned an invalid refund reference")
        return result

    def fetch_refund_status(self, provider_refund_id: str) -> str:
        response = self._request("GET", f"refunds/{quote(provider_refund_id, safe='')}")
        return self._refund_state(str(response.get("status", "")))

    def verify_refund_webhook(self, payload: bytes, signature: str | None) -> bool:
        return self.verify_callback(payload, signature)


def configured_provider() -> PaymentProvider:
    if settings.PAYMENT_MODE == "disabled":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payments are disabled")
    if settings.PAYMENT_MODE == "sandbox" and settings.PAYMENT_PROVIDER == SandboxHmacProvider.name:
        return SandboxHmacProvider()
    if settings.PAYMENT_MODE in ("test", "live") and settings.PAYMENT_PROVIDER == RazorpayProvider.name:
        return RazorpayProvider()
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Configured payment provider adapter is unavailable")
