# Umred textual pilot result

Executed 3 October 2026 against the configured **local development** MySQL database. No production deployment, schema migration, publication, image retrieval/import or remaining-site migration occurred. This result supersedes the inventory-only stop point for Umred alone.

## Entity resolution and hierarchy

The full read-only collision check included every lifecycle state: 36 Districts, zero Destinations, 49 curated Places, no Admin/unpublished Place candidates, nine Interests and ten Stories. Nagpur is canonical District ID **25**, slug `nagpur`. Both temple identities are supported by their source-page introductions and the Umred listing. Names, punctuation, Shri/Shree, W.C.L/WCL and Kawarapeth/Kawrapeth variants were compared. The existing Vitthal-Rukmini temple in Pandharpur/Solapur is distinct. The old Nashik Gajanan institution is outside this pilot.

| Record | Entity | Decision / actual action | Local ID | State |
| --- | --- | --- | --- | --- |
| C030 | Umred | CREATE / CREATE | 409 | DRAFT |
| C031 | Gandhi Sagar Lake, Umred | POSSIBLE_DUPLICATE / REVIEW | None | Not created or merged |
| C032 | Gandhi Sagar Park, Umred | POSSIBLE_DUPLICATE / REVIEW | None | Not created or merged |
| C033 | Shree Gajanan Maharaj Devasthan WCL, Umred | CREATE / CREATE | 394 | DRAFT |
| C034 | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | CREATE / CREATE | 395 | DRAFT |

Zero existing entities were enriched or overwritten. On the committed rerun the three imported entities were SKIP and both lake/park candidates remained REVIEW. Existing matches are classified ENRICH_EXISTING but conservatively SKIP pending explicit Admin review; reporting that decision does not imply enrichment happened.

The two migrated Places use `district_id=25`, `destination_id=409` and the existing Interest IDs (sacred-spiritual, plus nature-hills for WCL). No new taxonomy or DiscoveryStory was created. Umred is a draft planning-area parent supported by the old tehsil listing and explicit Place locality descriptions. Confirm town versus wider taluka scope before publishing.

## Content and verification

Umred retains **null overview and short summary**, no FAQs and no media. Its source body only lists four attractions; the broad sanctuary metadata was not imported as an overview or converted into Safari content.

Both temples retain the full archived About paragraphs verbatim and the source introduction as their short description, including source wording/capitalization. Draft status leaves devotional/editorial claims available for owner review. Existing fields receive the old address, opening hours, entry-fee answer and getting-there material. WCL also receives its old best-time answer. HINDU tradition follows the explicitly named Hindu deities/saint and existing sacred-spiritual classification.

| Place | Migrated visitor claims (unverified) | Intentionally absent |
| --- | --- | --- |
| Shree Gajanan Maharaj Devasthan WCL, Umred | Open daily : 5 am to 7 pm; V872+8JQ, MSH 9, Gangapur, Maharashtra 441203; source fee and route answers | duration, railway, airport |
| Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | Open daily 5.00 Am to 8.00 pm; V857+HV, Kawrapeth, Gangapur Umred Rural, Maharashtra 441203; source fee and route answers | duration, railway, airport, best time |

All migrated visitor claims remain **OLD_SITE_UNVERIFIED**, with the original page URL and an explicit reconfirmation notice in `visitor_info_source`. `visitor_info_verified_at` remains null; the crawl date is not a verification date. WCL bus fares, stops, walking times, road quality, seasonal advice and access permissions, and Kawrapeth fees, transport, photography and distances need current confirmation. Existing frontend source presentation already says “Details may change; confirm before travel.” No missing logistics were generated or copied from another Place.

## FAQ ownership and ordering

31 source FAQs were checked against the archived page context: **31 PLACE FAQ classifications**, zero Destination FAQs and zero duplicate-within-owner questions. Similar generic questions on different Place pages are separate owned FAQs, not town-level duplicates. **15 imported** (WCL 10; Kawrapeth 5). **16 held for review** (lake 11; park 5), because their canonical Place identities remain unresolved. Ordering is zero-based source order. Answers are retained verbatim in the reviewed payload; source evidence and CSV retain every held answer.

| Source / order | Question | Classification | Result / owner |
| --- | --- | --- | --- |
| C031 / 0 | Where is Gandhi Sagar Lake (Gaotalav) located? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 1 | What is Gandhi Sagar Lake famous for? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 2 | Is there any entry fee to visit the lake? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 3 | What is the best time to visit Gandhi Sagar Lake? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 4 | Are there any activities available at the lake? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 5 | How can I reach Gandhi Sagar Lake (Gaotalav)? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 6 | What is the nearest major city to visit the lake? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 7 | Is public transport available to reach the lake? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 8 | Which is the nearest railway station? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 9 | Which is the nearest airport? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C031 / 10 | Is it suitable for a one-day trip? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C032 / 0 | How can I reach Gandhi Sagar Park from Nagpur? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C032 / 1 | Are there public transport options available to reach the park? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C032 / 2 | What is the best time to visit Gandhi Sagar Park? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C032 / 3 | How much time should I plan for a visit? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C032 / 4 | Is the park suitable for a day trip? | PLACE FAQ; REVIEW REQUIRED for entity resolution | Held; no canonical Place created |
| C033 / 0 | What is this place? | PLACE FAQ | Imported to Place 394 |
| C033 / 1 | Is it good for a picnic? | PLACE FAQ | Imported to Place 394 |
| C033 / 2 | Is there any entry fee? | PLACE FAQ | Imported to Place 394 |
| C033 / 3 | How far is it from Nagpur? | PLACE FAQ | Imported to Place 394 |
| C033 / 4 | What is the ticket price of bus? | PLACE FAQ | Imported to Place 394 |
| C033 / 5 | Where can I catch the bus in Nagpur? | PLACE FAQ | Imported to Place 394 |
| C033 / 6 | Where should I go by bus or travels? | PLACE FAQ | Imported to Place 394 |
| C033 / 7 | Is public transport available? | PLACE FAQ | Imported to Place 394 |
| C033 / 8 | Is the road good? | PLACE FAQ | Imported to Place 394 |
| C033 / 9 | Best time to visit? | PLACE FAQ | Imported to Place 394 |
| C034 / 0 | Where is the temple located? | PLACE FAQ | Imported to Place 395 |
| C034 / 1 | How can I reach the temple? | PLACE FAQ | Imported to Place 395 |
| C034 / 2 | Is photography allowed inside the temple? | PLACE FAQ | Imported to Place 395 |
| C034 / 3 | Is there any entry fee to visit the temple? | PLACE FAQ | Imported to Place 395 |
| C034 / 4 | How far is the temple from Nagpur? | PLACE FAQ | Imported to Place 395 |

## All 26 image-family mappings

**Mapping only.** All families remain OWNER_CONFIRMATION_REQUIRED. No old image file was downloaded, copied, imported, published or hotlinked. No PublicMediaAsset, DestinationMedia or PlaceMedia was created or changed. Hero image fields remain null and platform fallback selection is untouched. Exact source URLs, encoded variants, alt/caption text, declared dimensions and reuse appear in `image-migration-inventory.csv`.

| Family | Filename family | Proposed owner | Role | Canonical relationship |
| --- | --- | --- | --- | --- |
| 03901d8cc85c | `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view.webp` | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | PLACE_GALLERY | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| 0ede3b0f2b35 | `Shree-gajanan-maharaj-temple-picnic-spot-wcl-umred.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_HERO | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| 1c10448b17dc | `shivling-Gandhi-Sagar-Lake-Gaotalav-Umred​.webp` | Gandhi Sagar Lake, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-lake-umred` |
| 2b75b01d8695 | `Gandhi-Sagar-Park-out-side-view.webp` | Gandhi Sagar Park, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-park-umred` |
| 30b54087a082 | `Shree-gajanan-maharaj-temple-picnic-spot-video-point-umred.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_GALLERY | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| 376456607bc7 | `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-darshan.webp` | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | PLACE_GALLERY | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| 52e1c361ff91 | `Beautiful-Gandhi-Sagar-Park-in-umred.webp` | Gandhi Sagar Park, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-park-umred` |
| 575f96a9ccdb | `shiv-temple-picnic-spot-umred-inside-views.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_GALLERY | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| 591bb1b28387 | `shiv-mandir-picnic-spot-umred-inside-view.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_GALLERY | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| 5fe55172c4f8 | `Gandhi-Sagar-Park-front-view.webp` | Gandhi Sagar Park, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-park-umred` |
| 605e808cbb9d | `Gandhi-Sagar-Park-garden-view.webp` | Gandhi Sagar Park, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-park-umred` |
| 61e8b62d01a9 | `Gandhi-Sagar-Park.webp` | Gandhi Sagar Park, Umred | PLACE_HERO | `/places/nagpur/gandhi-sagar-park-umred` |
| 6511c3ada86a | `Shree-gajanan-maharaj-temple-entry-gate-picnic-spot-umred.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_GALLERY | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| 74eb8ba3e0da | `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-front-view.webp` | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | PLACE_HERO | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| 87694c5369cf | `shiv-temple-Gandhi-Sagar-Lake-Gaotalav-Umred​.webp` | Gandhi Sagar Lake, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-lake-umred` |
| 8913a71b50fb | `Gandhi-Sagar-Lake-Gaotalav-Umred​-side-view2.webp` | Gandhi Sagar Lake, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-lake-umred` |
| a27afad69392 | `Gandhi-Sagar-Park-Garden-views.webp` | Gandhi Sagar Park, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-park-umred` |
| abe95a3d7210 | `Umred.webp` | Umred | DESTINATION_HERO | `/destinations/nagpur/umred` |
| ac3de7bf2d5e | `Shree-gajanan-maharaj-temple-picnic-spot-umred.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_GALLERY | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| ad27e4f10664 | `Shree-gajanan-maharaj-temple-outside-view-picnic-spot-umred.webp` | Shree Gajanan Maharaj Devasthan WCL, Umred | PLACE_GALLERY | `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` |
| af317ec2c842 | `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view2.webp` | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | PLACE_GALLERY | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| ba40b5d01683 | `Gandhi-Sagar-Lake-Gaotalav-Umred​-side-view3.webp` | Gandhi Sagar Lake, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-lake-umred` |
| c33537fcad9d | `Gandhi-Sagar-Lake-Gaotalav-Umred​-side-view1.webp` | Gandhi Sagar Lake, Umred | PLACE_HERO | `/places/nagpur/gandhi-sagar-lake-umred` |
| d320f0605551 | `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-inside-door-view.webp` | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | PLACE_GALLERY | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| d828d1132c74 | `Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view-gajanan-maharaj.webp` | Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth | PLACE_GALLERY | `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| e7e8e515db41 | `Gandhi-Sagar-Lake-Gaotalav-Umred​.webp` | Gandhi Sagar Lake, Umred | PLACE_GALLERY | `/places/nagpur/gandhi-sagar-lake-umred` |

Families reconcile to one Destination HERO and 25 Place families (four HERO, 21 GALLERY): lake 6, park 6, WCL 7 and Kawrapeth 6. The 106 Umred image page/URL rows include resized/reused variants; they are not 106 separate assets. Every row retains SAME_URL_OR_WORDPRESS_FILENAME_FAMILY;NOT_BYTE_VERIFIED. Filename grouping is approximate, not proof of identical bytes. Possible alternate-upload families remain documented in the CSV; no deduplication/deletion or rights approval occurred. Lake filenames include an invisible zero-width character, preserved in source references.

Lake hero proposal uses the named lake-side-view1 family instead of its old Shiva-shrine metadata primary. WCL hero proposal uses the named temple WCL family; video-point remains a gallery candidate. Subject/visual review is still required. One Umred hero does not authorize a Destination gallery assembled from Place thumbnails.

## Mechanism, execution and safety

A separate versioned, reviewed JSON payload (`backend/app/data/umred_pilot_v1.json`) and operator-run importer follow the established controlled seed pattern. The CSV is not executable import input. `content_source=MIGRATION` identifies newly imported drafts; existing Admin and curated records are always skipped, including Admin edits to imported rows. All slugs/publication states/media and existing FAQs are preserved. Known identity matches reuse records, uncertain variants produce REVIEW, and ambiguous parent identity prevents all new child creation. Required canonical references are checked before writes. Database uniqueness plus a single caller-owned transaction protect the batch.

Commands run:

```powershell
backend/venv/Scripts/python.exe backend/scripts/import_umred_pilot.py --report docs/content-migration/evidence/umred-dry-run.json
backend/venv/Scripts/python.exe backend/scripts/import_umred_pilot.py --apply --report docs/content-migration/evidence/umred-apply.json
backend/venv/Scripts/python.exe backend/scripts/import_umred_pilot.py --apply --report docs/content-migration/evidence/umred-rerun.json
```

Default execution rolls back. `--apply` is restricted to a local development database. The dry-run allocated temporary IDs but committed no rows; only the apply report records canonical local IDs. First committed run: CREATE 3, ENRICH 0, SKIP 0, REVIEW 2. Second committed run: CREATE 0, ENRICH 0, SKIP 3, REVIEW 2; no duplicate Destinations, Places or FAQs. Imports never publish records or run at startup. Admin remains the publication workflow.

## Canonical routes and public behavior

- `/destinations/nagpur/umred` — reserved canonical draft route; currently returns public 404.
- `/places/nagpur/shree-gajanan-maharaj-devasthan-wcl-umred` — reserved canonical draft route; currently returns public 404.
- `/places/nagpur/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` — reserved canonical draft route; currently returns public 404.

Draft 404 responses are intentional publication safety, not proof of a live Umred landing page. The existing Destination renderer and backend query automatically derive published membership from `Place.destination_id`; tests prove published membership and exclusion of drafts with synthetic test-only overview text. No test text reached the pilot database. Umred cannot publish until source-backed overview exists, and its linked Places cannot publish first.

No frontend cards/routes were hardcoded or redesigned. Existing breadcrumbs, canonical metadata, related Places, Interest links, Find Stays and Safari components/services remain unchanged. Live public API checks retain 49 Places, 14 sacred-spiritual Places and ten Stories. No incomplete pilot record appears in public discovery/search.

## Verification results

- 57 relevant backend tests passed: new pilot, curated seed, Destination/Place integration, DiscoveryStory, Admin Discovery, content enrichment and public media/manifest.
- Eight existing frontend media, brand and discovery tests passed (`npm test`). No frontend behavior changed; lint/type/build were not required or rerun.
- 36 source/scope/local-database checks passed: original records and Interest memberships unchanged, exactly one Destination/two Places/15 FAQs added, source paragraphs/answers preserved, null verification dates, no media additions and safe public draft/search exclusion.
- Seven live API checks passed: three draft-detail 404s; public Places, sacred Interest filter, Story listing and Nagpur Destination listing 200.
- Inventory CSV exact round-trips passed; all 38 existing inventory QA checks passed after the targeted status/note updates.

Evidence: `evidence/umred-before.json`, `umred-dry-run.json`, `umred-apply.json`, `umred-rerun.json`, `umred-verification.json`, `umred-public-verification.json`, and `quality-checks.json`. No generated build/media artifact is added.

## Files and data changed

- Added reviewed pilot payload, importer service, operator script and 11 focused backend tests.
- Added this result and read-only verification helper/evidence. Updated five content inventory statuses/notes and 106 Umred image-row mapping notes; source fields, other entities and every rights status are preserved.
- Updated phase-status cross-references in inventory summary, overview and pilot plan. The original inventory/public snapshot remains dated historical evidence.
- Local database additions only: Umred draft, two temple drafts, 15 owned Place FAQs and three existing-Interest memberships. No schema or unrelated backend/frontend functionality changed.

## Exact owner decisions still required

1. Confirm whether Umred represents town or wider taluka/planning area and supply a source-backed overview (and summary if desired). Approve it through Admin before publication.
2. Establish lake/park boundaries and identity: one attraction, two distinct Places or parent attraction/subfeatures. Provide local authoritative evidence, canonical names and locations; then decide whether either/both may be created. All 16 FAQs remain held meanwhile.
3. Review both temple names, addresses and source About claims. Confirm WCL public/picnic access and conditions; verify current hours, fees, transport fares/stops, road/walking advice, photography and seasonal recommendations before setting verification dates or approving publication.
4. For each of 26 image families, confirm creator/owner, license or explicit permission, usage basis, attribution, rights verification date, exact subject and original file choice. Review visual suitability and any duplicate upload families before a separately authorized media phase.

Stop: Umred textual pilot only. No image import, other destination migration or domain cutover.
