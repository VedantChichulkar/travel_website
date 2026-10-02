# Refund execution and reconciliation

## Audited baseline

MAHARASHTRA TOURIST PLACES already calculated cancellation outcomes from the immutable booking policy
snapshot, restored inventory through the shared inventory service, persisted
`Cancellation` and `Refund` rows, exposed manual-review controls, emitted refund
notifications, and deducted completed refunds from settlements. The previous
completion route could, however, let an administrator mark a refund successful
without verified provider evidence. Refund rows also received synthetic provider
references before a provider instruction existed, and there was no callback,
status-check, retry, or refund reconciliation workflow.

## Authoritative lifecycle

The backend calculates the refundable amount and validates it against the captured
payment and every existing refund instruction. A cancellation creates one stable,
idempotent refund instruction. The provider may accept that instruction into
`PROCESSING`, but acceptance never means completion.

Only a cryptographically verified provider callback or a reconciled provider
status can move a refund to `SUCCEEDED`. Pending, rejected, unavailable, timeout,
and unknown responses remain visible as `PROCESSING`, `FAILED`,
`RETRY_REQUIRED`, `RECONCILIATION_REQUIRED`, or `MANUAL_REVIEW`. Provider event
IDs use the existing webhook ledger and duplicate callbacks are harmless.

The sandbox adapter remains available for local automation. The Razorpay adapter
submits normal full/partial refunds in currency subunits, uses the Maharashtra Tourist Places refund
idempotency key as the provider receipt, and maps `pending`, `processed`, and
`failed` without treating API acceptance as completion. A submission timeout is
uncertain and enters reconciliation rather than blind resubmission.

## Reconciliation and settlements

The existing worker submits missing payment-reconciliation refunds, retries safe
provider instructions with the same idempotency key, and checks pending provider
refunds with bounded backoff. It never creates a second refund because local state
is stale.

Before payout, provider-confirmed refunds update the settlement deduction and net
payable. After a settlement is immutable, the refund creates one append-only
future `REVERSAL` adjustment instead of rewriting the settled snapshot. Refund
callbacks never touch inventory; inventory restoration remains part of the
idempotent cancellation transaction.

Admin actions require a reason and are audited. Administrators can retry, request
provider reconciliation, or place a refund into manual review, but cannot declare
provider completion. Customer refund details are reachable only through their own
booking and contain no raw provider payloads or secrets.
