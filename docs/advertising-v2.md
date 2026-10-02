# Maharashtra Tourist Places Advertising V2

## Architecture and ownership

Advertising V2 extends the existing `AdvertisingCampaign` engine. It does not create a parallel External-campaign system.

- `HOTEL` campaigns belong to one canonical Maharashtra Tourist Places Hotel. Their owner is the Hotel Partner already authorized to manage that Hotel.
- `EXTERNAL` campaigns belong to one `AdvertiserProfile`. The profile belongs one-to-one to an existing Customer account and does not grant Hotel Partner or Admin privileges.
- A database check constraint requires exactly one owner: Hotel or External advertiser. Existing campaign IDs, payments, analytics, and history are preserved and backfilled as `HOTEL`.
- Advertiser status (`ACTIVE` or `SUSPENDED`) is separate from campaign status.

External businesses use the normal Maharashtra Tourist Places registration, email-verification, login, refresh-token, password-reset, and account-security implementation. They create a profile in `/advertiser`; there is no second credential system and no fake Hotel, room inventory, Hotel onboarding, or Hotel verification record.

## Lifecycle and financial boundary

The canonical lifecycle remains:

`DRAFT → PAYMENT_PENDING → PENDING_REVIEW → SCHEDULED/ACTIVE → EXPIRED`

With governed alternatives: `NEEDS_CHANGES`, `REJECTED`, `PAUSED`, and `CANCELLED`.

The activation invariant is:

`active owner + valid creative/target + PAID payment + Admin approval + current schedule = delivery eligible`

Payment success never approves or activates a campaign. Admin approval rejects unpaid campaigns. The configured server-side plan determines placement, duration, currency, and amount; browser input is not authoritative. Payment order creation is idempotent while an order is pending or paid.

A paid rejection sets `refund_review_required`. Advertising refund policy is not defined by the current product rules, so Maharashtra Tourist Places does not silently retain or automatically refund the payment. Operations must make the policy decision through the existing financial controls. This is the remaining business-policy decision.

## Targets and material changes

Hotel destinations are canonical Maharashtra Tourist Places Hotel detail routes; Partners cannot replace them with external URLs.

External targets must be absolute HTTPS URLs on a public hostname, without credentials, fragments, custom ports, local/single-label names, IP loopback, link-local, or private/reserved IP literals. `javascript:`, `data:`, `file:`, HTTP, malformed targets, localhost, and private network literals are rejected.

At approval, Maharashtra Tourist Places snapshots `approved_target_url`. Public clicks use `/api/v1/ads/{public_id}/click`; the destination is loaded from the approved campaign record and never from a request query parameter. The endpoint rechecks campaign eligibility, records a deduplicated click, applies `no-referrer`, and redirects to the approved URL. This prevents open-redirect substitution.

Changing an approved target, headline, material copy, or creative clears approval and moves the campaign to `NEEDS_CHANGES`, immediately stopping public delivery until resubmission and another Admin approval.

## Public creative media and rights

Advertising creative is public media, not a private KYC document. External uploads accept JPEG, PNG, and WebP only and verify declared MIME, magic bytes, decodability, pixel safety, maximum bytes, and a minimum 640×360 size. Images are EXIF-oriented, resized to a 2400-pixel bound, metadata-stripped, and stored as opaque-name WebP assets under the public media root.

Advertisers must attest they have rights or authorization and may supply provenance/source information. The attestation is displayed to Admin; it is not represented as independent copyright verification by Maharashtra Tourist Places.

## Admin moderation and suspension

The Advertising control center filters by lifecycle and advertiser type and can search advertiser/campaign names. Review shows ownership type, creative, copy, target, placement, schedule, payment, rights attestation, analytics, and operational refund-review state.

Admin can approve, request changes, reject, or pause. Reasons are mandatory for request-changes, rejection, pause, and advertiser suspension. Suspension prevents new External campaigns, payment, submission, and edits; active/scheduled campaigns are paused without deleting financial or analytics history. Reactivation does not automatically resume paused campaigns.

Meaningful profile, campaign, target, creative, submission, moderation, and suspension actions use the immutable audit log. Existing notification events are reused for payment received, approval, changes requested, rejection, and pause. Notification delivery failure does not govern campaign or payment state. No production Email/SMS/WhatsApp provider was enabled.

## Delivery, rotation, and analytics

Public selection revalidates lifecycle, time window, paid payment, owner eligibility, creative presence, and placement/destination scope on the server. Draft, unpaid, pending-review, needs-changes, rejected, paused, expired, cancelled, or suspended-owner campaigns are not returned.

Every item is visibly labelled `Sponsored`. Multiple eligible items use the configured rotation interval; one item does not rotate. The browser records an impression when an item is displayed rather than when the API merely returns it. Impression/click deduplication uses a keyed visitor fingerprint and time bucket. Analytics expose impressions, clicks, and the inputs needed for CTR; they are lightweight anti-inflation measures, not a fraud-proof attribution platform. No conversion pixel, sales attribution, or invasive tracking exists.

## Privacy, indexing, and operations

`/advertise` is a public, indexable explanation and entry point. `/advertiser` is `noindex`, requires a Customer session, and exposes only that profile, its campaigns, payments, and analytics. Public ad payloads contain only approved customer-facing information; emails, phones, payment references, review notes, and audit history remain private.

Operational moderation procedure:

1. Confirm payment independently from review.
2. Inspect advertiser identity, rights attestation, creative, copy, approved placement, schedule, and External destination.
3. Approve only a paid, valid submission from an active owner; otherwise request changes or reject with a reason.
4. For a paid rejection, resolve the explicit refund-policy review outside campaign approval.
5. Pause a running campaign or suspend an External advertiser with a recorded reason when governance requires it.
6. Never edit payment evidence to force activation.

An External business starts at `/advertise`, signs in or registers a normal Customer account, creates its business profile, creates a campaign using an available configured plan, uploads an authorized creative, completes the existing checkout, and submits the paid campaign for Maharashtra Tourist Places review.

## Deployment notes and limitations

- Configure `MEDIA_BASE_URL` to the public HTTPS backend/media origin so public assets and controlled click links are correct.
- Advertising creatives currently use the durable public-media filesystem boundary. Multi-instance production deployment should point this boundary at shared object storage/CDN before horizontal scaling.
- DNS hostnames are syntactically screened and IP literals are classified. If server-side URL fetching is added later, it must perform DNS resolution and connection-time private-network enforcement to prevent DNS rebinding; the current system does not fetch advertiser URLs.
- Paused duration is not extended automatically. Compensation policy remains intentionally undefined.
- Advertising refund policy remains an explicit business decision.
