# Migration inventory summary

3 October 2026. Inventory and planning only. No application, database, seed, production-image or domain-cutover changes were made.

| Measure | Count | Meaning |
| --- | ---: | --- |
| Public HTML pages read | 44 | 42 sitemap + 2 link-only pages; all HTTP 200. |
| Empty placeholders | 8 | HTTP 200 does not imply usable content. |
| District pages with usable listings | 3 | Existing canonical District identities. |
| Proposed Destinations | 6 | Daulatabad, Khuldabad, Verul, Kuhi, Umred, Trimbakeshwar. |
| Proposed Place candidates | 17 | Includes matches and two held lake/park candidates. |
| Place CREATE candidates | 11 | Requires authority, rights and full collision review. |
| Existing Place matches | 4 | Additive ENRICH_EXISTING proposals; retain identity/copy. |
| Place candidates held as possible duplicates | 2 | One unresolved lake/park relationship pair. |
| Proposed new Discovery Stories | 0 | No standalone narrative found; existing ten preserved. |
| ENRICH_EXISTING actions including District listings | 7 | Four Places + three Districts; no edits executed. |
| Matches including empty district placeholders | 13 | Four Places + three usable Districts + six empty district listings. |
| CREATE actions across Destination/Place | 17 | Six Destinations + eleven Places. |
| SKIP records | 18 | Home, category/updates indexes, utility/legal pages and placeholders. |
| Records marked REVIEW_REQUIRED | 27 | 26 hierarchy/content records + ambiguous empty Mumbai page. |
| Place records with volatile information | 17 | All have unverified operational claims. |
| Raw / unique-within-page FAQ pairs | 142 / 140 | 107 Place FAQs; 31 in Umred. |
| Exact image URLs | 237 | Includes resized and encoded/scheme variants. |
| Image page/URL rows | 486 | Repeated appearances retained. |
| Approximate filename families | 124 | Not verified distinct photographs. |
| Families reused across pages | 24 | Shared thumbnails/related cards. |
| Image rights needing owner confirmation | 237 URLs / 486 rows | 124 families; no rights cleared. |
| RIGHTS_CLEARED / REPLACE / UNKNOWN rights rows | 0 / 0 / 0 | All await confirmation; no replacement decision made. |
| Image bytes downloaded | 0 | URLs and page declarations only. |
| Umred Place candidates | 4 | Lake, Park, WCL institution and Kawrapeth temple. |
| Umred image families | 26 | One Destination family + 25 Place families. |

Image role occurrences, including URL variants/page reuse: PLACE_HERO 281, PLACE_GALLERY 191, DESTINATION_HERO 14. No Destination gallery/editorial relationship was established. Roles are candidates, not approved selections.

## Existing-system comparison

Repository: 36 Districts, nine Interests, 49 curated Places, 10 Stories. The local public catalogue returned the same counts and zero published Destinations across 36 successful district-list GETs. No authenticated Admin or production data was read; draft/unpublished/Admin/production collisions remain unknown.

Place matches: Devgiri-Daulatabad Fort, Ghrishneshwar Temple, Ellora Caves and Trimbakeshwar Temple. Proposed Destination attachment is a separate decision and must not overwrite an existing relationship or copy. No matching curated Umred Place was found. Religious institutions with similar names in other districts are not matches.

## Umred findings

The listing supports Nagpur → proposed Umred → four candidate Places. Lake/Park boundaries need confirmation before creation. Shrines mentioned inside pages do not automatically become extra records. Umred provides a listing and metadata but lacks a usable Destination overview, dedicated FAQs, logistics or established gallery.

Old lake primary metadata uses a Shiva-temple image. The proposed hero instead uses the named lake-side-view family, pending visual/rights review. WCL's temple-view family is proposed as its hero; the old video-point primary remains a gallery candidate. No pictures were fetched or viewed.

Hours, free-entry claims, distances, rail/airport routes, bus fares and WCL access remain OLD_SITE_UNVERIFIED. See the [pilot plan](umred-pilot-plan.md) for field/media/FAQ decisions.

## Gaps and unresolved decisions

- Eight empty pages and ambiguous Mumbai district mapping.
- Town versus tehsil Destination scope, especially Trimbakeshwar/Kuhi; Harihar/Ambhora remain district-level pending review.
- Full production and unpublished/Admin collisions.
- Lake/Park boundaries, institution spelling and geography.
- Every image's creator/license/permission/attribution and subject suitability.
- Historical/visitor-information verification; no old claim was promoted to current fact.
- Image-file reachability, decode/hash/perceptual checks, owner WordPress export and hidden/AJAX-only content are outside this phase.

All discovered internal pages were processed, URL duplicates removed, sitemap coverage reconciled, image reuse inspected, every proposed Place assigned a canonical District and Destination links qualified by evidence. CSV exact round-trips passed. Automated results: `evidence/quality-checks.json`.

Deliverables: [overview](old-site-inventory.md), [content CSV](content-migration-inventory.csv), [image CSV](image-migration-inventory.csv), [repository map](repository-migration-map.md), [Umred plan](umred-pilot-plan.md).

Stop point: inventory complete. No import, image retrieval/upload, publishing, migration, redesign or cutover has begun.


## Subsequent Umred textual pilot — 3 October 2026

The inventory above records the original audit and planning state. The separately authorized Umred text pilot has now created a draft Destination, two temple drafts and 15 Place FAQs in the local development database. Lake/park remain unresolved and uncreated; all image rights remain pending with mapping only. No overview was fabricated and nothing was published. See [Umred pilot result](umred-pilot-result.md) for canonical local IDs, FAQ/image ownership, execution, verification and remaining owner decisions. Remaining-site and image migration have not begun.
