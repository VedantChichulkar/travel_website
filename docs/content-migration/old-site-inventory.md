# Old Maharashtra Tourist Places inventory

Observation date: 3 October 2026, Asia/Kolkata. Source: [owner's old website](https://maharashtratouristplaces.in/). Inventory and mapping only. Extracted claims are unverified source material, not approved production copy.

Read the [repository map](repository-migration-map.md), [summary](migration-summary.md), [Umred plan](umred-pilot-plan.md), and both CSVs together.

## Discovery method and coverage

Read robots, the Yoast sitemap index and its page sitemap, then followed same-site HTML links to queue exhaustion. The sitemap lists 42 pages. Two additional linked pages are [Khuldabad](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/khuldabad/) and [Gandhi Sagar Park](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/). All 44 unique pages returned HTTP 200; no unresolved internal HTML URL remained. Robots contains no public-path prohibition. `wp-sitemap.xml` and `sitemap.xml` resolve to the same index and do not represent additional content pages.

Captured titles, headings, canonicals, main text, internal/external anchor links, FAQs, IMG/source/srcset references, Elementor gallery data attributes, inline/background references, schema primary images and sitemap image references. The sitemap contains 89 page/image occurrences. Original/lightbox file references were recorded without requesting image files. No image bytes, CSS files, PDFs or other binary assets were downloaded. WordPress admin, media binaries, fragments and dynamic search queries were outside the page crawl.

The web fetch tool initially could not read some URLs; approved direct HTML GETs resolved those failures. No public HTML page remains inaccessible. This does not establish image-file accessibility or unpublished WordPress completeness. Owner-side export records and hidden/AJAX-only media remain outside coverage.

## Site structure

The primary menu links Places to Visit/home; Nashik → Trimbakeshwar → two named religious institutions; Chhatrapati Sambhaji Nagar → Verul and Daulatabad Village; Nagpur → Umred and Kuhi. Repeated responsive menu/footer links are not separate records.

Homepage sections include recent updates, Temples, Forts, Caves and a Lake card. `/all-updates/` links a broader attraction set; district and nested subarea listings expose additional pages. About, Policy, Terms, Disclaimer and Contact are utility pages. Their content is preserved as evidence; no policy replacement or tourism-entity import is proposed.

## Existing Interests, not old categories

| Old discovery/category | Existing target | Decision |
| --- | --- | --- |
| Temples | `/explore/sacred-spiritual` | Map individual POIs to the existing Interest. |
| Forts | `/explore/forts-heritage` | Add history/nature only when intrinsic and supported. |
| Caves | `/explore/ancient-caves` | Existing Ellora keeps its established additional Interests. |
| Lakes/parks/landscapes | `/explore/nature-hills` | No separate Lakes taxonomy or new Experiences page. |
| All Updates/home discovery | `/destinations` | Discovery index, not a new editorial entity. |
| Standalone culture/food narrative | DiscoveryStory and existing Culture/Food Interests | None found. Generic listing FAQs do not become Stories. |

All nine existing Interests remain intact, including history-architecture, wildlife-forests, beaches-coast, culture-traditions and food-local-flavours. Broad sanctuary wording in Umred metadata does not justify a protected-area record or Safari inventory.

## Proposed Destinations

All six are proposed CREATE candidates because the local public catalogue has no published Destination. Owner scope and production/Admin collision review are required first.

| Record | Old page / proposed name | District | Evidence/scope |
| --- | --- | --- | --- |
| C010 | [Daulatabad](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/daulatabad-village/) | Chhatrapati Sambhajinagar | Village overview with explicit district and linked fort. |
| C012 | [Khuldabad](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/khuldabad/) | Chhatrapati Sambhajinagar | Old tehsil listing links Bhadra Maruti. Confirm intended Destination scope. |
| C016 | [Verul](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/) | Chhatrapati Sambhajinagar | Village overview explicitly identifies Khuldabad tehsil. Flatten to District -> Verul; do not nest Destinations. |
| C027 | [Kuhi](https://maharashtratouristplaces.in/nagpur/kuhi/) | Nagpur | Tehsil listing, not proof that the Ambhora temple is in Kuhi town. Keep temple district-level pending planning-area decision. |
| C030 | [Umred](https://maharashtratouristplaces.in/nagpur/umred/) | Nagpur | Old tehsil listing and all four attraction descriptions support Umred/Nagpur. Town versus wider planning-area scope needs owner review. |
| C036 | [Trimbakeshwar](https://maharashtratouristplaces.in/nashik/trimbakeshwar/) | Nashik | Listing mixes Trimbak town and wider tehsil. Town temples supported; Harihar parent held for review. |

Verul's mention of Khuldabad tehsil does not create Destination nesting. Harihar Fort is grouped under Trimbakeshwar tehsil but is near Harshewadi/Nirgudpada; its Destination stays blank. Chaitanyeshwar Temple is in Ambhora within Kuhi tehsil; its Destination also stays blank. Both retain supported districts and valid district-level Place proposals.

## Places and collisions

| Record | Old page / canonical name | District | Proposed Destination | Action | Slug |
| --- | --- | --- | --- | --- | --- |
| C009 | [Bibi Ka Maqbara](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/bibi-ka-maqbara/) | Chhatrapati Sambhajinagar | District-level | CREATE | `bibi-ka-maqbara` |
| C011 | [Devgiri-Daulatabad Fort](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/daulatabad-village/daulatabad-fort/) | Chhatrapati Sambhajinagar | Daulatabad | ENRICH_EXISTING | `devgiri-daulatabad-fort` |
| C013 | [Shree Bhadra Maruti Temple](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/khuldabad/shree-bhadra-maruti-mandir/) | Chhatrapati Sambhajinagar | Khuldabad | CREATE | `shree-bhadra-maruti-temple` |
| C014 | [Panchakki Water Mill](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/panchakki-water-mill/) | Chhatrapati Sambhajinagar | District-level | CREATE | `panchakki-water-mill` |
| C017 | [Ahilyabai Holkar Shivalay Tirth Kund](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/ahilyabai-holkar-shivalay-tirth-kund/) | Chhatrapati Sambhajinagar | Verul | CREATE | `ahilyabai-holkar-shivalay-tirth-kund` |
| C018 | [Ellora Caves](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/ellora-caves/) | Chhatrapati Sambhajinagar | Verul | ENRICH_EXISTING | `ellora-caves` |
| C019 | [Shree Laksha Vinayak Ganapati Temple](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/shree-laksha-vinayak-ganapati-temple-shree-kshetra-verul/) | Chhatrapati Sambhajinagar | Verul | CREATE | `shree-laksha-vinayak-ganapati-temple` |
| C020 | [Ghrishneshwar Temple](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/shri-grishneshwar-jyotirlinga/) | Chhatrapati Sambhajinagar | Verul | ENRICH_EXISTING | `ghrishneshwar-temple` |
| C028 | [Shree Chaitanyeshwar Shiv Temple, Ambhora](https://maharashtratouristplaces.in/nagpur/kuhi/shree-chaitanyeshwar-temple/) | Nagpur | District-level | CREATE | `shree-chaitanyeshwar-shiv-temple-ambhora` |
| C029 | [Shri Ganesh Mandir Tekdi](https://maharashtratouristplaces.in/nagpur/shri-ganesh-mandir-tekdi/) | Nagpur | District-level | CREATE | `shri-ganesh-mandir-tekdi` |
| C031 | [Gandhi Sagar Lake, Umred](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | Nagpur | Umred | POSSIBLE_DUPLICATE | `gandhi-sagar-lake-umred` |
| C032 | [Gandhi Sagar Park, Umred](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | Nagpur | Umred | POSSIBLE_DUPLICATE | `gandhi-sagar-park-umred` |
| C033 | [Shree Gajanan Maharaj Devasthan WCL, Umred](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | Nagpur | Umred | CREATE | `shree-gajanan-maharaj-devasthan-wcl-umred` |
| C034 | [Shree Vitthal Rukmini Ganeshrao Maharaj Devasthan, Kawrapeth](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | Nagpur | Umred | CREATE | `shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth` |
| C037 | [Harihar Fort](https://maharashtratouristplaces.in/nashik/trimbakeshwar/harihar-fort/) | Nashik | District-level | CREATE | `harihar-fort` |
| C038 | [Shri Gajanan Maharaj Sansthan, Trimbakeshwar](https://maharashtratouristplaces.in/nashik/trimbakeshwar/shri-gajanan-maharaj-sansthan-trimbkeshwar/) | Nashik | Trimbakeshwar | CREATE | `shri-gajanan-maharaj-sansthan-trimbakeshwar` |
| C039 | [Trimbakeshwar Temple](https://maharashtratouristplaces.in/nashik/trimbakeshwar/trimbakeshwar-jyotirlinga-temple/) | Nashik | Trimbakeshwar | ENRICH_EXISTING | `trimbakeshwar-temple` |

The four ENRICH_EXISTING aliases are Daulatabad/Devgiri-Daulatabad, Grishneshwar/Ghrishneshwar, Ellora and Trimbakeshwar/Jyotirlinga. Keep existing canonical slugs and curated descriptions. Do not create alternate-spelling Places or attach existing district-only Places to proposed Destinations without review.

Gandhi Sagar Lake and Park have separate URLs, text, addresses and galleries but need a boundary/identity review. POSSIBLE_DUPLICATE records the unresolved relationship, not an instruction to merge. The Kawrapeth Vitthal-Rukmini temple is in Nagpur, distinct from the curated Pandharpur temple in Solapur. Gajanan Maharaj institutions in Trimbakeshwar and WCL Umred are separate local sites. Nearby/onsite shrines mentioned inside descriptions remain contextual content rather than automatic extra Places.

## Empty and unresolved areas

Eight HTTP-200 placeholders have no main tourism text: Mumbai, Pune, Amravati, Bhandara, Chandrapur, Gondia, Wardha and Soegaon. Six named districts match the canonical registry; empty content should not be imported. Mumbai cannot be assigned to Mumbai City versus Mumbai Suburban from its empty page. Soegaon has no supported Destination content. No geographic relationship was fabricated from these placeholders.

## Content and later verification

The content CSV records title/URL, proposed entity/geography/name/slug/path, existing match/action, short summary, full About text for all 17 Places, address, hours, entry claims, duration, best-time claims, travel/railway/airport evidence and JSON FAQs. `observed_on` is retrieval date; every record is OLD_SITE_UNVERIFIED.

There are 142 raw FAQ occurrences, reduced to 140 exact question/answer pairs within pages. Of these, 107 belong to Place pages and 31 to the Umred pilot. Two repeated Forts-category FAQ occurrences remain in raw evidence but are not duplicated in CSV. Cross-page/template FAQ wording needs editorial review.

All 17 Places contain potentially volatile operational claims. Check fees, hours, fares/routes/frequency, travel distances/times, parking, photography/drone/access rules, WCL permission, monsoon safety, lodging/meal claims and review counts later with responsible authorities. Historical chronology and religious claims also need source/editorial review. Do not promote rating widgets, unsupported superlatives, miracle claims, relative ages or currentness assertions to verified factual copy. Never fill `visitor_info_verified_at` with the crawl date.

## Images

237 exact image-reference URLs are represented by 486 page/URL occurrences, grouped into 124 approximate filename families. These include encoded/scheme alternatives and WordPress resized versions. Twenty-four families appear on multiple pages. Neither URL counts nor families prove the number of distinct photographs.

All images are OWNER_CONFIRMATION_REQUIRED. No license or ownership was cleared. Roles derive from detail-gallery/primary-image evidence, with explicit Umred hero-candidate adjustments recorded in notes. Related-card imagery stays associated with the depicted Place rather than the source-page entity. Three Destination hero families are identifiable from metadata: Umred, Kuhi and Trimbakeshwar. No dedicated Destination gallery is established. Other Destination hero/gallery material is missing or requires owner selection.

Dimensions are page declarations only. Some URLs contain zero-width characters; preserve the exact reference and safely encode it in a later approved retrieval. `-1` upload suffixes are only possible duplicate-upload clues. No image hashes or perceptual comparisons were performed. Visual identity, resolution/integrity, creator, permission, attribution and exact-entity specificity must be checked before upload.

## CSV conventions

- Content: one row per discovered public HTML URL, including skipped indexes and placeholders. Actions are proposals; REVIEW_REQUIRED is a separate state and never import authorization.
- Blank fields mean not captured/not applicable, not verified absence. New proposed slugs mirror existing `slugify`; the server must resolve collisions later. Matches retain curated slugs.
- FAQ/other-info/source-reference JSON cells retain source evidence. Whole archived railway/airport answers require concise field review before submission. Old passages are not approved copy.
- Images: one row per source page + exact URL. Discovery methods merge within that key. Family IDs link variants/repeated-page usage. Every relationship is explicit or UNKNOWN, and every role uses a requested enum value.
- Associations describe proposed entity relationships, not copyright ownership. Blank alt/caption/dimension cells mean no declaration for that particular reference; another family variant may carry one.

## Complete URL register

| Record | Old URL | Classification | Content | Action |
| --- | --- | --- | --- | --- |
| C001 | [/](https://maharashtratouristplaces.in/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C002 | [/about/](https://maharashtratouristplaces.in/about/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C003 | [/all-updates/](https://maharashtratouristplaces.in/all-updates/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C004 | [/amravati/](https://maharashtratouristplaces.in/amravati/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C005 | [/bhandara/](https://maharashtratouristplaces.in/bhandara/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C006 | [/caves/](https://maharashtratouristplaces.in/caves/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C007 | [/chandrapur/](https://maharashtratouristplaces.in/chandrapur/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C008 | [/chhatrapati-sambhaji-nagar/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/) | DISTRICT | CONTENT | ENRICH_EXISTING |
| C009 | [/chhatrapati-sambhaji-nagar/bibi-ka-maqbara/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/bibi-ka-maqbara/) | PLACE | CONTENT | CREATE |
| C010 | [/chhatrapati-sambhaji-nagar/daulatabad-village/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/daulatabad-village/) | DESTINATION | CONTENT | CREATE |
| C011 | [/chhatrapati-sambhaji-nagar/daulatabad-village/daulatabad-fort/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/daulatabad-village/daulatabad-fort/) | PLACE | CONTENT | ENRICH_EXISTING |
| C012 | [/chhatrapati-sambhaji-nagar/khuldabad/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/khuldabad/) | DESTINATION | CONTENT | CREATE |
| C013 | [/chhatrapati-sambhaji-nagar/khuldabad/shree-bhadra-maruti-mandir/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/khuldabad/shree-bhadra-maruti-mandir/) | PLACE | CONTENT | CREATE |
| C014 | [/chhatrapati-sambhaji-nagar/panchakki-water-mill/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/panchakki-water-mill/) | PLACE | CONTENT | CREATE |
| C015 | [/chhatrapati-sambhaji-nagar/soegaon/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/soegaon/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C016 | [/chhatrapati-sambhaji-nagar/verul/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/) | DESTINATION | CONTENT | CREATE |
| C017 | [/chhatrapati-sambhaji-nagar/verul/ahilyabai-holkar-shivalay-tirth-kund/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/ahilyabai-holkar-shivalay-tirth-kund/) | PLACE | CONTENT | CREATE |
| C018 | [/chhatrapati-sambhaji-nagar/verul/ellora-caves/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/ellora-caves/) | PLACE | CONTENT | ENRICH_EXISTING |
| C019 | [/chhatrapati-sambhaji-nagar/verul/shree-laksha-vinayak-ganapati-temple-shree-kshetra-verul/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/shree-laksha-vinayak-ganapati-temple-shree-kshetra-verul/) | PLACE | CONTENT | CREATE |
| C020 | [/chhatrapati-sambhaji-nagar/verul/shri-grishneshwar-jyotirlinga/](https://maharashtratouristplaces.in/chhatrapati-sambhaji-nagar/verul/shri-grishneshwar-jyotirlinga/) | PLACE | CONTENT | ENRICH_EXISTING |
| C021 | [/contact/](https://maharashtratouristplaces.in/contact/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C022 | [/disclaimer/](https://maharashtratouristplaces.in/disclaimer/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C023 | [/forts/](https://maharashtratouristplaces.in/forts/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C024 | [/gondia/](https://maharashtratouristplaces.in/gondia/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C025 | [/mumbai/](https://maharashtratouristplaces.in/mumbai/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C026 | [/nagpur/](https://maharashtratouristplaces.in/nagpur/) | DISTRICT | CONTENT | ENRICH_EXISTING |
| C027 | [/nagpur/kuhi/](https://maharashtratouristplaces.in/nagpur/kuhi/) | DESTINATION | CONTENT | CREATE |
| C028 | [/nagpur/kuhi/shree-chaitanyeshwar-temple/](https://maharashtratouristplaces.in/nagpur/kuhi/shree-chaitanyeshwar-temple/) | PLACE | CONTENT | CREATE |
| C029 | [/nagpur/shri-ganesh-mandir-tekdi/](https://maharashtratouristplaces.in/nagpur/shri-ganesh-mandir-tekdi/) | PLACE | CONTENT | CREATE |
| C030 | [/nagpur/umred/](https://maharashtratouristplaces.in/nagpur/umred/) | DESTINATION | CONTENT | CREATE |
| C031 | [/nagpur/umred/gandhi-sagar-lake/](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-lake/) | PLACE | CONTENT | POSSIBLE_DUPLICATE |
| C032 | [/nagpur/umred/gandhi-sagar-park/](https://maharashtratouristplaces.in/nagpur/umred/gandhi-sagar-park/) | PLACE | CONTENT | POSSIBLE_DUPLICATE |
| C033 | [/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/](https://maharashtratouristplaces.in/nagpur/umred/shree-gajanan-maharaj-devasthan-w-c-l-picnic-spot/) | PLACE | CONTENT | CREATE |
| C034 | [/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/](https://maharashtratouristplaces.in/nagpur/umred/shree-vitthal-rukmini-ganeshrao-maharaj-devasthan-kawrapeth/) | PLACE | CONTENT | CREATE |
| C035 | [/nashik/](https://maharashtratouristplaces.in/nashik/) | DISTRICT | CONTENT | ENRICH_EXISTING |
| C036 | [/nashik/trimbakeshwar/](https://maharashtratouristplaces.in/nashik/trimbakeshwar/) | DESTINATION | CONTENT | CREATE |
| C037 | [/nashik/trimbakeshwar/harihar-fort/](https://maharashtratouristplaces.in/nashik/trimbakeshwar/harihar-fort/) | PLACE | CONTENT | CREATE |
| C038 | [/nashik/trimbakeshwar/shri-gajanan-maharaj-sansthan-trimbkeshwar/](https://maharashtratouristplaces.in/nashik/trimbakeshwar/shri-gajanan-maharaj-sansthan-trimbkeshwar/) | PLACE | CONTENT | CREATE |
| C039 | [/nashik/trimbakeshwar/trimbakeshwar-jyotirlinga-temple/](https://maharashtratouristplaces.in/nashik/trimbakeshwar/trimbakeshwar-jyotirlinga-temple/) | PLACE | CONTENT | ENRICH_EXISTING |
| C040 | [/policy/](https://maharashtratouristplaces.in/policy/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C041 | [/pune/](https://maharashtratouristplaces.in/pune/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |
| C042 | [/temples/](https://maharashtratouristplaces.in/temples/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C043 | [/terms/](https://maharashtratouristplaces.in/terms/) | OTHER / REVIEW REQUIRED | CONTENT | SKIP |
| C044 | [/wardha/](https://maharashtratouristplaces.in/wardha/) | OTHER / REVIEW REQUIRED | EMPTY_PLACEHOLDER | SKIP |

## Reproducibility

Evidence JSON retains source content/link/image declarations, sitemap/robots responses, crawl closure, source-only canonical identities, the local public catalogue and reviewed mapping data. `tools/` contains read-only discovery, target capture, offline mapping, CSV authoring and validation. No tool imports database content.

The CSVs were authored with artifact-tool ranges, RFC 4180 quoting and exact CSV re-import verification. External discovery is an explicit read operation and must not run as part of production deployment. No image retrieval, import, publishing, schema migration or cutover was performed.


## Subsequent Umred textual pilot — 3 October 2026

The inventory above records the original audit and planning state. The separately authorized Umred text pilot has now created a draft Destination, two temple drafts and 15 Place FAQs in the local development database. Lake/park remain unresolved and uncreated; all image rights remain pending with mapping only. No overview was fabricated and nothing was published. See [Umred pilot result](umred-pilot-result.md) for canonical local IDs, FAQ/image ownership, execution, verification and remaining owner decisions. Remaining-site and image migration have not begun.
