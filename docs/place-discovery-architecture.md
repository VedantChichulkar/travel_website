# Place discovery architecture

Public Place media status, provenance, fallback resolution, and the production photography queue are documented in [Discovery media and content-quality readiness](./discovery-media-readiness.md).

Culture, craft, festival and culinary concepts that are not visitable POIs belong to the separate reusable `DiscoveryStory` layer documented in `docs/discovery-story-architecture.md`. They must not be inserted as Places merely to populate an Interest. The one-District Place constraint remains intentional and was not redesigned for multi-district wildlife areas.

Maharashtra Tourist Places keeps its existing Maharashtra hierarchy and adds attractions as a separate content layer:

```text
District
├── Destination (optional parent for a Place)
│   └── Place
└── Place (when no meaningful child Destination exists)

Place ── many-to-many ── Interest
```

## Canonical routes

- Districts remain at `/destinations/{district-slug}`.
- Destinations remain at `/destinations/{district-slug}/{destination-slug}`.
- Places use `/places/{district-slug}/{place-slug}` because Place slugs are unique within a district, matching the existing scoped Destination convention.
- Interest discovery is reserved under `/explore/{interest-slug}` for the later frontend implementation. This prevents values such as `caves` or `forts` from being interpreted as district slugs by `/destinations/[districtSlug]`.

The existing API route `/destinations/{district-slug}/places` continues to return child Destinations for backward compatibility. Canonical Places are queried through `/places?district={district-slug}` and can additionally be filtered by destination, interest, or search term.

The existing `/destinations/search` contract remains district/destination-only by default. Clients that can handle canonical Place paths opt in with `include_places=true`; this lets unified discovery evolve without sending current destination-only navigation to frontend routes that are intentionally deferred.

## Domain boundaries

Places are public discovery content, not accommodations or bookable Safari inventory. Geography links allow a future Place page to find nearby Hotels or related Safaris without copying either domain into the Place model.

The nine stable Interest records are seeded during foundation bootstrap. Reviewed attraction content is maintained separately in the operator-run curated dataset described in [curated-place-data.md](curated-place-data.md); it is never inserted by a schema migration or destructively reseeded at application startup.

Nature, Wildlife, and Coast remain discovery classifications, while Safari inventory and booking remain separate. Wildlife cross-discovery is rendered only when a Place has an exact canonical Destination that also resolves existing public Safari products; district similarity alone is not sufficient.
