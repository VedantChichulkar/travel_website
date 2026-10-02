# MAHARASHTRA TOURIST PLACES Platform Architecture & Foundation Specification

## 1. System Overview

**MAHARASHTRA TOURIST PLACES** is a Maharashtra-focused travel and hotel booking platform operating on a **hybrid / intermediary booking model**:
- **Customers** discover destinations, hotels, and room types, placing bookings and completing payments directly through Maharashtra Tourist Places.
- **Hotel Partners** manage their property profiles, room types, optional physical room assignments, availability gateway, check-ins/check-outs, and operational records.
- **Maharashtra Tourist Places Administrators** oversee platform governance, hotel verification, booking gateway overrides, financial settlements, cancellations, refunds, disputes, reviews, and audit logs.

---

## 2. Core Architectural & Business Decisions (Source of Truth)

1. **Regional Focus**: Maharashtra tourism destinations and properties initially.
2. **Tri-Portal Actor Model**: Customers, Hotel Partners, and Maharashtra Tourist Places Administrators.
3. **Verification & Onboarding**: Hotels apply and must complete verification before receiving live bookings.
4. **Availability & Gateway Control**:
   - Hotel partner operational status (`DRAFT`, `PENDING`, `ACTIVE`, `INACTIVE`, `SUSPENDED`) and booking gateway state (`ACTIVE`, `PAUSED`) are decoupled.
   - Maharashtra Tourist Places administrators retain the authority to override hotel booking availability.
   - Pausing a hotel gateway does **not** cancel previously confirmed bookings.
5. **Inventory & Room Modeling**:
   - Commercial inventory is managed at the **Room Type** level.
   - Physical room tracking is **optional** for hotels and controlled by the hotel at check-in/assignment.
6. **Preservation of Terms**: Confirmed bookings retain snapshots of the applicable room data, price breakdown, and cancellation policy terms active at the time of booking.
7. **Financial & Settlement Separation**:
   - Customer payments flow through Maharashtra Tourist Places.
   - Customer payments, refunds, and hotel partner settlements are recorded as distinct, auditable ledger items.
   - Standard Cancellation Policy:
     - Between 24 hours and 48 hours from booking: **50% refund**.
     - After 48 hours from booking: **No refund (0%)**.
8. **Data Security & Governance**:
   - Secure and minimal handling of identity information (e.g., Aadhaar/ID metadata where legitimately required for guest verification).
   - Sensitive financial and administrative events are strictly audited.

---

## 3. Technology Stack & Boundaries

| Layer | Technology | Responsibilities |
| :--- | :--- | :--- |
| **Backend API** | FastAPI (Python 3.10+) | REST API endpoints, business rules, validation, security, and orchestration |
| **ORM & Migrations** | SQLAlchemy 2.0 + Alembic | Relational data models, database transactions, schema migration versioning |
| **Database** | MySQL (PyMySQL driver) | ACID relational data persistence with foreign keys, constraints, and indexes |
| **Customer App** | Next.js (TypeScript, React) | Public discovery, destination exploration, booking interface, customer profile |
| **Admin App** | Next.js (TypeScript, React) | Internal administration, partner verification, operational dashboards, financial controls |
| **Hotel Portal** | Next.js (TypeScript, React) | Property management, inventory gateway, guest check-in/out, partner settlements |

---

## 4. Database Entity Roadmap (Sequential Build)

The platform database architecture will be implemented incrementally in the following strict sequential order:

```
CORE
├── 1. users (IMPLEMENTED & VERIFIED)
├── 2. hotels (IMPLEMENTED & VERIFIED)
├── 3. hotel_verifications
└── 4. hotel_policies

INVENTORY
├── 5. room_types
├── 6. physical_rooms
├── 7. room_inventory
├── 8. hotel_images
└── 9. room_images

BOOKING
├── 10. bookings
├── 11. booking_guests
└── 12. booking_policy_snapshots

FINANCIAL
├── 13. payments
├── 14. refunds
└── 15. settlements

STAY OPERATIONS
├── 16. check_ins
├── 17. check_outs
├── 18. no_shows
└── 19. cancellations

REVIEWS
├── 20. reviews
├── 21. review_responses
└── 22. review_challenges

COMMUNICATION
├── 23. conversations
├── 24. messages
└── 25. notifications

GOVERNANCE
├── 26. audit_logs
└── 27. admin_actions
```

---

## 5. Entity Specifications

### Entity 1: `users`

#### Purpose
Represents platform-level user identity and account authentication across the three platform actors (Customers, Hotel Partners, Maharashtra Tourist Places Admins). Hotel properties, bookings, payments, reviews, and identity documents are strictly decoupled and handled by subsequent entities.

#### Schema & Fields
| Field | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | No | PK, Auto-Increment | Stable numerical primary key |
| `full_name` | `VARCHAR(100)` | No | Min length 2 | Normalized full name |
| `email` | `VARCHAR(255)` | No | UNIQUE, Index `ix_users_email` | Normalized lowercase email address |
| `phone` | `VARCHAR(16)` | No | UNIQUE | E.164 formatted telephone number |
| `password_hash` | `VARCHAR(255)` | No | Bcrypt hashed | Secure one-way password hash |
| `role` | `VARCHAR(20)` | No | Default: `'CUSTOMER'` | Platform actor role |
| `status` | `VARCHAR(20)` | No | Default: `'ACTIVE'` | Account lifecycle status |
| `is_active` | `BOOLEAN` | No | Default: `1` (True) | Active flag for fast boolean checks |
| `is_email_verified`| `BOOLEAN` | No | Default: `0` (False) | Explicit email verification state |
| `is_phone_verified`| `BOOLEAN` | No | Default: `0` (False) | Explicit phone verification state |
| `last_login_at` | `DATETIME` | Yes | Nullable | Timestamp of most recent successful login |
| `created_at` | `DATETIME` | No | Server Default: `NOW()` | Audit record creation timestamp |
| `updated_at` | `DATETIME` | No | Server Default: `NOW()`, onupdate | Audit record modification timestamp |

#### Role Values (`UserRole`)
- `CUSTOMER`: End-user customer booking accommodations in Maharashtra.
- `USER`: Backward-compatibility alias for `CUSTOMER`.
- `HOTEL_PARTNER`: Hotel owner/staff operating property profile and inventory.
- `ADMIN`: Maharashtra Tourist Places platform administrator with platform-wide oversight.

#### Account Status Values (`UserStatus`)
- `ACTIVE`: Normal operating state; permitted to authenticate and access authorized routes.
- `INACTIVE`: Soft-disabled account; authentication rejected.
- `SUSPENDED`: Administratively suspended account; authentication rejected.

---

### Entity 2: `hotels`

#### Purpose
Represents a property/business entity registered on Maharashtra Tourist Places across Maharashtra. It strictly encapsulates property-level information, geographic location, and operational platform state while remaining separated from user identity, verification documents, room types, inventory, and bookings.

#### Schema & Fields
| Field | Type | Nullable | Constraints & Defaults | Description |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | No | PK, Auto-Increment | Stable numerical primary key |
| `name` | `VARCHAR(150)` | No | Min length 2, trimmed | Property / business trade name |
| `slug` | `VARCHAR(180)` | No | UNIQUE, Index `ix_hotels_slug` | SEO-friendly URL identifier |
| `description` | `TEXT` | Yes | Max 10,000 chars | General property overview |
| `property_type` | `VARCHAR(50)` | No | Enum `PropertyType` | Category: `HOTEL`, `RESORT`, `VILLA`, `APARTMENT`, `HOSTEL`, `HOMESTAY` |
| `star_rating` | `DECIMAL(2,1)`| No | Default `0.0`, Range `0.0` - `5.0` | Official / standard property rating |
| `status` | `VARCHAR(20)` | No | Default `'DRAFT'`, Indexed | Hotel lifecycle state: `DRAFT`, `PENDING`, `ACTIVE`, `INACTIVE`, `SUSPENDED` |
| `booking_gateway_status` | `VARCHAR(20)` | No | Default `'ACTIVE'`, Indexed | Booking gateway state: `ACTIVE`, `PAUSED` |
| `address_line1` | `VARCHAR(255)` | No | Min length 2 | Street address / landmark |
| `address_line2` | `VARCHAR(255)` | Yes | Nullable | Secondary address line / suite |
| `city` | `VARCHAR(100)` | No | Indexed | City / town name (e.g. Pune, Mahabaleshwar) |
| `district` | `VARCHAR(100)` | Yes | Indexed | Maharashtra district (e.g. Satara, Raigad, Ratnagiri) |
| `state` | `VARCHAR(100)` | No | Default `'Maharashtra'`, Indexed | State name |
| `country` | `VARCHAR(100)` | No | Default `'India'` | Country name |
| `postal_code` | `VARCHAR(20)` | No | Validated | Pincode / Postal code |
| `latitude` | `DECIMAL(10,7)`| Yes | Range `-90.0` to `90.0` | GPS Latitude coordinates |
| `longitude` | `DECIMAL(10,7)`| Yes | Range `-180.0` to `180.0` | GPS Longitude coordinates |
| `contact_email` | `VARCHAR(255)` | Yes | Valid Email | Property inquiry/management email |
| `contact_phone` | `VARCHAR(16)` | Yes | E.164 format | Property operational phone number |
| `check_in_time` | `TIME` | No | Standard Time | Standard guest check-in time |
| `check_out_time`| `TIME` | No | Standard Time | Standard guest check-out time |
| `is_featured` | `BOOLEAN` | No | Default `0` (False) | Featured placement flag |
| `created_at` | `DATETIME` | No | Server Default: `NOW()` | Audit record creation timestamp |
| `updated_at` | `DATETIME` | No | Server Default: `NOW()`, onupdate | Audit record modification timestamp |

#### Hotel Status Values (`HotelStatus`)
- `DRAFT`: Initial draft property profile created by partner.
- `PENDING`: Awaiting Maharashtra Tourist Places verification (Entity 3).
- `ACTIVE`: Fully approved and active property on Maharashtra Tourist Places.
- `INACTIVE`: Partner-disabled or temporarily offloaded property.
- `SUSPENDED`: Administratively suspended due to policy or operational violations.

#### Booking Gateway Status (`BookingGatewayStatus`)
- `ACTIVE`: Gateway open; new customer bookings can be placed for active rooms.
- `PAUSED`: Gateway paused; new bookings cannot be placed, but existing confirmed bookings remain valid and unaffected.

#### Why Hotel Status and Booking Gateway Status Are Decoupled
1. **Administrative Availability Control**: Maharashtra Tourist Places or the hotel partner can pause incoming bookings during peak maintenance, local weather disruptions, or inventory audits without revoking the hotel's verified partner status.
2. **Preservation of Existing Bookings**: Pausing the booking gateway does not cancel or invalidate confirmed customer reservations.
3. **Multi-tier Governance**: A hotel can be `HotelStatus.ACTIVE` with `BookingGatewayStatus.PAUSED`, allowing partner portal operations, check-ins, and reporting to continue uninterrupted while blocking new public bookings.

#### Relationships to Future Entities (Planned)
- `users`: Partner/staff relationship mapping (many-to-many or membership mapping) permitting authorized partner users to manage property details.
- `hotel_verifications` (Entity 3): Business registration, GST, PAN, and verification documentation.
- `hotel_policies` (Entity 4): Property-specific cancellation, house rules, and check-in policies.
- `room_types` (Entity 5): Commercial room categories for inventory management.
- `hotel_images` (Entity 8): Gallery and promotional photo assets.
- `bookings` (Entity 10): Transactional reservations associated with the property.
- `settlements` (Entity 15): Financial payouts and commission tracking.

#### Indexes & Constraints
- **`PRIMARY KEY (id)`**: Fast clustered index for primary joins.
- **`ix_hotels_slug` (`slug`)**: Unique index ensuring fast routing by SEO-friendly property slug.
- **`ix_hotels_location` (`country`, `state`, `city`, `district`)**: Multi-column index supporting geographic searches across Maharashtra.
- **`ix_hotels_booking_gateway` (`status`, `booking_gateway_status`)**: Composite index ensuring $O(1)$ filtering for customer-facing availability queries.
- **Check Constraints**: Latitude (`[-90, 90]`), Longitude (`[-180, 180]`), Star Rating (`[0, 5]`).

---

## 6. Environment Configuration & Tooling

- Backend reads `.env` located at `backend/.env` (configured via `pydantic-settings`).
- Frontend & Admin read `.env.local` pointing `NEXT_PUBLIC_API_URL` to backend API prefix (`http://localhost:8000/api/v1`).
- Migrations executed via `alembic upgrade head`.
- Tests run using standard Python `unittest`: `python -m unittest tests.test_hotels_entity tests.test_users_entity`.
