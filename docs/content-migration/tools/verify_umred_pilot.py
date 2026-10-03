"""Read-only source, scope and local database verification after the Umred pilot."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / "backend"))

from fastapi import HTTPException
from sqlalchemy import select
import app.models
from app.database import SessionLocal
from app.models import District, Destination, Place, Interest, DiscoveryStory, PublicMediaAsset, PlaceMedia, DestinationMedia, PlaceFAQ, DestinationFAQ
from app.services import destination_service, place_service
from app.services.umred_pilot_import import load_pilot


def main():
    before = json.loads((ROOT / "evidence/umred-before.json").read_text(encoding="utf-8"))
    data = load_pilot()
    pages = {v["url"]: v for v in json.loads((ROOT / "evidence/old-site-pages.json").read_text(encoding="utf-8"))}
    checks = []

    def check(label, value):
        if not value:
            raise AssertionError(label)
        checks.append(label)

    with SessionLocal() as db:
        models = (District, Destination, Place, Interest, DiscoveryStory, PublicMediaAsset, PlaceMedia, DestinationMedia, PlaceFAQ, DestinationFAQ)
        after = {}
        for model in models:
            after[model.__name__] = [{c.name: str(getattr(v, c.name)) for c in model.__table__.columns} for v in db.scalars(select(model).order_by(model.id))]
        after["PlaceInterestMembership"] = {str(v.id): sorted(i.id for i in v.interests) for v in db.scalars(select(Place))}
        for model in models:
            original = before[model.__name__]
            current = {v["id"]: v for v in after[model.__name__]}
            check(f"Original {model.__name__} rows unchanged", all(current.get(v["id"]) == v for v in original))
        check("Original Interest membership unchanged", all(after["PlaceInterestMembership"][key] == value for key, value in before["PlaceInterestMembership"].items()))
        for model in (District, Interest, DiscoveryStory, PublicMediaAsset, PlaceMedia, DestinationMedia, DestinationFAQ):
            check(f"No additional {model.__name__} records", before[model.__name__] == after[model.__name__])
        check("Exactly one Destination, two Places and 15 FAQs added", all(len(after[k]) - len(before[k]) == n for k, n in (("Destination", 1), ("Place", 2), ("PlaceFAQ", 15))))
        parent = db.scalar(select(Destination).where(Destination.slug == "umred"))
        check("No generated Umred overview/summary", parent.description is None and parent.short_summary is None)
        for record in data["places"]:
            item = db.scalar(select(Place).where(Place.slug == record["slug"]))
            check(f"{record['record_id']} source FAQs unchanged", record["faqs"] == pages[record["source_url"]]["faqs"])
            source_blocks = {v["text"] for v in pages[record["source_url"]]["content_blocks"]}
            check(f"{record['record_id']} source description captured verbatim", all(line in source_blocks for line in record["fields"]["description"].splitlines()))
            check(f"{record['record_id']} canonical relationship and draft state", item.destination_id == parent.id and item.district_id == parent.district_id and not item.is_active and item.visitor_info_verified_at is None)
            check(f"{record['record_id']} no media assignment", item.image_url is None and item.media_asset_id is None)
            check(f"{record['record_id']} source FAQ ownership/order", record["faqs"] == [{"question": f.question, "answer": f.answer} for f in item.faqs] and [f.display_order for f in item.faqs] == list(range(len(item.faqs))))
            try:
                place_service.get_place(db, "nagpur", item.slug)
            except HTTPException as error:
                check(f"{record['record_id']} draft public detail excluded", error.status_code == 404)
            else:
                raise AssertionError("Draft Place exposed")
        try:
            destination_service.get_destination(db, "nagpur", "umred")
        except HTTPException as error:
            check("Draft Umred public detail excluded", error.status_code == 404)
        else:
            raise AssertionError("Incomplete Destination exposed")
        check("Drafts absent from public search", not destination_service.search(db, "Umred", 50, include_places=True, include_stories=True).items)
        for v in data["held"]:
            check(f"{v['record_id']} unresolved entity not created", db.scalar(select(Place).where(Place.slug == v["slug"])) is None)
    result = {"checks": checks, "passed": len(checks), "snapshot": after}
    (ROOT / "evidence/umred-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(checks)} source/scope/local-database checks passed")


if __name__ == "__main__":
    main()
