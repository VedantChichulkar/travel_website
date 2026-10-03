# Repository migration map

Inspected 3 October 2026. Existing capabilities are described here for later migration decisions. No models, application code, seed data or database records were changed.

## Identity and hierarchy

| Layer | Existing implementation | Migration decision |
| --- | --- | --- |
| District | `backend/app/models/destination.py`, `backend/app/data/maharashtra.py` | Reuse 36 canonical identities. Old `chhatrapati-sambhaji-nagar` maps to `chhatrapati-sambhajinagar`. Mumbai requires City/Suburban evidence. |
| Destination | `Destination` in `destination.py` | Required district FK; names/slugs unique within district. A meaningful town/village/planning area may be a Destination. No Destination nesting. |
| Place | `backend/app/models/place.py` | Required district FK; optional `destination_id`. Parent must belong to the same district. |
| Interest | `backend/app/data/interests.py`, `place_interests` | Reuse nine records and existing many-to-many assignments. No category import or new taxonomy. |
| DiscoveryStory | `backend/app/models/discovery.py` | Editorial traditions/food, rather than visitable POIs. Multiple Districts, Destinations and related Places supported. |

Canonical frontend routes already exist:

- `/destinations/{districtSlug}`: District.
- `/destinations/{districtSlug}/{destinationSlug}`: Destination. Some frontend component/service names still say `PlaceDetail`/`getPlace` here; they represent Destination data.
- `/places/{districtSlug}/{placeSlug}`: actual Place.
- `/explore/{interestSlug}`: Interest discovery, optionally filtered by district.
- `/discover/{storySlug}`: DiscoveryStory.

Backend GET `/destinations/{districtSlug}/places` lists Destinations for compatibility. GET `/places` lists actual Places. Do not misclassify the former as Place inventory.

## Content and FAQs

Destination has `short_summary` (500 characters), `description` (Admin input up to 20,000), relational FAQs and hero/gallery media. It has no separate visitor/railway/airport columns. Reviewed Destination logistics can fit overview text or FAQs without changing schema.

Place has `short_description` (500), `description` (Admin input up to 20,000), `address` (500), `opening_hours`, `entry_fee_info`, `recommended_visit_duration` (120), `best_time_to_visit` (300), `getting_there`, `nearest_railway_station` (300), `nearest_airport` (300), `visitor_info_source`, `visitor_info_source_url`, and nullable `visitor_info_verified_at`.

CSV source passages are evidence, not ready-to-submit payloads. Whole old railway/airport FAQ answers must be condensed and verified to fit the actual fields. Never set `visitor_info_verified_at` to the crawl date.

`backend/app/models/discovery_content.py` contains separate DestinationFAQ/PlaceFAQ tables: parent FK, question, answer, display_order, is_active. Admin inputs allow up to 50 pairs, question 500 characters and answer 10,000. Public responses omit empty fields and inactive FAQs. No new FAQ schema is needed.

## Media and provenance

`PublicMediaAsset` (`backend/app/models/public_media.py`) records entity identity, opaque storage key/public URL, format, size, dimensions, alt text, specificity, creator/owner, source, usage basis, attribution, rights verification date, retirement and replacement history.

DestinationMedia and PlaceMedia attach an entity-owned asset as HERO or ordered GALLERY. Cross-entity assignment is rejected. Old thumbnail reuse identifies a likely subject; it does not make a Place photo part of a Destination gallery. Retain existing hero/history unless an explicit replacement is reviewed.

The existing pipeline (`media_storage.py`, Admin Discovery media routes) accepts JPEG/PNG/WebP up to 8 MB, verifies signatures/decode integrity and a 640×360 minimum, applies EXIF orientation, strips metadata, bounds to 2400 pixels and produces WebP. Page-declared dimensions do not prove that a file will pass these checks. Later approved retrieval must use this pipeline with rights evidence, never hotlink old images.

The inspected Admin upload API accepts DESTINATION or PLACE. DiscoveryStory currently has `image_url`; normalized Story gallery uploads are not exposed by these endpoints. No Story media migration or architecture extension is proposed.

## Admin ownership and publication

`backend/app/api/v1/admin_discovery.py`, `admin_discovery_service.py` and `admin/src/app/discovery/` provide Destination/Place drafts, edits, previews, publishing, FAQs and public media. Creation generates district-scoped slugs server-side; renaming retains the slug. Updates/media changes use `expected_version` and are audited. Linked Places cannot be published under an unpublished Destination.

`content_source` distinguishes CURATED/ADMIN. Editing curated content sets `admin_overridden`. Later enrichment must respect Admin edits and optimistic versions. Before CREATE, inspect all lifecycle states through the existing authenticated Admin workflow. This audit used only public GETs, with no authentication attempts.

## Curated data and collision baseline

`backend/app/data/places/` contains 49 curated records. `curated_place_seed.py` validates the whole batch, resolves canonical references, upserts by district + slug, and skips ADMIN/admin-overridden records. It preserves the existing controlled seed workflow. `backend/app/data/discovery_stories/` contains 10 Stories with provenance and its own operator-run seeder. Neither seeder nor any migration was executed.

The local public snapshot contains 36 Districts, nine Interests, 49 Places and 10 Stories. All 36 district Destination-list endpoints returned successfully with zero published Destinations. This is a local-public observation, not a production export. Hidden drafts, unpublished Admin content and production records are not covered. Documentation describing how to add a Place to Umred proves capability, not an existing Umred row.

Evidence: `evidence/repository-canonical-entities.json` and `evidence/local-public-discovery-snapshot.json`. Source-only identities were extracted with Python AST, without importing application modules or connecting to a database.
