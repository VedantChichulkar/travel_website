# Transactional notification delivery

In-app notifications are Maharashtra Tourist Places' primary working notification channel. They
are committed in the same database transaction as the business event and are
available even when every external provider is disabled or failing.

Each in-app notification owns one durable job per external channel: email, SMS,
and WhatsApp. Recipient plus event deduplication prevents duplicate in-app
records, while each job has a stable hashed idempotency key and a unique
notification/channel constraint.

The existing application worker processes due jobs. Provider failures move a
job to `FAILED` with exponential bounded retry metadata. Missing adapters remain
`PROVIDER_UNAVAILABLE`; they are never reported as delivered. A later provider
configuration automatically activates the applicable backlog. A successful job
is immutable `SENT`, so worker retries do not resend it.

## Provider boundary

The provider contract accepts a channel, recipient address, transactional title
and body, and stable idempotency key. No live provider is selected. The optional
`VAYORA_NOTIFICATION_SANDBOX` adapter performs no external delivery and exists
only for lifecycle testing.

Configuration:

- `NOTIFICATION_MODE`: `disabled` or `sandbox`;
- `NOTIFICATION_EMAIL_PROVIDER`;
- `NOTIFICATION_SMS_PROVIDER`;
- `NOTIFICATION_WHATSAPP_PROVIDER`;
- `NOTIFICATION_RETRY_MAX_ATTEMPTS`;
- `NOTIFICATION_RETRY_BACKOFF_MINUTES`.

Provider credentials are intentionally absent until a business-approved live
adapter is implemented. Provider exception text is not persisted or logged,
and ordinary message notifications never include private message contents.

Production activation still requires provider selection, credentials managed by
the deployment secret store, sender/domain and WhatsApp template approval,
delivery/webhook reconciliation as required by that provider, consent and
regional compliance review, and operational alerting for exhausted retries.
