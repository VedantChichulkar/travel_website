# Travel Booking API

FastAPI backend using SQLAlchemy 2, Alembic, MySQL, and PyMySQL.

## Setup

Run these commands from this `backend` directory in Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements.private-storage.txt -r requirements.public-media.txt
Copy-Item .env.example .env # only when .env does not already exist
```

Update `DATABASE_URL` and `SECRET_KEY` in `.env`, then start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Useful URLs:

- API documentation: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Database health: <http://127.0.0.1:8000/api/v1/health>

## Migrations

With the MySQL database running and `.env` configured:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

## Verification

```powershell
.\venv\Scripts\python.exe -m compileall -q app migrations
```

Automated tests have not been added yet; this is tracked in the repository roadmap.

## Curated Place content

Reviewed customer-facing Place data is applied intentionally and idempotently, separately from Alembic and application startup:

```powershell
.\venv\Scripts\python.exe scripts\seed_curated_places.py --dry-run
.\venv\Scripts\python.exe scripts\seed_curated_places.py
```

See `docs/curated-place-data.md` for source standards, managed fields, validation rules, image policy, and the review workflow.

## Room inventory operations

Partners manage their own future room-type inventory through `GET` and `PUT`
`/api/v1/partner/room-types/{room_id}/inventory`. The update endpoint applies
settings to an inclusive date range and will reject a reduction below blocked,
confirmed, or held capacity. `POST /api/v1/bookings/holds` reserves capacity for
15 minutes (`INVENTORY_HOLD_MINUTES`) without creating a booking or payment.

Expired holds are reconciled atomically whenever inventory is read or changed
(including public availability and quote reads).

## Hotel stay operations

The partner operations API is rooted at `/api/v1/partner/operations`. It exposes
a tenant-scoped operations board, booking ID/reference/QR lookup, check-in,
check-in review, checkout, and manual no-show actions. Operational responses omit
payment, policy, and guest-contact data.

An in-process scheduler runs idempotent automatic checkout and no-show fallback
transactions. Configure it with `OPERATIONS_SCHEDULER_ENABLED`,
`OPERATIONS_SCHEDULER_INTERVAL_SECONDS`, `AUTO_CHECKOUT_GRACE_HOURS`,
`NO_SHOW_REMINDER_HOURS`, `NO_SHOW_FALLBACK_HOURS`, and
`NO_SHOW_REMINDER_OPPORTUNITY_MINUTES`. Multi-instance deployments should run one
designated scheduler instance; database row locks and booking status transitions
provide duplicate-action protection.

## Post-stay settlements

The same scheduler creates one settlement ledger entry per checked-out booking
after `SETTLEMENT_ELIGIBILITY_DAYS` (default: 7). Existing cancellation, refund,
and payment-reconciliation records determine refund deductions and automatic
holds. Partners can read only their hotel's records at `/api/v1/partner/settlements`;
administrators review them at `/api/v1/admin/settlements`.

The provider-neutral payout boundary supports the local sandbox and a
configuration-gated RazorpayX adapter. The ledger snapshots the configured
commission rule and rate; missing commission configuration holds the settlement
instead of inventing a rate. Provider acceptance remains processing and only a
verified terminal status settles the payout. Stable idempotency, signed webhook
deduplication, lookup-based recovery of uncertain POSTs, explicit reversals, and
append-only corrections preserve financial traceability. See
`docs/settlement-payout-architecture.md`.

## Verified-stay reviews

Only the customer attached to a `CHECKED_OUT` booking can create its single
review. Ratings and customer text are immutable, while hotel responses,
challenges, and moderation decisions are stored separately. Published reviews
are available at `/api/v1/hotels/{hotel_id}/reviews`; partner actions are scoped
to their hotel under `/api/v1/partner/reviews`, and the administrator queue is
at `/api/v1/admin/reviews/moderation`.

Low ratings and ordinary negative feedback publish normally. A conservative
rules-based screen holds obvious personal information, spam links, threats, or
extortion phrases for human review. Hotel challenges do not hide an otherwise
published review unless an administrator upholds the challenge.
