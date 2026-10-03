# Discovery story architecture

Public Story media status, provenance, fallback resolution, and replacement workflow are documented in [Discovery media and content-quality readiness](./discovery-media-readiness.md).

## Why this layer exists

Before this change, Maharashtra Tourist Places had a database-backed Place and Interest system, while `/experiences` used frontend-only destination cards plus hard-coded culture and food snippets. There was no backend Experience, Story, Article, Guide, Culture or generic content model. The static snippets could not carry provenance, support idempotent corrections, model statewide or multi-district context, provide canonical detail pages, or participate safely in public search.

`DiscoveryStory` is the smallest reusable editorial entity that closes that gap. It represents source-reviewed cultural, craft, festival and culinary discovery. It is not a Place, Destination, Hotel, Safari product, restaurant listing or booking inventory.

## Domain boundaries

- `Place` remains a geographically visitable POI with one required District.
- `DiscoveryStory` may be statewide, linked to one District, or linked to multiple Districts.
- A story may optionally relate to Destinations and Places when the relationship is direct and verified.
- Stories reuse the existing Interest taxonomy through `discovery_story_interests`; there is no duplicate editorial taxonomy.
- The known multi-district Place limitation exposed by Bor and Nagzira remains unchanged.

## Data flow

Reviewed Python records in `backend/app/data/discovery_stories/` contain customer copy, taxonomy, optional geography, optional related Places and internal source provenance. The operator-run `seed_curated_discovery_stories.py` command validates the complete batch before writes and then performs an idempotent slug-based upsert. Alembic contains schema only; stories are never inserted from a migration or automatically at application startup.

Curated-managed fields are title, descriptions, image reference, visibility, featured/order fields, Interests and optional geographic/Place relationships. Repeated runs preserve database identity and `created_at`. `--dry-run` calculates the same change report and rolls back.

## Public surfaces

- `GET /api/v1/discovery-stories` supports `interest`, `district`, `q` and `limit`.
- `GET /api/v1/discovery-stories/{slug}` returns active story details and active related records.
- `/explore/[interestSlug]` can render Places and stories together. Culture and Food lead with stories; geographic interests continue to lead with Places.
- `/discover/[storySlug]` is the single reusable editorial detail route.
- Unified destination search includes stories only when `include_stories=true`, preserving the older default contract. The customer search opts in and labels them “Story”.

Internal source URLs and review dates are intentionally absent from public responses. They are editorial audit metadata rather than customer-facing citation infrastructure.

## Public discovery entry points

The redundant `/experiences` page has been removed and permanently redirects to `/destinations`. Homepage discovery cards use the existing nine Interests and canonical `/explore/{interestSlug}` routes. Destination culture links use those same Interest guides with a district filter. Culture and Food guides retain editorial lists and canonical `/discover/{storySlug}` details; Places, Discovery Stories, and Admin Discovery management are preserved.

## Media and SEO

Stories accept a centralized `image_url`, but the initial controlled batch deliberately has no unverified photography. Cards and detail pages use clearly labelled generic Interest artwork as fallback. Detail metadata uses the real title and short description, a canonical `/discover/{slug}` URL, and either specific media or the Interest fallback. Inactive stories return 404 and are therefore not indexable as valid content.

## Initial controlled batch

Culture: Pandharpur Wari; Lavani Performance Tradition; Warli Art and Community Storytelling; Paithani Weaving; Ganeshotsav Traditions Across Maharashtra.

Food: Varhadi Cuisine of Vidarbha; Saoji Cuisine of Nagpur; Kolhapuri Cuisine; Malvani Cuisine of the Konkan Coast; Puran Poli and Modak at Festival Tables.

Standalone Misal, generic Maharashtrian thali, restaurant records, menus, recipes and weakly sourced origin claims were deliberately omitted.
