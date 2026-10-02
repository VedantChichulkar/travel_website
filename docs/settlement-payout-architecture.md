# Settlement and hotel payout lifecycle

Maharashtra Tourist Places owns payout eligibility and financial amounts. RazorpayX executes an
already-authorized instruction; it never decides whether a stay, refund,
dispute, commission, adjustment, or hotel cancellation is payable.

## Existing settlement authority

There is one settlement per booking and one payout per settlement. The existing
eligibility service requires a captured/reconciled payment, checked-out stay or
policy-supported finalized no-show, the checkout/no-show timestamp plus
`SETTLEMENT_ELIGIBILITY_DAYS` (7 by default), and no blocking cancellation,
refund review, open dispute, or manual-review condition. Auto-checkout supplies
the canonical booking checkout timestamp. No payout-specific eligibility or
checkout clock exists.

At settlement creation Maharashtra Tourist Places snapshots captured gross, provider-confirmed
refund deductions, the configured commission rate and rule, one-time carried
adjustments, and net payable. The formula remains:

`net payable = gross - refund deductions - commission + adjustments`

Missing commission configuration holds the settlement. Historical economics
are not recomputed from current pricing or commission settings, settled
financial fields are immutable, and later corrections remain append-only. No
tax/TDS rate is invented; an approved future deduction can use the existing
adjustment ledger after accounting policy is finalized.

## Provider and destination architecture

The production adapter is RazorpayX Payouts. It uses the composite bank payout
endpoint to provide the required contact and bank fund account while creating
the payout. RazorpayX may reuse matching provider-side entities. Maharashtra Tourist Places stores
only returned provider contact/fund-account IDs, payout ID, UTR, and a keyed
destination fingerprint on the payout record. Provider objects do not escape
the adapter.

Hotel bank account, IFSC, and beneficiary name remain encrypted at rest in the
approved `hotel_verifications` record and are decrypted only in backend memory
for submission. APIs and UI return masked account data. Logs, audit reasons,
URLs, webhook ledgers, and frontend bundles never contain full bank details.
The hotel verification must be approved and complete; this is a Maharashtra Tourist Places
governance check, not a claim that RazorpayX verified account ownership.

The fingerprint binds a reserved payout to its authorized destination. A bank
change cannot redirect an in-flight payout. A controlled resubmission is
rejected when the current destination fingerprint differs and requires finance
review/re-verification.

## Submission, states, and idempotency

The server locks and rechecks canonical eligibility immediately before it
creates a durable local payout instruction. The database transaction is
committed before the network call, so a provider call does not hold a database
lock. Amount, currency, and destination come only from Maharashtra Tourist Places records.

Each payout uses `settlement-<id>-v1` as its stable internal/reference identity
and a deterministic UUID in RazorpayX's `X-Payout-Idempotency` header. Database
uniqueness enforces one payout per settlement, one idempotency key, and one
provider payout ID.

Provider mapping:

| RazorpayX state | Maharashtra Tourist Places payout | Maharashtra Tourist Places settlement |
| --- | --- | --- |
| `queued`, `pending`, `processing` | `PROCESSING` | `PROCESSING` |
| `processed` | `SUCCESS` | `SETTLED` |
| `rejected`, `failed`, `cancelled` | `FAILED` | `RECONCILIATION_REQUIRED` |
| `reversed` | `REVERSED` | `RECONCILIATION_REQUIRED` |
| unknown/mismatched financial data | `RECONCILIATION_REQUIRED` | `RECONCILIATION_REQUIRED` |

API acceptance is not payment completion. Only provider `processed`, received
through a verified webhook or lookup, settles the record. A later `reversed`
event moves an apparently paid settlement into finance reconciliation; stale
non-reversal events cannot undo success or reversal.

A POST transport failure is an uncertain outcome. Maharashtra Tourist Places never blindly issues a
second payout: the worker/admin lookup searches by the stable `reference_id`.
Only an explicit no-result lookup permits controlled resubmission, and the same
idempotency identity and destination fingerprint are reused. Financial mismatch
always requires manual reconciliation.

## Webhooks and reconciliation

Configure `POST /api/v1/payouts/webhook` with a dedicated RazorpayX webhook
secret. The adapter validates `X-Razorpay-Signature` over the raw request body
before parsing or mutation. The unique provider/event ledger stores only an
event ID and payload hash. Duplicate or webhook/poll races are idempotent.

The operations worker reconciles due `PROCESSING` and
`RECONCILIATION_REQUIRED` payouts with bounded attempts and backoff. Admins may
request a lookup and may retry only after definitive failure or confirmed
provider absence; there is no Mark Paid control. Partner UI shows business
states and optional UTR, while admin UI shows safe failure/reconciliation detail.
Meaningful submission, recovery, paid, failed, reversed, reconciled, and retry
transitions are recorded in settlement events and/or admin audit logs.

## Provider configuration and activation

Defaults are `PAYOUT_MODE=disabled` and `PAYOUT_EXECUTION_ENABLED=false`.
Sandbox uses only `VAYORA_PAYOUT_SANDBOX` outside production. Real modes use
`PAYOUT_PROVIDER=RAZORPAYX`, explicit execution enablement, mode-matched
`rzp_test_`/`rzp_live_` credentials, debit account identifier, dedicated
webhook secret, HTTPS endpoint, bounded timeout, payout rail, purpose,
narration, and configured INR minimum. Test mode is rejected in production;
live mode is rejected outside production.

Official references: [composite payout and idempotency](https://razorpay.com/docs/api/x/payout-wallet/create/payout-composite/?preferred-country=IN),
[payout lookup and statuses](https://razorpay.com/docs/api/x/payouts/fetch-all//?preferred-country=IN),
[RazorpayX Payouts](https://razorpay.com/x/payouts/), and
[webhook payloads](https://axisbank-docs.razorpay.com/razorpayx/webhooks/payloads/).

Before production enablement, activate RazorpayX for the legal entity and debit
account, create separate Test/Live keys, configure and validate the signed
webhook, run a synthetic Test Mode payout and status lookup, confirm the account
and rail limits with Razorpay, and establish finance monitoring for aged,
failed, reversed, and reconciliation-required payouts. No real hotel account
should be used for sandbox validation.

Emergency disable: set `PAYOUT_MODE=disabled`,
`PAYOUT_EXECUTION_ENABLED=false`, and `PAYOUT_AUTO_INITIATE=false`, restart API
and worker, then reconcile every in-flight provider reference. Disabling or
rolling back code does not reverse remote payouts.
