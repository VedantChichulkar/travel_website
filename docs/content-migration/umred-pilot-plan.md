# Umred proposed pilot plan

Inventory only — 3 October 2026. Do not execute this plan yet.

## Evidence-supported hierarchy

The [old Umred listing](https://maharashtratouristplaces.in/nagpur/umred/) names four attractions. Each detail page describes an Umred locality in Nagpur district. The listing says tehsil: clarify whether the target Destination represents Umred town or its wider planning area before establishing relationships.

```text
Maharashtra
└── Nagpur (existing canonical District: nagpur)
    └── Umred (proposed Destination: umred)
        ├── Gandhi Sagar Lake, Umred [C031; identity/boundary review]
        ├── Gandhi Sagar Park, Umred [C032; identity/boundary review]
        ├── Shree Gajanan Maharaj Devasthan WCL, Umred [C033]
        └── Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth [C034]
```

Lake/Park remain provisional. Separate URLs, addresses and galleries support two candidates but do not settle whether they are separate managed POIs or a lake-and-park complex. Confirm with owner/local authority; neither merge nor creation is authorized. Gaotalav/Gaon Talav are lake aliases. Onsite Shiva shrines mentioned on lake/WCL pages remain contextual features, not extra Place records.

## Collisions and prerequisites

Nagpur exists in the canonical registry. Local public lists contain no published Umred Destination and no matching Place among the 49 curated/public Places or ten Stories. This excludes draft/unpublished/Admin/production state. Later, check every lifecycle state, spelling alias and relationship through existing Admin Discovery. Do not use the CSV as a seeder input.

Kawrapeth's temple is distinct from the curated Vitthal-Rukmini Temple in Pandharpur, Solapur. WCL Umred is distinct from Shri Gajanan Maharaj Sansthan in Trimbakeshwar, Nashik. Keep Umred context in Gandhi Sagar Lake naming to distinguish similarly named Nagpur-city attractions. If an Admin record exists, retain its slug, content and media and prepare additive version-checked changes.

## Destination content and media

C030 proposes `/destinations/nagpur/umred`. The old body is a four-card listing with no substantive Destination About text or FAQs. Metadata's broad sanctuary wording establishes neither a protected-area record nor a Safari relationship. A factual source-reviewed overview and short summary must be supplied later. Do not fabricate town-wide opening hours or fees from attraction details.

`Umred.webp` is the old primary-image family, declared 1280×960 on its source page, and a DESTINATION_HERO candidate. It also appears as resized Nagpur-listing thumbnails. Confirm actual subject, creator and rights. No dedicated Destination gallery was found. Do not fill one with Place thumbnails just because the listing displays them. Keep fallback media until appropriate approved files exist.

## Place content and routes

| Record | Proposed route | Interests | Content decision |
| --- | --- | --- | --- |
| C031 | `/places/nagpur/gandhi-sagar-lake-umred` | nature-hills | Review lake copy/shrine claims and lake/park boundary. |
| C032 | `/places/nagpur/gandhi-sagar-park-umred` | nature-hills | Verify park boundary, amenities and access. |
| C033 | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` | sacred-spiritual; nature-hills | Temple and existing picnic setting as one POI; check WCL permission. |
| C034 | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` | sacred-spiritual | Specific Kawrapeth institution; do not merge with Pandharpur. |

These slugs are suggestions normalized like existing `slugify`; final server creation depends on a full collision check. Each Place needs Nagpur, an optional reviewed Umred relationship, factual short/full descriptions and existing Interest IDs. HINDU tradition may be assigned only after identity review; no enum assignment was made here.

Four full source About texts and 31 FAQ pairs are captured. Review superlatives, promises, religious claims and repetitive wording before publishing. Retain original source references for editorial audit.

## Visitor information — old claims only

Every value below is OLD_SITE_UNVERIFIED. Retrieval on 3 October 2026 does not verify current operations.

| Record / Place | Old opening claim | Old entry claim | Old address |
| --- | --- | --- | --- |
| C031 / Gandhi Sagar Lake, Umred | Open daily | Is there any entry fee to visit the lake? No, generally there is no entry fee to visit Gandhi Sagar Lake. It is a public place open for all. | V849+XRG, Pavandham Rd, Kawarapeth, Teachers Colony, Umred Rural, Maharashtra 441203 |
| C032 / Gandhi Sagar Park, Umred | Open daily 5.00 Am to 8.00 pm |  | V85C+269, Budhwari peth, Umred, Maharashtra 441203 |
| C033 / Shree Gajanan Maharaj Devasthan WCL, Umred | Open daily : 5 am to 7 pm | Is there any entry fee? Usually no entry fee there. It’s a temple area, but rules can vary slightly depending on WCL management. | V872+8JQ, MSH 9, Gangapur, Maharashtra 441203 |
| C034 / Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | Open daily 5.00 Am to 8.00 pm | Is there any entry fee to visit the temple? No, entry to the temple is free for all devotees. | V857+HV, Kawrapeth, Gangapur Umred Rural, Maharashtra 441203 |

Lake: old FAQs name Nagpur Junction and Dr. Babasaheb Ambedkar International Airport, roughly 45–50 km road travel from Nagpur, and buses/travels via BaidyaNath bus stop to Kalamna Square. Verify station/airport suitability, actual routes, distances and last-mile instructions. “Open daily” gives no precise hours. A one-day-trip statement is not a recommended visit duration.

Park: old source suggests 1–2 hours, morning/evening and October–February. These are planning suggestions, not verified rules. No entry-fee, railway or airport details were found on this page; leave them blank until sourced.

WCL temple: old source claims 5am–7pm, usually free entry with WCL caveats, ₹50–₹80 bus fare, Ganeshpeth/Baidyanath departures, Gangapur chowk/Kawrapeth walking access, and a 40–45 km/45-minute-to-one-hour trip. Verify with transport operators and temple/WCL management. Do not reuse lake-specific railway/airport answers. Check public access, picnic permission, photography, closures and last-mile safety.

Kawrapeth temple: old source claims 5am–8pm, free entry, road access through Umred, 40–50 km from Nagpur and a ten-minute walk from the lake. Confirm the institution/address, access, photography rules and geography. No dedicated railway/airport/visit-duration information was found; do not synthesize it.

Only later verified fields may receive `visitor_info_source`, source URL and `visitor_info_verified_at`. Nearest-station/airport fields are concise 300-character strings; do not submit whole archived FAQ answers without review.

## FAQ handling

There are no Umred Destination FAQ pairs to migrate. A new town-level FAQ set would need separately reviewed information. Do not duplicate attraction FAQs indiscriminately across entities.

### Gandhi Sagar Lake, Umred — 11 old FAQ pairs

- Where is Gandhi Sagar Lake (Gaotalav) located?
- What is Gandhi Sagar Lake famous for?
- Is there any entry fee to visit the lake?
- What is the best time to visit Gandhi Sagar Lake?
- Are there any activities available at the lake?
- How can I reach Gandhi Sagar Lake (Gaotalav)?
- What is the nearest major city to visit the lake?
- Is public transport available to reach the lake?
- Which is the nearest railway station?
- Which is the nearest airport?
- Is it suitable for a one-day trip?

Full old answers: `C031` in the content CSV. Source answers are not currently verified.

### Gandhi Sagar Park, Umred — 5 old FAQ pairs

- How can I reach Gandhi Sagar Park from Nagpur?
- Are there public transport options available to reach the park?
- What is the best time to visit Gandhi Sagar Park?
- How much time should I plan for a visit?
- Is the park suitable for a day trip?

Full old answers: `C032` in the content CSV. Source answers are not currently verified.

### Shree Gajanan Maharaj Devasthan WCL, Umred — 10 old FAQ pairs

- What is this place?
- Is it good for a picnic?
- Is there any entry fee?
- How far is it from Nagpur?
- What is the ticket price of bus?
- Where can I catch the bus in Nagpur?
- Where should I go by bus or travels?
- Is public transport available?
- Is the road good?
- Best time to visit?

Full old answers: `C033` in the content CSV. Source answers are not currently verified.

### Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth — 5 old FAQ pairs

- Where is the temple located?
- How can I reach the temple?
- Is photography allowed inside the temple?
- Is there any entry fee to visit the temple?
- How far is the temple from Nagpur?

Full old answers: `C034` in the content CSV. Source answers are not currently verified.

Operational answers need verification; template questions can be simplified without inventing answers. Use existing PlaceFAQ ownership, order, active state and parent-version checking later.

## Image plan

There are 26 approximate Umred image families: one Destination hero family and 25 Place families. Each Place has one proposed hero; the remaining 21 Place families are gallery candidates. Count families rather than thumbnails when preparing selection. No image file was fetched or viewed.

Old lake primary metadata uses a Shiva-temple image. The proposed lake hero uses the named lake-side-view family, with shrine images retained as contextual gallery candidates. WCL's old primary video-point landscape stays in the gallery; the temple-view family is its proposed hero. These are filename/context proposals requiring visual review, not approved crops or replacements.

### Gandhi Sagar Lake, Umred

Hero candidate family: `Gandhi-Sagar-Lake-Gaotalav-Umred​-side-view1.webp`. 5 gallery families:

- `Gandhi-Sagar-Lake-Gaotalav-Umred​-side-view2.webp`
- `Gandhi-Sagar-Lake-Gaotalav-Umred​-side-view3.webp`
- `Gandhi-Sagar-Lake-Gaotalav-Umred​.webp`
- `shiv-temple-Gandhi-Sagar-Lake-Gaotalav-Umred​.webp`
- `shivling-Gandhi-Sagar-Lake-Gaotalav-Umred​.webp`

Source URLs, variants, declared dimensions and alt/caption text are in the image CSV. All require owner rights confirmation and visual/exact-subject review.

### Gandhi Sagar Park, Umred

Hero candidate family: `Gandhi-Sagar-Park.webp`. 5 gallery families:

- `Beautiful-Gandhi-Sagar-Park-in-umred.webp`
- `Gandhi-Sagar-Park-Garden-views.webp`
- `Gandhi-Sagar-Park-front-view.webp`
- `Gandhi-Sagar-Park-garden-view.webp`
- `Gandhi-Sagar-Park-out-side-view.webp`

Source URLs, variants, declared dimensions and alt/caption text are in the image CSV. All require owner rights confirmation and visual/exact-subject review.

### Shree Gajanan Maharaj Devasthan WCL, Umred

Hero candidate family: `Shree-gajanan-maharaj-temple-picnic-spot-wcl-umred.webp`. 6 gallery families:

- `Shree-gajanan-maharaj-temple-entry-gate-picnic-spot-umred.webp`
- `Shree-gajanan-maharaj-temple-outside-view-picnic-spot-umred.webp`
- `Shree-gajanan-maharaj-temple-picnic-spot-umred.webp`
- `Shree-gajanan-maharaj-temple-picnic-spot-video-point-umred.webp`
- `shiv-mandir-picnic-spot-umred-inside-view.webp`
- `shiv-temple-picnic-spot-umred-inside-views.webp`

Source URLs, variants, declared dimensions and alt/caption text are in the image CSV. All require owner rights confirmation and visual/exact-subject review.

### Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth

Hero candidate family: `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-front-view.webp`. 5 gallery families:

- `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-darshan.webp`
- `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-inside-door-view.webp`
- `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view-gajanan-maharaj.webp`
- `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view.webp`
- `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view2.webp`

Source URLs, variants, declared dimensions and alt/caption text are in the image CSV. All require owner rights confirmation and visual/exact-subject review.

Some lake/shrine filenames contain an invisible zero-width character. Preserve exact URLs and safely encode them during later approved retrieval; check encoded aliases before deduplication. Gallery declarations commonly describe 1024px variants. Actual bytes, dimensions, file integrity and duplicates remain unverified.

For every image, obtain creator/owner, original source, license or permission/usage basis, attribution and rights verification date. Confirm exact subject and alt text. Select HERO/GALLERY and ordering separately for Destination and each Place. Approved files must use PublicMediaAsset normalization and entity-owned relationships; no old-site hotlinks or cross-entity gallery assignments.

## Later sequence — not authorized now

1. Resolve Umred scope, lake/park identity, naming and full Admin/production collisions.
2. Obtain authoritative content/visitor review and per-image rights evidence; select exact-subject photos.
3. Prepare a concrete field-by-field proposal preserving existing slugs, curated/Admin copy, FAQs and media unless a reviewed change is justified.
4. In a separately authorized phase, use existing Admin Discovery to create/reuse an Umred draft and draft Places with canonical District/Interest relationships. Review verified enrichment and FAQs.
5. Retrieve approved originals only then; upload through the existing public-media pipeline and inspect entity-specific hero/gallery previews.
6. Publish Destination before linked Places through audited lifecycle/version checks. Verify Destination/Place routes, district/Interest discovery, FAQs and responsive media. Do not create hotel, Safari, booking or payment inventory.

Current stop point: no drafts, records, imports, image files/uploads, migrations, publishing or cutover performed.


## Subsequent Umred textual pilot — 3 October 2026

The inventory above records the original audit and planning state. The separately authorized Umred text pilot has now created a draft Destination, two temple drafts and 15 Place FAQs in the local development database. Lake/park remain unresolved and uncreated; all image rights remain pending with mapping only. No overview was fabricated and nothing was published. See [Umred pilot result](umred-pilot-result.md) for canonical local IDs, FAQ/image ownership, execution, verification and remaining owner decisions. Remaining-site and image migration have not begun.
