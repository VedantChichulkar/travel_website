# Curated Place data

Maharashtra Tourist Places' production Place content is a reviewed dataset, not a schema migration and not an application-startup seed.

```text
authoritative source review
  -> backend/app/data/places/
  -> complete preflight validation
  -> idempotent upsert
  -> canonical Place rows
```

## Dataset layout

- `types.py` defines the immutable record and provenance structures.
- `caves.py`, `forts.py`, and `sacred_spiritual.py` contain the first controlled batch.
- `nature_hills.py`, `wildlife_forests.py`, and `beaches_coast.py` contain the second controlled batch.
- `__init__.py` publishes `CURATED_PLACES_V1`, the reviewed dataset applied by the operator command.
- `app/services/curated_place_seed.py` owns validation, reference resolution, updates, and reporting.
- `scripts/seed_curated_places.py` is the intentional execution entry point.

The dataset records source provenance internally because provenance is editorial review information rather than customer-facing Place content. The current product does not need source fields in its public schema, and a schema extension solely for an internal citation was not justified. Each record must carry an authoritative source name, HTTP(S) URL, and last-verification date.

## Source and writing rules

Prefer, in order: the institution responsible for the site, UNESCO for World Heritage status, the Archaeological Survey of India, Maharashtra Tourism or another government authority, and an official religious institution. Do not use Wikipedia, affiliate pages, travel blogs, search snippets, or model memory as production authority.

Descriptions must paraphrase a small set of durable, verified facts. Keep them factual, neutral, concise, and respectful. Do not copy source passages or add superlatives. UNESCO wording is allowed only when the record cites the official UNESCO World Heritage property.

Never include volatile operating information such as admission prices, hours, closures, phone numbers, parking charges, queues, or temporary restrictions. Do not add coordinates without a separate verified geospatial workflow.

## Second-batch boundaries

The second batch adds nature and hill landscapes, protected wildlife areas, and Konkan beaches. A town-scale hill or coastal record is acceptable only when an authoritative tourism or government source treats it as a visitor place and no canonical production Destination represents the same concept. Prefer a specific plateau, ghat, lake, protected area, or beach when that gives the user a clearer Place identity. Re-run the duplicate audit whenever Destination data is introduced; a future canonical Destination may require the corresponding Place decision to be revisited.

Protected-area names must use the designation supported by the Maharashtra Forest Department, the National Tiger Conservation Authority, or the responsible district authority. National Park, Tiger Reserve, Wildlife Sanctuary, and Conservation Reserve are not interchangeable. Wildlife copy must describe habitats without promising sightings.

Place remains a discovery/content domain. Safari remains the managed availability and booking domain. A wildlife Place may surface an existing Safari only through an exact canonical Destination relationship. The curated Place dataset never creates Safari inventory, availability, gates, prices, or booking state. The production database had no Destination or Safari records when this batch was reviewed, so all second-batch Places deliberately use district fallback and expose no Safari link.

Coastal classification describes the Place itself, not merely its district. Existing sea forts can receive `beaches-coast` when their maritime setting is intrinsic; do not create a duplicate beach or fort record to populate another Interest. Ganpatipule is represented once as a combined beach-and-temple Place because its official district description treats both as defining features.

Every second-batch Place currently leaves `image_url` unset and uses the branded fallback. The centralized Nature, Wildlife, and Coast category heroes were reviewed and retained. Add Place-specific photography only after identity and usage rights are verified.

### Intentionally deferred candidates

- Bor Tiger Reserve was not added because the authoritative NTCA profile identifies both Nagpur and Wardha districts, while the current Place model requires one canonical district.
- Nagzira Wildlife Sanctuary was not added because the Gondia district authority explicitly locates it between Gondia and Bhandara districts.
- No Place-to-Safari link was fabricated: the production Safari catalogue and production Destination table were both empty during review.

## Adding or correcting a Place

1. Select the appropriate group module under `backend/app/data/places/`.
2. Confirm the Place's canonical district slug against `app/data/maharashtra.py`.
3. Supply a destination slug only when that exact canonical Destination already exists in the same district. District-only records are valid.
4. Use only slugs already present in `app/data/interests.py`.
5. Use an existing `SpiritualTradition` enum value or leave it unset. The classification describes the Place's actual religious heritage, not its visitors.
6. Add concise `short_description` and `description` text supported by the recorded source.
7. Record every source and the date it was last reviewed.
8. Add a Place-specific local image only when its identity and usage rights are known. Otherwise leave `image_url` unset so the customer UI uses its neutral branded fallback.
9. Run the focused tests and a dry run before committing the update.

The canonical slug is generated with Maharashtra Tourist Places' shared `slugify` implementation. Do not hand-build a second slug algorithm. When a later naming correction must preserve an already-published URL, set the record's optional `slug` to that existing canonical value; validation still normalizes it through the shared slug rules. The identity used by the seeder is this stable slug within the resolved district.

## Validation and ownership

The complete batch is validated before any Place writes. Validation rejects missing names or descriptions, unknown districts or destinations, destination/district mismatches, unknown or duplicate Interests, invalid traditions, duplicate canonical identities, invalid visibility values, bad display order, and missing or malformed provenance.

The curated dataset owns:

- name;
- district and optional destination relationships;
- short and full descriptions;
- image URL;
- spiritual tradition;
- active and featured state;
- display order;
- Interest classifications.

The seeder preserves the existing row ID, canonical slug, and creation timestamp. It does not modify other domains or create Districts, Destinations, Interests, Hotels, or Safaris.

## Running the seeder

From `backend`:

```powershell
.\venv\Scripts\python.exe scripts\seed_curated_places.py --dry-run
.\venv\Scripts\python.exe scripts\seed_curated_places.py
```

The command reports created, updated, unchanged, and failed counts plus totals grouped by Interest, District, and spiritual tradition. A validation failure exits non-zero and rolls back. Repeating a committed run with an unchanged dataset produces no duplicates and reports every managed row as unchanged.

## Review workflow

For every future batch, review source availability, geography, naming, Interest classification, tradition, and imagery in code review. Run the seed test suite, then run the command twice against the target environment and confirm the second report contains only unchanged records. Review customer pages and unified search after applying the data.
