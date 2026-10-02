"""Provider-neutral payout boundary and RazorpayX implementation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PayoutDestination:
    reference: str
    beneficiary_name: str
    bank_account_number: str
    bank_ifsc: str
    fingerprint: str


@dataclass(frozen=True)
class ProviderPayout:
    provider_payout_id: str
    status: str
    amount: Decimal
    currency: str
    provider_contact_id: str | None = None
    provider_fund_account_id: str | None = None
    utr: str | None = None


@dataclass(frozen=True)
class ProviderPayoutEvent:
    event_id: str
    provider_payout_id: str
    status: str
    amount: Decimal
    currency: str
    failure_reason: str | None = None
    utr: str | None = None


class ProviderOutcomeUnknown(RuntimeError):
    """A mutating payout request may have succeeded remotely."""


class PayoutProvider(Protocol):
    name: str

    def create_payout(self, *, destination: PayoutDestination, amount: Decimal, currency: str, idempotency_key: str) -> ProviderPayout: ...
    def fetch_payout(self, provider_payout_id: str) -> ProviderPayout: ...
    def find_payout_by_reference(self, idempotency_key: str) -> ProviderPayout | None: ...
    def verify_payout_callback(self, payload: bytes, signature: str | None) -> bool: ...
    def parse_payout_callback(self, payload: bytes, event_id: str | None) -> ProviderPayoutEvent: ...


class SandboxPayoutProvider:
    """Explicit opt-in adapter for lifecycle testing; it never reports success itself."""

    name = "VAYORA_PAYOUT_SANDBOX"

    def create_payout(self, *, destination: PayoutDestination, amount: Decimal, currency: str, idempotency_key: str) -> ProviderPayout:
        del destination, idempotency_key
        return ProviderPayout(f"vyp_{secrets.token_urlsafe(18)}", "processing", amount, currency)

    def fetch_payout(self, provider_payout_id: str) -> ProviderPayout:
        return ProviderPayout(provider_payout_id, "processing", Decimal("0"), "INR")

    def find_payout_by_reference(self, idempotency_key: str) -> ProviderPayout | None:
        del idempotency_key
        return None

    def verify_payout_callback(self, payload: bytes, signature: str | None) -> bool:
        if not signature or not settings.PAYOUT_WEBHOOK_SECRET:
            return False
        expected = hmac.new(settings.PAYOUT_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_payout_callback(self, payload: bytes, event_id: str | None) -> ProviderPayoutEvent:
        try:
            data = json.loads(payload)
            return ProviderPayoutEvent(event_id=event_id or str(data["event_id"]), provider_payout_id=str(data["payout_reference"]), status=str(data["status"]), amount=Decimal(str(data["amount"])), currency=str(data["currency"]).upper())
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Invalid payout callback payload") from exc


class RazorpayXPayoutProvider:
    """RazorpayX composite bank payout adapter with bounded network calls."""

    name = "RAZORPAYX"

    @staticmethod
    def _subunits(amount: Decimal) -> int:
        return int(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)

    @staticmethod
    def _amount(value: object) -> Decimal:
        return (Decimal(str(value)) / 100).quantize(Decimal("0.01"))

    @staticmethod
    def _stable_reference(idempotency_key: str) -> str:
        return idempotency_key[:40]

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None, *, headers: dict[str, str] | None = None) -> dict[str, object]:
        body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
        credentials = base64.b64encode(f"{settings.RAZORPAYX_KEY_ID}:{settings.RAZORPAYX_KEY_SECRET}".encode()).decode()
        request_headers = {"Authorization": f"Basic {credentials}", "Content-Type": "application/json", **(headers or {})}
        request = Request(f"{settings.RAZORPAYX_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}", data=body, method=method, headers=request_headers)
        try:
            with urlopen(request, timeout=settings.PAYOUT_PROVIDER_TIMEOUT_SECONDS) as response:  # noqa: S310
                parsed = json.loads(response.read().decode())
        except HTTPError as exc:
            description = "Payout provider rejected the request"
            try:
                description = str(json.loads(exc.read().decode()).get("error", {}).get("description") or description)
            except (ValueError, AttributeError, UnicodeDecodeError):
                pass
            logger.warning("RazorpayX request rejected", extra={"provider": self.name, "operation": path.split("?")[0], "http_status": exc.code})
            if method == "POST" and exc.code >= 500:
                raise ProviderOutcomeUnknown("Payout provider request outcome is unknown") from exc
            raise HTTPException(status_code=502, detail=description[:200]) from exc
        except (TimeoutError, URLError, OSError) as exc:
            logger.warning("RazorpayX request outcome unavailable", extra={"provider": self.name, "operation": path.split("?")[0]})
            if method == "POST":
                raise ProviderOutcomeUnknown("Payout provider request outcome is unknown") from exc
            raise HTTPException(status_code=503, detail="Payout provider is temporarily unavailable") from exc
        except (ValueError, UnicodeDecodeError) as exc:
            if method == "POST":
                raise ProviderOutcomeUnknown("Payout provider response was unavailable after submission") from exc
            raise HTTPException(status_code=502, detail="Payout provider returned an invalid response") from exc
        if not isinstance(parsed, dict):
            if method == "POST":
                raise ProviderOutcomeUnknown("Payout provider response was invalid after submission")
            raise HTTPException(status_code=502, detail="Payout provider returned an invalid response")
        return parsed

    def _payout(self, data: dict[str, object]) -> ProviderPayout:
        payout_id = str(data.get("id", ""))
        if not payout_id:
            raise HTTPException(status_code=502, detail="Payout provider returned no payout reference")
        fund = data.get("fund_account") if isinstance(data.get("fund_account"), dict) else {}
        contact = fund.get("contact") if isinstance(fund, dict) and isinstance(fund.get("contact"), dict) else {}
        return ProviderPayout(
            payout_id, str(data.get("status", "unknown")).lower(), self._amount(data.get("amount", 0)), str(data.get("currency", "")).upper(),
            str(contact.get("id")) if contact.get("id") else None, str(data.get("fund_account_id")) if data.get("fund_account_id") else None,
            str(data.get("utr")) if data.get("utr") else None,
        )

    def create_payout(self, *, destination: PayoutDestination, amount: Decimal, currency: str, idempotency_key: str) -> ProviderPayout:
        currency = currency.upper()
        if currency != "INR":
            raise HTTPException(status_code=422, detail="RazorpayX hotel payouts support INR only")
        reference = self._stable_reference(idempotency_key)
        response = self._request("POST", "payouts", {
            "account_number": settings.RAZORPAYX_ACCOUNT_NUMBER, "amount": self._subunits(amount), "currency": currency,
            "mode": settings.RAZORPAYX_PAYOUT_MODE, "purpose": settings.RAZORPAYX_PAYOUT_PURPOSE,
            "reference_id": reference, "narration": settings.RAZORPAYX_PAYOUT_NARRATION,
            "fund_account": {
                "account_type": "bank_account",
                "bank_account": {"name": destination.beneficiary_name, "ifsc": destination.bank_ifsc, "account_number": destination.bank_account_number},
                "contact": {"name": destination.beneficiary_name, "type": "vendor", "reference_id": destination.reference[:40], "notes": {"vayora_destination": destination.fingerprint[:32]}},
            },
            "notes": {"vayora_payout": reference},
        }, headers={"X-Payout-Idempotency": str(uuid.uuid5(uuid.NAMESPACE_URL, idempotency_key))})
        try:
            return self._payout(response)
        except HTTPException as exc:
            raise ProviderOutcomeUnknown("Payout provider acceptance could not be identified safely") from exc

    def fetch_payout(self, provider_payout_id: str) -> ProviderPayout:
        return self._payout(self._request("GET", f"payouts/{quote(provider_payout_id, safe='')}"))

    def find_payout_by_reference(self, idempotency_key: str) -> ProviderPayout | None:
        reference = self._stable_reference(idempotency_key)
        query = urlencode({"account_number": settings.RAZORPAYX_ACCOUNT_NUMBER, "reference_id": reference, "count": 10})
        response = self._request("GET", f"payouts?{query}")
        items = response.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=502, detail="Payout provider returned an invalid lookup response")
        matches = [item for item in items if isinstance(item, dict) and item.get("reference_id") == reference]
        if not matches:
            return None
        if len(matches) != 1:
            raise HTTPException(status_code=409, detail="Provider returned multiple payouts for one Maharashtra Tourist Places reference")
        return self._payout(matches[0])

    def verify_payout_callback(self, payload: bytes, signature: str | None) -> bool:
        if not signature or not settings.RAZORPAYX_WEBHOOK_SECRET:
            return False
        expected = hmac.new(settings.RAZORPAYX_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_payout_callback(self, payload: bytes, event_id: str | None) -> ProviderPayoutEvent:
        try:
            data = json.loads(payload)
            event_name = str(data["event"])
            entity = data["payload"]["payout"]["entity"]
            if not event_name.startswith("payout.") or not isinstance(entity, dict):
                raise ValueError("Unsupported event")
            failure = entity.get("failure_reason")
            if not failure and isinstance(entity.get("error"), dict):
                failure = entity["error"].get("description")
            return ProviderPayoutEvent(
                event_id or hashlib.sha256(payload).hexdigest(), str(entity["id"]), str(entity["status"]),
                self._amount(entity["amount"]), str(entity["currency"]).upper(),
                str(failure)[:200] if failure else None, str(entity.get("utr")) if entity.get("utr") else None,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Invalid payout callback payload") from exc


def configured_provider() -> PayoutProvider:
    if settings.PAYOUT_MODE == "disabled" or not settings.PAYOUT_PROVIDER:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No payout provider is configured")
    if settings.PAYOUT_MODE == "sandbox" and settings.PAYOUT_PROVIDER == SandboxPayoutProvider.name:
        return SandboxPayoutProvider()
    if settings.PAYOUT_MODE in ("test", "live") and settings.PAYOUT_PROVIDER == RazorpayXPayoutProvider.name:
        return RazorpayXPayoutProvider()
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Configured payout provider adapter is unavailable")
