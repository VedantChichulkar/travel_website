# MAHARASHTRA TOURIST PLACES Database Design & Schema Specification

This document defines the relational database architecture for the MAHARASHTRA TOURIST PLACES platform across all 27 planned entities, divided into 8 functional domains.

---

## Domain Breakdown & Entity Index

### 1. Core Domain
1. **`users`** — System users spanning Customers, Hotel Partners, and Maharashtra Tourist Places Administrators.
2. **`hotels`** — Hotel properties with profile details, contact info, ratings, and gateway status.
3. **`hotel_verifications`** — Business registration, GST, PAN, ownership proofs, and verification history.
4. **`hotel_policies`** — Hotel-specific rules, check-in/check-out timing, house rules, and default terms.

### 2. Inventory Domain
5. **`room_types`** — Commercial room categories (e.g. Deluxe, Executive Suite) with max occupancy and amenities.
6. **`physical_rooms`** — Optional individual physical room numbers and maintenance states.
7. **`room_inventory`** — Date-wise inventory counts, base rates, and availability flags.
8. **`hotel_images`** — Property gallery images, categories, display order, and alt metadata.
9. **`room_images`** — Room-type specific photos and display rankings.

### 3. Booking Domain
10. **`bookings`** — Core booking transactional records, reference codes, dates, price breakdowns, and states.
11. **`booking_guests`** — Primary guest and accompanying guest information with minimal required identification metadata.
12. **`booking_policy_snapshots`** — Immutable snapshot of the cancellation policy and terms active at confirmation.

### 4. Financial Domain
13. **`payments`** — Inbound customer transactions, gateways, transaction IDs, timestamps, and status.
14. **`refunds`** — Outbound customer refunds, calculated policy refund amounts, reasons, and tracking.
15. **`settlements`** — Periodic payout ledger entries and calculations for hotel partners after commission deduction.

### 5. Stay Operations Domain
16. **`check_ins`** — Guest arrival timestamps, assigned physical room (if applicable), and identity verification notes.
17. **`check_outs`** — Departure timestamps and final folio/clearance notes.
18. **`no_shows`** — Recorded guest no-show events and policy execution.
19. **`cancellations`** — Cancellation logs, timestamps, refund tier triggers (e.g., 24h-48h 50% tier), and initiating actor.

### 6. Reviews Domain
20. **`reviews`** — Verified guest ratings and textual reviews tied directly to completed bookings.
21. **`review_responses`** — Official hotel partner responses to guest reviews.
22. **`review_challenges`** — Hotel dispute requests on potentially fraudulent or policy-violating reviews.

### 7. Communication Domain
23. **`conversations`** — Communication channels between guest and hotel partner / admin for a booking.
24. **`messages`** — Individual auditable text messages within a conversation.
25. **`notifications`** — Multi-channel notification queue and history (email, SMS, in-app).

### 8. Governance Domain
26. **`audit_logs`** — System-wide immutable security, financial, and operational event trails.
27. **`admin_actions`** — Specific administrative overrides, manual refunds, and gateway changes.
