import json
from pathlib import Path

from app.core.slug import slugify
from app.data.discovery_stories import CURATED_DISCOVERY_STORIES
from app.data.places import CURATED_PLACES_V1


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "frontend" / "src" / "data" / "discovery-media-manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_media_manifest_matches_curated_place_and_story_identities():
    manifest = _manifest()
    place_identities = {
        f"{record.district_slug}/{record.slug or slugify(record.name, max_length=180)}"
        for record in CURATED_PLACES_V1
    }
    story_identities = {
        record.slug or slugify(record.title, max_length=200)
        for record in CURATED_DISCOVERY_STORIES
    }

    assert set(manifest["places"]) == place_identities
    assert set(manifest["stories"]) == story_identities


def test_current_curated_records_are_honestly_classified_as_fallbacks():
    manifest = _manifest()
    assert all(record.image_url is None for record in CURATED_PLACES_V1)
    assert all(record.image_url is None for record in CURATED_DISCOVERY_STORIES)
    assert all(record["status"] == "FALLBACK" for record in manifest["places"].values())
    assert all(record["status"] == "FALLBACK" for record in manifest["stories"].values())


def test_manifest_assets_stay_in_public_images_and_have_rights_metadata():
    manifest = _manifest()
    assets = [manifest["globalFallback"], *manifest["interests"].values()]
    for asset in assets:
        assert asset["asset"].startswith("/images/")
        assert (PROJECT_ROOT / "frontend" / "public" / asset["asset"].removeprefix("/")).is_file()
        provenance = manifest["provenance"][asset["provenanceId"]]
        assert provenance["source"]
        assert provenance["creator"]
        assert provenance["usageBasis"]
        assert provenance["license"]
        assert provenance["documentary"] is False
