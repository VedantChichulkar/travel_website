# Travel Platform Roadmap

This roadmap records the state found in the repository so implementation work can proceed without treating empty placeholder files as completed features.

## Phase 0 — Project foundation

- [x] Create FastAPI backend structure.
- [x] Configure SQLAlchemy, PyMySQL, and Alembic.
- [x] Add environment template and pinned Python dependencies.
- [x] Create customer and admin Next.js applications.
- [x] Configure Antigravity/Python tooling to use the backend virtual environment.
- [x] Document local setup and verification commands.

## Phase 1 — Backend domain and authentication

- [ ] Finalize the database design in `docs/database-design.md`.
- [ ] Implement user models and Alembic migrations.
- [ ] Implement password hashing, JWT access/refresh tokens, and role permissions.
- [ ] Implement authentication and user API routes.
- [ ] Add unit and API tests, including database-health behavior.

## Phase 2 — Booking platform

- [ ] Define hotel, room, availability, pricing, booking, payment, and cancellation models.
- [ ] Implement search and availability APIs.
- [ ] Implement booking lifecycle and payment integration.
- [ ] Connect the customer frontend to versioned APIs.

## Phase 3 — Operations

- [ ] Build admin workflows and authorization.
- [ ] Build the hotel-partner application.
- [ ] Add observability, CI checks, deployment configuration, backups, and security review.

Work should proceed in phase order. The next implementation milestone is the Phase 1 database design; schema-dependent backend code should not be guessed before that design is approved.
