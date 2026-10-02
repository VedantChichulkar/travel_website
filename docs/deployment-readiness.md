# Maharashtra Tourist Places deployment readiness

## Private documents

The S3 adapter, authenticated streaming routes, metadata migration, audit events, and retryable object retirement are implemented. Cloud validation was not run without credentials. Real sensitive-document collection remains blocked on dedicated private-bucket configuration, least-privilege workload identity, an approved retention schedule, and production malware scanning/quarantine. See [private-document-storage.md](private-document-storage.md).

The repository now has a provider-neutral production topology for the FastAPI
API, a singleton operations worker, the customer/partner Next.js application,
and the admin Next.js application. MySQL remains a managed external dependency,
and media requires shared durable storage.

See [production-deployment.md](production-deployment.md) for the complete
architecture, environment inventory, migration procedure, backup policy,
worker responsibilities, Razorpay payment boundary, health checks, rollback
procedure, and exact release sequence.

## Current boundary

- Refresh tokens use Secure/HttpOnly/SameSite cookies and are reissued on refresh;
  access tokens remain memory-only in browser applications.
- Payment mode supports local `sandbox` plus Razorpay `test`/`live`; startup
  rejects missing or mode-mismatched credentials. Live remains configuration-gated.
- Provider-confirmed customer payments/refunds and the configuration-gated
  RazorpayX hotel payout adapter are implemented. Hotel payouts default to
  disabled, cannot be manually marked successful, and still require a controlled
  RazorpayX Test Mode E2E before live enablement.
- Expired holds, auto-checkout, no-show fallbacks, and settlement eligibility
  run through the existing idempotent scheduler in one dedicated worker.
- The existing worker now owns durable transactional-notification delivery and
  bounded retries. Live external adapters, credentials, and provider delivery
  reconciliation remain intentionally unconfigured production requirements.
