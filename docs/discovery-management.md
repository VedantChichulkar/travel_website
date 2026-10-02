# Discovery management

## Purpose and boundaries

Maharashtra Tourist Places Control Center manages customer-facing Destinations, Places, rich editorial content, publication state, FAQs, and public discovery media. It reuses the canonical 36 Maharashtra districts, nine Interests, 49 curated Places, and ten Discovery Stories. It is not a generic CMS. It does not create districts or Interests, manage private verification documents, or change hotel finance, payout, advertising, or safari workflows.

## Rich content and automatic Place discovery

A Destination retains `description` as its detailed overview and adds an optional `short_summary`. A Place retains `short_description` and `description`, then adds nullable visitor fields (address, opening-hours text, entry-fee text, recommended duration, and best-time guidance) and nullable travel fields (general guidance, nearest railway information, and nearest airport information). Empty values are omitted publicly; Maharashtra Tourist Places never synthesizes “N/A”.

Opening hours, fees, and access details can become stale, so a Place may record a source, absolute HTTP(S) source URL, and `visitor_info_verified_at`. The public page shows the verification date and advises travellers to confirm current details. No automatic external verification or currency claim is made.

`Place.destination_id` is the sole source of truth for a Destination's Places. The Destination detail query eager-loads and returns only published Places assigned to it. Draft, unpublished, other-Destination, and district-only Places are excluded. Publishing or unpublishing an assigned Place updates the Destination page immediately without maintaining a second list or deploying the frontend.

Destination and Place FAQs use separate relational tables with proper owner foreign keys, cascading lifecycle, `question`, `answer`, `display_order`, and `is_active`. They save atomically with the parent under the same optimistic version check. Public responses return active records only in deterministic order. Customer pages use semantic disclosure elements and intentionally do not emit FAQ structured data.

## Lifecycle

Every admin-created Destination or Place begins as `DRAFT` (`is_active=false`, no `published_at`). An administrator can preview it only inside the authenticated Control Center. Publishing sets `is_active=true` and records the first `published_at`; unpublishing retains that timestamp and produces `UNPUBLISHED`. Existing public repositories continue to require active records, active districts, and—when linked—an active destination. Draft and unpublished content therefore cannot leak through detail, list, search, Explore, or destination pages.

Slugs are generated server-side at creation and scoped to the district. Editing a name never changes the slug. An attempted district move that would collide with the stable slug returns `409 Conflict`.

Each write includes an `expected_version`. A stale editor receives `409 Conflict` and must reload. FAQ edits share the parent save transaction; media role/order/alt-text changes and retirement also check the entity version. Create, edit, publish, unpublish, upload, replacement, assignment, and retirement actions are recorded in the immutable admin audit log.

## Curated and admin ownership

`content_source` distinguishes `CURATED` from `ADMIN`. Editing, publishing, unpublishing, or attaching media to a curated record sets `admin_overridden=true`. The curated Place seeder skips admin-owned records and curated records with an administrator override, so routine idempotent seed runs cannot erase operational edits. Admin-created records are never treated as part of the curated dataset.

## Validation and relationships

- Districts and Interests must be active canonical records.
- A linked Destination must belong to the selected district.
- Duplicate Interest assignments are rejected.
- Spiritual tradition uses the existing controlled enum and is accepted only when `sacred-spiritual` is selected.
- Publishing requires a name, full description, and—for Places—a short description plus at least one Interest.
- A Place linked to an unpublished Destination cannot be published.
- Unpublishing a Destination reports linked public Places, Hotels, and Stories before/after the audited action; it never deletes those records.

## Public media

`destination_media` and `place_media` provide normalized entity-to-asset relationships with `HERO` or `GALLERY` role and deterministic display order. They reuse `PublicMediaAsset` and its rights registry; cross-entity assignment is rejected. The selected hero is mirrored through the legacy primary-media fields for backward compatibility. Replacing a hero retires the old hero, while adding gallery media leaves it intact. Removing media retires rather than hard-deletes the asset.

Public discovery images use `public_media_assets` and `MEDIA_ROOT`; private documents continue to use the isolated private-document provider and are never served from this path. Uploads accept JPEG, PNG, or WebP up to 8 MB, verify signatures and decode integrity, reject decompression bombs, require at least 640×360 pixels, apply EXIF orientation, strip metadata, resize to a 2400-pixel bound, and encode an optimized WebP under an opaque key.

The administrator must record creator/owner, source, usage basis, verification date, alt text, and specificity. `SPECIFIC` also requires confirmation that the image depicts the exact entity. Replacing an image atomically points the entity at the new asset and retires the previous asset while preserving provenance and replacement history. Retired files are intentionally retained for audit/recovery; a future reviewed cleanup job may delete unreferenced files after the required retention period.

The customer resolver prefers an active rights-recorded entity image, then the existing deterministic Interest fallback, then the global fallback. Media storage is local/provider-neutral at the service boundary and can move behind a CDN or object-store public origin through `MEDIA_BASE_URL` without changing entity URLs.

## Customer page structure

Destination pages render a hero, optional summary, overview, populated gallery, automatic image-led Place cards, existing Find Stays behavior, qualifying existing Safari discovery, and active FAQs. Place pages render hierarchy-aware breadcrumbs, hero, descriptions, populated gallery, only populated visitor/travel rows, existing Find Stays behavior, active FAQs, and a bounded related-Places list. Related Places prefer the same Destination; district-only Places fall back to the same District. Eager loading prevents per-card media/interest/FAQ queries.

Find Stays continues to use exact canonical Destination/District geography; no fuzzy Hotel link was added. Wildlife enrichment does not create Safari availability. The Safari UI remains governed by the existing real inventory query.

## Operations

1. Install backend dependencies including `requirements.public-media.txt`.
2. Run `python -m alembic upgrade head` (rich-content revision `c3d8e1f5a7b2`).
3. Configure `MEDIA_ROOT`, an HTTPS `MEDIA_BASE_URL` in production, and durable backup/retention for public media.
4. Use Control Center → Discovery → Destinations / Places / Public media.
5. Run backend tests, both portal lint/type checks/builds, and browser QA before deployment.

The migration backfills existing active Destinations and Places as published curated content without changing their names or slugs.

## Administrator workflows

To add a Destination, open **Discovery → Destinations → New destination**, select one canonical district, enter reviewed copy, and create the draft. Review the secure preview, optionally attach rights-recorded public media, then publish with an audit reason. It immediately enters the existing district route, destination search, canonical detail route, and hotel location filter. It never creates hotel or safari inventory.

To add a Place, open **Discovery → Places → New place**, select its required district, optionally select a Destination from that district, choose one or more canonical Interests, add reviewed descriptions, and create the draft. Spiritual tradition is shown only when Sacred & Spiritual is selected. After preview and publication, the existing Place detail, district/Interest filters, unified search, Find Stays logic, canonical metadata, and media fallback resolver pick it up without a seeder or deployment.

Normal administrators cannot hard-delete discovery records. Unpublish instead; the record remains editable in Control Center and disappears from public detail, list, Explore, and search queries. Media replacement creates a new opaque asset, preserves the previous rights record as retired, and leaves physical retired-file cleanup to a future retention-aware maintenance job.

### Adding a Place to Umred

Open **Discovery → Places → New place**, choose Nagpur as District and Umred as Destination, then add the required descriptions and Interests. Fill only applicable visitor/travel fields, add source and verification details for volatile facts, optionally add ordered FAQs, and create the draft. Upload a rights-recorded hero and any gallery images, review, and publish. The Place then appears automatically in Umred's “Places to visit” section because its canonical `destination_id` points to Umred. No code or manual Destination list is involved.

The curated seeder continues to manage only its documented legacy fields. New nullable enrichment, FAQs, galleries, rights metadata, and Admin content are not removed or overwritten by reruns. Existing curated Places remain valid without enrichment.
