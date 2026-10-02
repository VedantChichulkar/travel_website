# MAHARASHTRA TOURIST PLACES Implementation Roadmap

This roadmap tracks the incremental development of the MAHARASHTRA TOURIST PLACES platform following the Master Blueprint.

---

## Foundation Milestone

- [x] Inspect existing repository structure, dependencies, and environment files.
- [x] Verify backend, database configuration, and Next.js frontend workspaces.
- [x] Document system architecture, security principles, and 27-entity database roadmap in [architecture.md](architecture.md).
- [x] Freeze foundational baseline.

---

## Entity 1 — Users (Completed & Verified)

- [x] Complete `users` model, schemas, repositories, and services with `UserRole` (`CUSTOMER`, `HOTEL_PARTNER`, `ADMIN`) and `UserStatus` (`ACTIVE`, `INACTIVE`, `SUSPENDED`).
- [x] Implement password hashing (bcrypt), JWT access/refresh tokens, and verification flags (`is_email_verified`, `is_phone_verified`, `last_login_at`).
- [x] Implement user authentication endpoints (`/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`).
- [x] Create Alembic migration `e7192f1b4520_enhance_users_entity.py`.
- [x] Verify test suite against `users` module (`test_users_entity.py` passing).

---

## Entity 2 — Hotels (Completed & Verified)

- [x] Complete `hotels` model with decoupled `HotelStatus` (`DRAFT`, `PENDING`, `ACTIVE`, `INACTIVE`, `SUSPENDED`) and `BookingGatewayStatus` (`ACTIVE`, `PAUSED`).
- [x] Implement Maharashtra structured location schema (including `district`, `city`, `state`, `country`, `postal_code`, coordinates).
- [x] Add composite indexes `ix_hotels_location` and `ix_hotels_booking_gateway`.
- [x] Implement admin booking gateway toggle endpoint (`PATCH /admin/hotels/{hotel_id}/booking-gateway`).
- [x] Update public search & repository availability filtering (`list_public_hotels` & `search_hotels`).
- [x] Create Alembic migration `c8230da46721_enhance_hotels_entity.py`.
- [x] Verify test suite against `hotels` module (`test_hotels_entity.py` passing).

---

## Entity 3 — Hotel Verifications (Next Step)

- [ ] Implement `hotel_verifications` model (business registration, GST, PAN, ownership documents, audit logs).
- [ ] Implement partner verification submission and admin review workflows.
- [ ] Enforce security and privacy boundaries on sensitive verification documents.

---

## Sequential Database & Domain Roadmap

| Sequence | Domain | Entities | Status |
| :--- | :--- | :--- | :--- |
| **01** | **Core** | `users` | **Completed** |
| **02** | **Core** | `hotels` | **Completed** |
| **03 - 04** | **Core** | `hotel_verifications`, `hotel_policies` | Next |
| **05 - 09** | **Inventory** | `room_types`, `physical_rooms`, `room_inventory`, `hotel_images`, `room_images` | Pending |
| **10 - 12** | **Booking** | `bookings`, `booking_guests`, `booking_policy_snapshots` | Pending |
| **13 - 15** | **Financial** | `payments`, `refunds`, `settlements` | Pending |
| **16 - 19** | **Stay Operations** | `check_ins`, `check_outs`, `no_shows`, `cancellations` | Pending |
| **20 - 22** | **Reviews** | `reviews`, `review_responses`, `review_challenges` | Pending |
| **23 - 25** | **Communication** | `conversations`, `messages`, `notifications` | Pending |
| **26 - 27** | **Governance** | `audit_logs`, `admin_actions` | Pending |
