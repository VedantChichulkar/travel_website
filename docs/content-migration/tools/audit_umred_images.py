"""Download inventory originals to ignored, non-public staging and audit bytes only."""
import csv
import hashlib
import io
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/content-migration"
STAGING = ROOT / "migration-staging/umred/images"
MAX_BYTES = 32 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 30_000_000


def request_url(value):
    parsed = urlsplit(value)
    if parsed.hostname != "maharashtratouristplaces.in" or not parsed.path.startswith("/wp-content/uploads/"):
        raise ValueError("Only inventoried old-site upload URLs are allowed")
    return urlunsplit(("https", parsed.netloc, quote(unquote(parsed.path), safe="/"), parsed.query, ""))


def inspect_bytes(data):
    result = {"file_size": len(data), "checksum": hashlib.sha256(data).hexdigest(), "decoding_succeeds": False}
    try:
        with Image.open(io.BytesIO(data)) as source:
            result["format"] = source.format
            source.verify()
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            result["exif_present"] = bool(source.getexif()) or bool(source.info.get("exif"))
            result["transparency"] = "transparency" in source.info or ("A" in source.getbands() and source.getchannel("A").getextrema()[0] < 255)
            image = ImageOps.exif_transpose(source)
            width, height = image.size
            result.update(width=width, height=height, aspect_ratio=round(width / height, 5), decoding_succeeds=True)
            gray = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).getdata())
            bits = [gray[y * 9 + x] > gray[y * 9 + x + 1] for y in range(8) for x in range(8)]
            result["dhash"] = f"{sum(int(b) << i for i, b in enumerate(bits)):016x}"
            result["normalized_pixel_sha256"] = hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()
            ratio = width / height
            if width < 640 or height < 360:
                quality, role = "LOW_QUALITY", "THUMBNAIL_ONLY"
            elif not .5 <= ratio <= 3:
                quality, role = "REVIEW_REQUIRED", "REVIEW_REQUIRED"
            elif width >= 1280 and height >= 720 and 1.2 <= ratio <= 2.2:
                quality, role = "GOOD", "HERO_CANDIDATE"
            else:
                quality, role = "ACCEPTABLE", "GALLERY_CANDIDATE"
            result.update(quality_status=quality, recommended_role=role, processing_dimension_minimum_met=width >= 640 and height >= 360, production_size_limit_met=len(data) <= 8 * 1024 * 1024)
    except Exception as error:
        result.update(quality_status="UNUSABLE", recommended_role="NOT_RECOMMENDED", decode_error=f"{type(error).__name__}: {error}")
    return result


def stage_family(pair):
    fid, rows = pair
    originals = sorted({u for r in rows for u in json.loads(r["observed_original_candidates_json"])})
    record = rows[0]
    pages = sorted({r["source_page_url"] for r in rows})
    source_page = next((p for p in pages if "/nagpur/umred/" in p), pages[0])
    owner = record["associated_place"] or "Umred"
    group = "Umred Destination" if owner == "Umred" else "WCL Temple" if "WCL" in owner else "Kawrapeth Temple" if "Ganeshrao" in owner else "Gandhi Sagar Lake" if "Lake" in owner else "Gandhi Sagar Park" if "Park" in owner else "Unknown/Ambiguous"
    item = dict(family_id=fid, source_page=source_page, source_pages=pages, source_url=originals[0] if originals else record["original_image_url_path"], original_filename=record["filename_family_key"].rsplit("/", 1)[-1], proposed_entity=owner, group=group, proposed_role=record["proposed_image_role"], source_family_key=record["filename_family_key"], source_duplicate_relationship=record["duplicate_relationship"], rights_status=record["rights_provenance_status"], entity_resolution_status="ENTITY_RESOLUTION_REQUIRED" if group in ("Gandhi Sagar Lake", "Gandhi Sagar Park", "Unknown/Ambiguous") else "DRAFT_ENTITY_RESOLVED", owner_confirmation_required="YES", attempts=[], local_staging_reference="", duplicate_status="REVIEW_REQUIRED", duplicate_of="", notes="Subject identity is not verified. Page association is proposed ownership only; no rights inference.")
    # Equivalent encoded spellings are one retrieval, not distinct image candidates.
    urls = list(dict.fromkeys(request_url(u) for u in originals or [item["source_url"]]))
    target = STAGING / f"{fid}.source"
    if target.exists():
        data = target.read_bytes()
        item["migration_status"] = "STAGED_CACHED"
        previous_path = DOCS / "evidence/umred-image-audit.json"
        if previous_path.exists():
            previous = json.loads(previous_path.read_text(encoding="utf-8"))
            old = next((v for v in previous["families"] if v["family_id"] == fid), None)
            if old:
                item["attempts"] = old["attempts"]
    else:
        data = None
        for url in urls:
            try:
                with urlopen(Request(url, headers={"User-Agent": "MaharashtraTouristPlaces-MigrationAudit/1.0"}), timeout=25) as response:
                    if urlsplit(response.url).hostname != "maharashtratouristplaces.in":
                        raise ValueError("Unexpected redirect host")
                    fetched = response.read(MAX_BYTES + 1)
                    if len(fetched) > MAX_BYTES:
                        raise ValueError("Staging download exceeds 32 MiB limit")
                    item["attempts"].append(dict(request_url=url, final_url=response.url, status=response.status, content_type=response.headers.get("Content-Type")))
                    data = fetched
                    target.write_bytes(data)
                    item["migration_status"] = "STAGED"
                    break
            except Exception as error:
                item["attempts"].append(dict(request_url=url, error=f"{type(error).__name__}: {error}"))
        if data is None:
            item.update(migration_status="DOWNLOAD_FAILED", quality_status="REVIEW_REQUIRED", recommended_role="REVIEW_REQUIRED", decoding_succeeds=False)
            return item
    item["local_staging_reference"] = target.relative_to(ROOT).as_posix()
    item.update(inspect_bytes(data))
    return item


def classify_duplicates(items):
    good = [v for v in items if v.get("decoding_succeeds")]
    pairs = []
    for i, a in enumerate(good):
        for b in good[i + 1:]:
            distance = (int(a["dhash"], 16) ^ int(b["dhash"], 16)).bit_count()
            kind = "EXACT_DUPLICATE" if a["checksum"] == b["checksum"] else "LIKELY_VISUAL_DUPLICATE" if distance <= 6 else None
            if kind:
                score_a = (a["width"] * a["height"], a["file_size"])
                score_b = (b["width"] * b["height"], b["file_size"])
                preferred = None if score_a == score_b else (a if score_a > score_b else b)["family_id"]
                pairs.append(dict(a=a["family_id"], b=b["family_id"], classification=kind, dhash_distance=distance, preferred_technical_candidate=preferred, same_normalized_pixels=a["normalized_pixel_sha256"] == b["normalized_pixel_sha256"]))
    for item in good:
        related = [p for p in pairs if item["family_id"] in (p["a"], p["b"])]
        item["duplicate_status"] = "EXACT_DUPLICATE" if any(p["classification"] == "EXACT_DUPLICATE" for p in related) else "LIKELY_VISUAL_DUPLICATE" if related else "UNIQUE"
        item["duplicate_of"] = ";".join(sorted({p["b"] if p["a"] == item["family_id"] else p["a"] for p in related}))
    return pairs


def main():
    rows = list(csv.DictReader((DOCS / "image-migration-inventory.csv").open(encoding="utf-8", newline="")))
    groups = defaultdict(list)
    for row in rows:
        if row["associated_destination_slug"] == "umred":
            groups[row["filename_family_id"]].append(row)
    if len(groups) != 26:
        raise ValueError("Expected exactly 26 inventoried Umred families")
    STAGING.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        items = sorted(pool.map(stage_family, sorted(groups.items())), key=lambda v: (v["group"], v["family_id"]))
    pairs = classify_duplicates(items)
    result = dict(observed_on="2026-10-03", retrieval_scope="One observed original per filename family; equivalent encoded aliases coalesced; resized variants not fetched", staged_files=sum(bool(v["local_staging_reference"]) for v in items), families=items, duplicate_pairs=pairs)
    (DOCS / "evidence/umred-image-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(families=len(items), staged=result["staged_files"], failed=sum(v["migration_status"] == "DOWNLOAD_FAILED" for v in items), exact_pairs=sum(p["classification"] == "EXACT_DUPLICATE" for p in pairs), likely_pairs=sum(p["classification"] == "LIKELY_VISUAL_DUPLICATE" for p in pairs))))


if __name__ == "__main__":
    main()
