# Umred image staging audit

Audited 3 October 2026. This phase staged and technically inspected old-site originals only. No public-media import, content publication, lake/park entity resolution or remaining-site migration occurred.

## Accounting and technical results

- All **26 inventory families** accounted for: Umred Destination 1; WCL Temple 7; Kawrapeth Temple 6; Gandhi Sagar Lake 6; Gandhi Sagar Park 6; Unknown/Ambiguous 0.
- **26 actual original files staged; zero inaccessible/missing originals.** One observed original per normalized filename family was fetched. Equivalent raw/percent-encoded URLs were coalesced; resized thumbnail variants were not downloaded. Original provenance and request/final URLs are retained in the evidence.
- All 26 decode as WebP: 25 at 1280×960 or 1600×1200, one at 1170×650. All meet the existing 640×360 minimum and 8 MB size limit. No decoding corruption or transparency detected. **EXIF is present in 25 originals**; originals are retained unmodified, with metadata contents confined to ignored staging.
- Dimension-based quality: **25 GOOD, one ACCEPTABLE, zero LOW_QUALITY, zero UNUSABLE, zero technical REVIEW_REQUIRED.** Visual sharpness, extreme compression artifacts, exact subject identity and editorial suitability are not certified by these checks.
- **One exact duplicate pair** (two family references), zero additional likely visual duplicate pairs. **25 distinct usable byte checksums**: 24 singleton families classified UNIQUE plus one two-family EXACT_DUPLICATE group.
- All **26 family references / 25 distinct byte images require rights confirmation**. Rights remain OWNER_CONFIRMATION_REQUIRED. Zero rights approvals inferred.

## Non-public staging and reproducibility

Originals are stored as `migration-staging/umred/images/{family_id}.source`; the extension avoids relying on a filename for detected format. `.gitignore` excludes the entire `/migration-staging/` directory. A local-only contact sheet is `migration-staging/umred/owner-reference.jpg`, labelled with family IDs and source association groups, not asserted subjects. Neither originals nor previews are frontend/public assets or backend uploads. No public URLs or storage uploads were created.

The operator script `docs/content-migration/tools/audit_umred_images.py` restricts retrieval to inventoried Umred families on the old site upload path, preserves source URL aliases, limits download size and records download/decode failures. It never imports application models or calls public-media processing. Existing files are inspected locally on rerun without refetching, while their original request provenance is retained. Originals are never deleted or normalized in place.

Technical evidence: [audit JSON](evidence/umred-image-audit.json). Structured owner checklist: [review CSV](umred-image-review.csv). Original page/variant associations remain in [image inventory](image-migration-inventory.csv), whose 106 Umred rows have audit status notes added without changing source URLs, proposed ownership or rights.

## Duplicate and quality method

SHA-256 compares exact downloaded bytes. Normalized filename/source relationships retain the existing WordPress family grouping; same URL, resize suffix and percent-encoding aliases are not treated as independent assets. A local Pillow 64-bit difference hash (9×8 grayscale, Lanczos) flags additional similarity candidates at Hamming distance ≤6. This heuristic can miss duplicates or flag unrelated similar compositions; UNIQUE means no match found by these checks, not a universal proof of originality. Normalized oriented RGB pixel hashes provide supplementary equality evidence. No automatic cross-owner merging occurs.

GOOD requires at least 1280×720 and ratio 1.2–2.2. ACCEPTABLE passes the existing 640×360 minimum but misses that hero preference. Below the minimum is LOW_QUALITY/THUMBNAIL_ONLY; extreme ratios outside 0.5–3 require review; decode failure is UNUSABLE. These audit preferences do not replace the backend validator or approve an actual hero. Technical HERO_CANDIDATE eligibility does not change the source-proposed HERO/GALLERY role.

The exact duplicate pair is:

| Family | Source-associated group | Original filename | SHA-256 |
| --- | --- | --- | --- |
| e7e8e515db41 | Gandhi Sagar Lake | `Gandhi-Sagar-Lake-Gaotalav-Umred​.webp` | `cec51c70764c9bf8cb10a9ece2f698f0c87ca18d924e7065a8b078144c335545` |
| 2b75b01d8695 | Gandhi Sagar Park | `Gandhi-Sagar-Park-out-side-view.webp` | `cec51c70764c9bf8cb10a9ece2f698f0c87ca18d924e7065a8b078144c335545` |

Both files are 1280×960, 211,952 bytes with equal normalized pixels. **No preferred technical candidate is chosen:** their resolution and bytes are identical. Keep both original references. Their cross-page reuse does not establish whether lake/park are one or two Places, or establish which subject either file depicts. Both groups remain ENTITY_RESOLUTION_REQUIRED.

## Owner-review checklist

For **each row**, answer: **Can Maharashtra Tourist Places reuse this exact image on the new website?** Supply creator/owner, license or explicit permission, usage basis, required attribution and a genuine rights-confirmation date. Confirm what the image depicts and whether its proposed entity association is correct. Source placement and filenames are associations only; they do not establish copyright ownership or subject identity.

Open the local contact sheet using its family reference, then inspect the retained original if needed. The CSV includes full source page/URL, local reference, dimensions, byte size, hashes, metadata flags, quality, duplicate status and an individual owner question. **Rights for every row: OWNER_CONFIRMATION_REQUIRED.**

### Umred Destination

| Reference / source file | Source page | Proposed role | Actual dimensions | Quality | Duplicate | Entity status |
| --- | --- | --- | --- | --- | --- | --- |
| `abe95a3d7210` [Umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/) | DESTINATION_HERO | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |

### WCL Temple

| Reference / source file | Source page | Proposed role | Actual dimensions | Quality | Duplicate | Entity status |
| --- | --- | --- | --- | --- | --- | --- |
| `0ede3b0f2b35` [Shree-gajanan-maharaj-temple-picnic-spot-wcl-umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-gajanan-maharaj-temple-picnic-spot-wcl-umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/) | PLACE_HERO | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `30b54087a082` [Shree-gajanan-maharaj-temple-picnic-spot-video-point-umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-gajanan-maharaj-temple-picnic-spot-video-point-umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE_GALLERY | 1170×650 | ACCEPTABLE | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `575f96a9ccdb` [shiv-temple-picnic-spot-umred-inside-views.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/shiv-temple-picnic-spot-umred-inside-views.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `591bb1b28387` [shiv-mandir-picnic-spot-umred-inside-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/shiv-mandir-picnic-spot-umred-inside-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `6511c3ada86a` [Shree-gajanan-maharaj-temple-entry-gate-picnic-spot-umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-gajanan-maharaj-temple-entry-gate-picnic-spot-umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `ac3de7bf2d5e` [Shree-gajanan-maharaj-temple-picnic-spot-umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-gajanan-maharaj-temple-picnic-spot-umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `ad27e4f10664` [Shree-gajanan-maharaj-temple-outside-view-picnic-spot-umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-gajanan-maharaj-temple-outside-view-picnic-spot-umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |

### Kawrapeth Temple

| Reference / source file | Source page | Proposed role | Actual dimensions | Quality | Duplicate | Entity status |
| --- | --- | --- | --- | --- | --- | --- |
| `03901d8cc85c` [Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | PLACE_GALLERY | 1600×1200 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `376456607bc7` [Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-darshan.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-darshan.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | PLACE_GALLERY | 1600×1200 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `74eb8ba3e0da` [Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-front-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-front-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/) | PLACE_HERO | 1600×1200 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `af317ec2c842` [Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view2.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view2.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | PLACE_GALLERY | 1600×1200 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `d320f0605551` [Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-inside-door-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-inside-door-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | PLACE_GALLERY | 1600×1200 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |
| `d828d1132c74` [Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view-gajanan-maharaj.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Shree-Vitthal-Rukmini-Ganeshrao-Maharaj-Devasthan-Kawrapeth-out-side-view-gajanan-maharaj.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | PLACE_GALLERY | 1600×1200 | GOOD | UNIQUE | DRAFT_ENTITY_RESOLVED |

### Gandhi Sagar Lake

| Reference / source file | Source page | Proposed role | Actual dimensions | Quality | Duplicate | Entity status |
| --- | --- | --- | --- | --- | --- | --- |
| `1c10448b17dc` [shivling-Gandhi-Sagar-Lake-Gaotalav-Umred[U+200B].webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/shivling-Gandhi-Sagar-Lake-Gaotalav-Umred%E2%80%8B.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `87694c5369cf` [shiv-temple-Gandhi-Sagar-Lake-Gaotalav-Umred[U+200B].webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/shiv-temple-Gandhi-Sagar-Lake-Gaotalav-Umred%E2%80%8B.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `8913a71b50fb` [Gandhi-Sagar-Lake-Gaotalav-Umred[U+200B]-side-view2.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Lake-Gaotalav-Umred%E2%80%8B-side-view2.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `ba40b5d01683` [Gandhi-Sagar-Lake-Gaotalav-Umred[U+200B]-side-view3.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Lake-Gaotalav-Umred%E2%80%8B-side-view3.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `c33537fcad9d` [Gandhi-Sagar-Lake-Gaotalav-Umred[U+200B]-side-view1.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Lake-Gaotalav-Umred%E2%80%8B-side-view1.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/) | PLACE_HERO | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `e7e8e515db41` [Gandhi-Sagar-Lake-Gaotalav-Umred[U+200B].webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Lake-Gaotalav-Umred%E2%80%8B.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | PLACE_GALLERY | 1280×960 | GOOD | EXACT_DUPLICATE → 2b75b01d8695 | ENTITY_RESOLUTION_REQUIRED |

### Gandhi Sagar Park

| Reference / source file | Source page | Proposed role | Actual dimensions | Quality | Duplicate | Entity status |
| --- | --- | --- | --- | --- | --- | --- |
| `2b75b01d8695` [Gandhi-Sagar-Park-out-side-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Park-out-side-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | PLACE_GALLERY | 1280×960 | GOOD | EXACT_DUPLICATE → e7e8e515db41 | ENTITY_RESOLUTION_REQUIRED |
| `52e1c361ff91` [Beautiful-Gandhi-Sagar-Park-in-umred.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Beautiful-Gandhi-Sagar-Park-in-umred.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `5fe55172c4f8` [Gandhi-Sagar-Park-front-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Park-front-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `605e808cbb9d` [Gandhi-Sagar-Park-garden-view.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Park-garden-view.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `61e8b62d01a9` [Gandhi-Sagar-Park.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Park.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/) | PLACE_HERO | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |
| `a27afad69392` [Gandhi-Sagar-Park-Garden-views.webp](https://maharashtratouristplaces.in/wp-content/uploads/2026/04/Gandhi-Sagar-Park-Garden-views.webp) | [Source page](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | PLACE_GALLERY | 1280×960 | GOOD | UNIQUE | ENTITY_RESOLUTION_REQUIRED |

### Unknown/Ambiguous

No inventory families are currently assigned to this group. Reclassify here if owner subject review finds an uncertain association; do not force an entity.

## Proposed candidates, pending owner approval

- **WCL Temple:** retain `0ede3b0f2b35` as the source-proposed hero candidate; six gallery candidates remain. `30b54087a082` (video-point, 1170×650) is ACCEPTABLE/GALLERY_CANDIDATE, while the other six files are GOOD. None requires replacement based solely on decode/dimensions; request a higher-resolution original if a large hero crop is desired for video-point.
- **Kawrapeth Temple:** retain `74eb8ba3e0da` as source-proposed hero candidate; five gallery candidates remain. All six are 1600×1200 and GOOD. Exact subjects still require owner confirmation.
- **Umred Destination:** `abe95a3d7210` is the only source-proposed Destination HERO, 1280×960 and GOOD. Its actual subject and representativeness require confirmation. Do not assemble a Destination gallery from Place photos.
- **Lake/Park:** six families each remain separate, ENTITY_RESOLUTION_REQUIRED. Even the exact duplicate is retained under both source associations. No Place or asset assignments may be made from this audit alone.

## Future approved-media import plan — not executed

1. Select the inventoried staged original and retain its source/family/checksum provenance. Confirm source association and actual subject with the owner.
2. Obtain per-image creator/owner, license or explicit permission, usage basis, attribution and rights-verification date. Keep rights pending when evidence is missing.
3. Resolve the target canonical Destination/Place ID. Lake/park require a separate content-identity decision first; do not use a duplicate match as entity authority.
4. Validate original format/signature, decoding, dimensions, byte limit and duplicate evidence. Choose a higher-resolution member only where technically justified; retain all source references. Resolve any cross-entity ownership ambiguity with the owner.
5. In a separately authorized approved-media phase, use existing authenticated Admin `POST /api/v1/admin/discovery/media/{entity_type}/{entity_id}` with its current rights/subject checks and entity lock. Use expected-version checks when subsequently editing/retiring relationships. Supply alt text, specificity, creator_owner, source_name/source_url, usage_basis, attribution_text, rights_verified_at, subject_match_confirmed, role and display_order as applicable.
6. Reuse `store_discovery_image`: JPEG/PNG/WebP signature/decode validation; 8 MB and 30 million pixel limits; EXIF orientation; maximum 2400×2400 bounds; minimum 640×360; metadata-free WebP derivative at quality 86. Inspect the derivative/metadata output and avoid passing original EXIF through.
7. Let the existing service create PublicMediaAsset and the entity-owned DestinationMedia/PlaceMedia relationship, then assign approved HERO/GALLERY and ordering. Preserve approved existing media/fallback behavior through the established replacement/history rules.
8. Preview in existing Admin, verify subject/crop, alt/attribution, rights evidence and canonical entity relationship. Publish content only through existing publication rules; Umred still needs a source-backed overview before publishing itself or its linked Places.

The Admin upload stores a public derivative even while content is draft. It therefore belongs only to the separately authorized approved-media phase, never this staging audit. No alternate media system is introduced.

## Verification and changed files

All 13 staging/provenance/Git-scope checks passed; recorded in `evidence/umred-image-verification.json`.

- Five focused image-audit tests passed: decode/dimensions/thumbnail classification, corruption, exact duplicate across unresolved groups, perceptual candidate classification and URL encoding/source restriction.
- All 57 relevant Discovery/backend tests and eight frontend media/brand/discovery tests passed. No frontend source changed; no build needed.
- All 26 families and 26 source binaries are accounted for. SHA-256 recomputation matches the audit manifest; the local-only reference sheet is additional preview output, not a 27th source image.
- The textual-pilot read-only verifier still passes all 36 checks, including unchanged original media, exactly the same three drafts/15 FAQs and no lake/park creation. No PublicMediaAsset or Destination/Place assignment changed.
- Git-ignore checks cover originals and contact sheet; staging contributes no commit candidates. Public frontend assets and application source remain unchanged.
- CSV exact round-trips and all 38 original inventory QA checks pass. The original HTML inventory zero-download figures are historical; this separate audit records the new 26 staged originals.

Changed: `.gitignore`; image inventory audit notes and corresponding reviewed mapping JSON; this audit, review CSV, technical/review evidence, staging audit tool and five focused tests. Source files/contact sheet exist only in ignored staging.

## Exact owner decisions required

1. Approve or reject reuse for each of 26 family references (25 distinct byte images), with evidence and required credit. Shared bytes do not automatically approve both usages.
2. Confirm actual depicted subject and proposed entity/role for every candidate, including the sole Destination image and shrine/gallery associations.
3. Explain the byte-identical lake/park file association and separately decide lake/park Place identity/boundary; neither image group has been merged.
4. Decide whether the lower-resolution WCL video-point file should remain a gallery candidate or be replaced by an owner-supplied higher-resolution original. No replacement was invented or fetched.
5. Select final hero/gallery sets, order, crops and alt text only after rights/subject review; then separately authorize the approved-media phase.

Stop: staging, technical audit and owner-review preparation only. All three content records remain DRAFT; no public-media import or publication occurred.
