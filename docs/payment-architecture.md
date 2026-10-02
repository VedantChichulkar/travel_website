# Payment and booking confirmation

## Audited baseline

MAHARASHTRA TOURIST PLACES already persisted `Payment` attempts and a unique `PaymentWebhookEvent`
ledger, created server-side sandbox orders, verified HMAC callbacks, checked amount
and currency, and converted `InventoryHold` capacity through the shared inventory
service. A verified payment could enter `CONFIRMATION_REQUIRED`, but there was no
retry, escalation, customer history, durable receipt view, or admin resolution
workflow. No external provider SDK or live-provider credentials are configured.

## Provider boundary

Core payment logic depends on the small provider interface in
`app/services/payment_provider.py`: order creation, checkout/webhook signature
verification, payment lookup, refund submission, and refund lookup. The signed
`VAYORA_GATEWAY` remains for local automation. `RAZORPAY` uses the same normalized
boundary for test/live Orders, captured-payment lookup, and normal refunds.

The application never accepts a payable amount from the browser. It uses the
authenticated customer's booking, the immutable booking price snapshot, and the
server-defined currency. Card numbers, CVV, UPI PINs, banking credentials, raw
callbacks, and webhook secrets are not stored in payment records.

## State flow

1. A customer booking in `PAYMENT_PENDING` with an active inventory hold creates
   or reuses a server-side `PENDING` payment order.
2. Only cryptographically verified provider evidence can change payment state.
   Hosted Checkout evidence is HMAC-verified with the server-stored order ID and
   independently fetched; only Razorpay `captured` maps to Maharashtra Tourist Places `PAID`.
   Provider event IDs are deduplicated, and the provider order, payment reference,
   amount, currency, and booking snapshot relationship are verified server-side.
3. Verified funds are committed as `PAID` before inventory finalization is tried,
   so a later booking failure cannot erase financial history.
4. The shared inventory service locks and converts the hold. Success changes the
   booking to `CONFIRMED`, writes status history, makes the receipt available, and
   resolves reconciliation.
5. A transient failure becomes `CONFIRMATION_REQUIRED` with exponential backoff.
   The existing operations worker retries eligible cases up to the configured
   maximum. Expired or missing fulfilment capacity becomes `REFUND_REQUIRED`;
   ambiguous state becomes `MANUAL_REVIEW`. Neither state claims a refund occurred.

Admin retry and classification actions require an authenticated administrator, a
reason, and an append-only audit record. Customer history and receipt endpoints
are scoped through booking ownership. Hotel partners have no payment mutation
boundary.

## Operations

Required payment settings are documented in `backend/.env.example`. Production
requires mode-matching Razorpay credentials and a dedicated webhook secret.
Relevant structured logs contain internal payment/booking/event identifiers and
state only; they exclude secrets and raw financial payloads.

The admin Control Center shows verified financials alongside the expected booking
snapshot, customer, hotel/room, hold state, timestamps, retry count, and failure
reason. `REFUND_REQUIRED` now creates an idempotent provider refund instruction;
it is not evidence of money movement until provider completion is verified.
