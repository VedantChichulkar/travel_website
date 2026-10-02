"""Transactional-notification provider boundary with no live provider selected."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Protocol

from app.core.config import settings
from app.models.communication import NotificationChannel


class NotificationProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class DeliveryResult:
    provider_message_id: str


class TransactionalNotificationProvider(Protocol):
    name: str
    supported_channels: frozenset[NotificationChannel]

    def send(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        title: str,
        body: str,
        idempotency_key: str,
    ) -> DeliveryResult: ...


class SandboxNotificationProvider:
    """Explicit test adapter; it performs no paid or external delivery."""

    name = "VAYORA_NOTIFICATION_SANDBOX"
    supported_channels = frozenset(NotificationChannel)

    def send(self, *, channel: NotificationChannel, recipient: str, title: str, body: str, idempotency_key: str) -> DeliveryResult:
        del recipient, title, body
        digest = hashlib.sha256(f"{channel.value}:{idempotency_key}".encode("utf-8")).hexdigest()[:32]
        return DeliveryResult(provider_message_id=f"sandbox-{digest}")


def configured_name(channel: NotificationChannel) -> str | None:
    if settings.NOTIFICATION_MODE == "disabled":
        return None
    names = {
        NotificationChannel.EMAIL: settings.NOTIFICATION_EMAIL_PROVIDER,
        NotificationChannel.SMS: settings.NOTIFICATION_SMS_PROVIDER,
        NotificationChannel.WHATSAPP: settings.NOTIFICATION_WHATSAPP_PROVIDER,
    }
    name = names[channel].strip()
    if settings.NOTIFICATION_MODE == "sandbox" and name == SandboxNotificationProvider.name:
        return name
    return None


def configured_provider(channel: NotificationChannel) -> TransactionalNotificationProvider:
    name = configured_name(channel)
    if name == SandboxNotificationProvider.name:
        return SandboxNotificationProvider()
    raise NotificationProviderUnavailable(f"No {channel.value.lower()} transactional provider is configured")
