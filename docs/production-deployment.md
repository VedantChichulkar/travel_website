# Maharashtra Tourist Places production deployment

This release contains production-capable Razorpay collection/refund and RazorpayX hotel-payout adapters. Both default to disabled and are independently gated. Customer payments require their own activation and validation. Hotel payouts require RazorpayX activation, Test Mode credentials, signed webhook delivery, and a controlled synthetic payout before live use.

Private operational documents use the provider-neutral storage boundary and the production Amazon S3 adapter documented in [private-document-storage.md](private-document-storage.md). Before accepting real hotel verification or Safari traveller files, configure the dedicated private bucket and workload role, validate the synthetic-file procedure, approve retention periods, and deploy an external malware scanning/quarantine control.

## Architecture and required services

| Runtime | Source | Purpose | Persistence |
| --- | --- | --- | --- |
| Customer + Hotel Partner web | `frontend/` | Customer routes and `/partner/*` | Stateless Node.js service/CDN |
| Admin web | `admin/` | Restricted operations portal | Stateless Node.js service/CDN |
| API | `backend/` | FastAPI, RBAC, tenant isolation and business services | Persistent web service |
| Operations worker | backend image, `python -m app.worker` | Holds, stay fallbacks and settlement eligibility | Exactly one persistent instance |
| Database | external MySQL | Transactional source of truth | Managed service with TLS and backups |
| Hotel media | `MEDIA_ROOT` | Uploaded hotel images | Shared persistent volume or object storage |

Use sibling HTTPS hosts under the same registrable domain for the API, customer site, and admin site. This lets the Secure, HttpOnly, SameSite=Lax refresh cookie work without weakening CSRF protection. Access tokens remain only in browser memory. Bearer tokens remain supported for non-browser API clients.

## Environment variables

The committed `.env.example` files contain names only. Store real values in the hosting platform's secret manager. Never commit `.env.production`.

### Backend

- `PROJECT_NAME`: safe service label; `ENVIRONMENT` must be `production` and `DEBUG` must be `false`.
- `DATABASE_URL`: TLS-enabled `mysql+pymysql` URL for the application account.
- `SECRET_KEY`: unique random JWT signing key, at least 32 characters.
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`: session lifetimes.
- `AUTH_COOKIE_NAME`, `AUTH_COOKIE_DOMAIN`: refresh-cookie name and optional domain. Prefer a host-only cookie.
- `AUTH_COOKIE_SECURE`: must be `true`.
- `AUTH_COOKIE_SAMESITE`: `lax` or `strict`.
- `CORS_ORIGINS`: JSON list containing only the exact HTTPS customer and admin origins.
- `TRUSTED_HOSTS`: JSON list of API hostnames accepted in the Host header.
- `LOG_LEVEL`: normally `INFO`; `LOG_FORMAT` must be `json`.
- `MEDIA_ROOT`, `MEDIA_URL`, `MEDIA_BASE_URL`, `HOTEL_IMAGE_MAX_BYTES`: durable media settings; the base URL must use HTTPS.
- `BOOKING_TAX_RATE`, `BOOKING_PLATFORM_FEE`, `INVENTORY_HOLD_MINUTES`, `INVENTORY_FRESHNESS_HOURS`: booking settings.
- `AUTO_CHECKOUT_GRACE_HOURS`, `NO_SHOW_REMINDER_HOURS`, `NO_SHOW_FALLBACK_HOURS`, `NO_SHOW_REMINDER_OPPORTUNITY_MINUTES`: stay fallbacks.
- `OPERATIONS_SCHEDULER_ENABLED`, `OPERATIONS_SCHEDULER_INTERVAL_SECONDS`, `SETTLEMENT_ELIGIBILITY_DAYS`: worker settings.
- `PAYMENT_PROVIDER`: `VAYORA_GATEWAY` for local sandbox or `RAZORPAY` for the regulated provider adapter.
- `PAYMENT_MODE`: `disabled`, `sandbox`, `test`, or `live`. Razorpay accepts only `test`/`live`; live mode is rejected outside `ENVIRONMENT=production`.
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`: mode-specific dashboard credentials. Only the key ID reaches hosted Checkout; both secrets remain server-side.
- `RAZORPAY_API_BASE_URL`: retain the official `https://api.razorpay.com/v1` endpoint unless an approved test transport is deliberately configured.
- `PAYMENT_PROVIDER_TIMEOUT_SECONDS`: bounded API timeout (2–30 seconds).
- `FINANCIAL_COMPLETION_ENABLED`: must be `true` for live collection/refund execution; it does not enable hotel payouts.
- `PAYOUT_PROVIDER`, `PAYOUT_MODE`, `PAYOUT_EXECUTION_ENABLED`, `PAYOUT_AUTO_INITIATE`: use `RAZORPAYX`, `test`/`live`, explicit execution enablement, and a deliberate auto-initiation choice. Keep disabled for initial deployment.
- `RAZORPAYX_KEY_ID`, `RAZORPAYX_KEY_SECRET`, `RAZORPAYX_WEBHOOK_SECRET`, `RAZORPAYX_ACCOUNT_NUMBER`: mode-specific server secrets and debit account identifier. The payout webhook secret must be dedicated.
- `RAZORPAYX_API_BASE_URL`, `RAZORPAYX_PAYOUT_MODE`, `RAZORPAYX_PAYOUT_PURPOSE`, `RAZORPAYX_PAYOUT_NARRATION`, `RAZORPAYX_MIN_PAYOUT_AMOUNT`: provider endpoint and approved operational policy.
- `PAYOUT_PROVIDER_TIMEOUT_SECONDS`, `PAYOUT_RECONCILIATION_MAX_ATTEMPTS`, `PAYOUT_RECONCILIATION_BACKOFF_MINUTES`: bounded payout network/reconciliation controls.

Run `python scripts/check_production_config.py` in the backend image before rollout. It reports only non-sensitive mode flags.

### Customer/partner build

- `NEXT_PUBLIC_API_URL`: public HTTPS API URL ending in `/api/v1`.
- `NEXT_PUBLIC_SITE_URL`: canonical customer origin.
- `NEXT_PUBLIC_ADMIN_PORTAL_URL`: absolute admin login URL.

### Admin build

- `NEXT_PUBLIC_API_URL`: public HTTPS API URL ending in `/api/v1`.
- `NEXT_PUBLIC_CUSTOMER_PORTAL_URL`: customer origin for role-correction links.

`NEXT_PUBLIC_*` values are embedded during `next build`; rebuild when they change. `TRUSTED_PROXY_IPS` is a compose-host value and must identify the exact reverse proxy address or CIDR—never `*`.

## Database deployment and backups

1. Provision a production-compatible MySQL version with encrypted connections.
2. Use a least-privilege runtime user and a separate migration identity where supported.
3. Enable automated backups, point-in-time recovery, retention alerts, and policy-required cross-region copies.
4. Test restoration into an isolated database before launch and regularly afterward.
5. Stop a release if the pre-migration snapshot cannot be verified.
6. From one release job run `alembic heads`, `alembic current`, `alembic upgrade head`, then `alembic current`.
7. Never run migrations concurrently from every API replica.

`scripts/verify_fresh_migrations.py` creates and drops a uniquely named disposable database and verifies base-to-head migration. Never point it at the production database name.

## Background jobs

Run exactly one dedicated worker and set `OPERATIONS_SCHEDULER_ENABLED=false` on all API replicas.

| Concern | Current execution |
| --- | --- |
| Expired inventory holds | Worker sweep plus request-time reconciliation |
| Auto-checkout | Worker |
| No-show reminder/fallback | Worker |
| Settlement eligibility/automatic holds | Worker |
| Notification delivery | Existing worker delivers configured channels with durable bounded retries; unconfigured channels remain `PROVIDER_UNAVAILABLE` |
| Payment reconciliation | Signed webhooks, immediate API verification after Checkout, and worker lookup of unresolved orders |
| Refund reconciliation | Stable refund receipt/idempotency key, signed events, and worker status lookup with bounded backoff |
| Hotel payout reconciliation | Stable payout reference/idempotency key, signed events, and worker lookup of processing/uncertain payouts |

Do not scale the worker above one until a database-backed leader lease exists.

## Razorpay payment and refund setup

Official references used: [Orders API](https://razorpay.com/docs/api/orders/create/), [Standard Checkout and signature verification](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/), [webhook validation](https://razorpay.com/docs/webhooks/validate-test/), [fetch payment](https://razorpay.com/docs/api/payments/fetch-with-id/), [create refund](https://razorpay.com/docs/api/refunds/create-normal/), and [fetch refund](https://razorpay.com/docs/api/refunds/fetch-with-id/).

1. Activate the merchant account and separately generate test and live API keys. Never reuse a test key in live mode; startup validates the key-ID prefix.
2. Enable automatic capture in the Razorpay Dashboard. Maharashtra Tourist Places fulfils only `captured` payments, never merely `authorized` ones.
3. In Test Mode configure `https://<api-host>/api/v1/bookings/payments/webhooks/RAZORPAY` for `payment.authorized`, `payment.captured`, `payment.failed`, and `order.paid`.
4. Configure `https://<api-host>/api/v1/bookings/payments/refunds/webhooks/RAZORPAY` for `refund.created`, `refund.processed`, and `refund.failed`.
5. Use a dedicated webhook secret of at least 32 characters. Razorpay signs the raw body in `X-Razorpay-Signature`; the endpoint is public but rejects invalid signatures.
6. Permit the exact customer/partner frontend origin through CORS. Hosted Checkout loads from `https://checkout.razorpay.com`; no Razorpay secret belongs in a frontend environment variable or bundle.
7. Run the worker continuously. It reconciles captured orders whose webhook was delayed and pending refunds whose completion event was missed.
8. Make one controlled Test Mode transaction for each domain subject, then verify a full and policy-permitted partial refund. Test keys never move real money.
9. Monitor admin financial operations, receipts, settlement holds, webhook rejection logs, provider failures, aged pending payments, and refunds in reconciliation/manual review.

Checkout success is only evidence submitted to the API. The API verifies the checkout HMAC, fetches the payment, checks provider order, amount, currency and `captured` state, and then enters the existing idempotent Maharashtra Tourist Places state machine. Webhooks independently follow the same path. Refund API acceptance remains `PROCESSING`; only `refund.processed` or reconciled provider status completes it. A stable refund receipt prevents duplicate submission, while a timeout is classified as uncertain rather than blindly retried.

## RazorpayX hotel payout setup

See [settlement-payout-architecture.md](settlement-payout-architecture.md) for the authority boundary, state mapping, idempotency, reversal, bank-change, and recovery rules. Activate RazorpayX and its debit account, create separate Test/Live API keys, then configure `https://<api-host>/api/v1/payouts/webhook` for payout status events with a dedicated secret. Start with Test Mode and `PAYOUT_AUTO_INITIATE=false`; run a synthetic supported bank-account payout, verify lookup and signed webhook handling, replay the event to confirm deduplication, and exercise provider-supported failure/reversal tooling. Enable live mode only after finance approves monitoring, limits, retry operations, and emergency disable. Credentials were not available during repository validation, so provider Test Mode E2E remains a launch blocker.

## Build and deployment

The compose topology expects managed MySQL and real production values supplied outside Git:

```text
docker compose -f compose.production.yaml build
docker compose -f compose.production.yaml run --rm backend alembic upgrade head
docker compose -f compose.production.yaml up -d
```

The Dockerfiles can also be deployed independently. On a native Next.js host, use `frontend/` and `admin/` as separate project roots and retain their build-time variables.

## Health and observability

- `/api/v1/health/live`: process liveness without MySQL.
- `/api/v1/health/ready`: readiness using `SELECT 1`, returning 503 when unavailable.
- `/api/v1/health`: compatibility database-readiness endpoint.

Alert on repeated readiness failures, worker exceptions, payment reconciliation-required records, provider-unavailable notification backlog, and failed migrations. JSON logs redact common bearer tokens, secrets, passwords, database URL passwords, and exception text. SQL parameter values are hidden in production.

## Rollback basics

1. Stop traffic and the worker if data compatibility is uncertain.
2. Roll back to the previous immutable image digest.
3. Prefer a forward-fix migration. Downgrade only after reviewing its exact SQL and confirming it is non-destructive.
4. Restore the verified pre-release snapshot only when a forward fix is unsafe and the operation is explicitly approved.
5. Re-run readiness, authentication, tenant-isolation, booking, and sandbox-payment smoke tests before reopening traffic.

For a collection incident, set `PAYMENT_MODE=disabled`. For a payout incident, set `PAYOUT_MODE=disabled`, `PAYOUT_EXECUTION_ENABLED=false`, and `PAYOUT_AUTO_INITIATE=false`. Restart API/worker before rolling back images. Do not delete financial rows, replay refunds, or resubmit uncertain payouts. Reconcile every in-flight provider reference first; a code rollback does not reverse remote actions.

## Exact release sequence

1. Create managed MySQL and durable media storage.
2. Configure DNS/TLS for sibling customer, admin, and API hosts.
3. Populate secret-manager variables from the three name-only examples.
4. Deploy first with Razorpay test mode, test credentials, financial completion enabled, and the API scheduler disabled.
5. Validate configuration with `check_production_config.py`.
6. Take and verify a database backup.
7. Run migrations once and confirm the single head.
8. Build immutable backend, worker, frontend, and admin images.
9. Deploy the API and verify liveness/readiness.
10. Deploy exactly one worker and confirm one successful cycle.
11. Deploy both web applications with their production URL build arguments.
12. Complete controlled Test Mode payment/refund checks and verify signed webhooks, duplicate delivery, callback/webhook ordering, cancellation, reconciliation, and receipts.
13. Confirm manual paid/refund/payout bypasses remain absent, leave hotel payouts disabled until the separate synthetic RazorpayX Test Mode E2E passes, and report missing notification providers honestly.
14. Verify logs, alerts, media persistence, backup restoration, and rollback.
