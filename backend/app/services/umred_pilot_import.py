"""Operator-run, text-only Umred pilot. Never runs at startup or publishes records."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.slug import slugify
from app.models import Destination, District, Interest, Place, PlaceFAQ, SpiritualTradition


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "umred_pilot_v1.json"
SOURCE = "Owner's old Maharashtra Tourist Places website; OLD_SITE_UNVERIFIED. Reconfirm visitor information locally."


def load_pilot() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def identity(value: str) -> str:
    """Compare known spelling/punctuation variants without choosing a new slug."""
    value = re.sub(r"\bw\s*[.]?\s*c\s*[.]?\s*l\b", "wcl", value.casefold())
    value = re.sub(r"\b(shri|sri)\b", "shree", value)
    value = value.replace("kawarapeth", "kawrapeth")
    return slugify(value)


def _matches(items: list, record: dict, district_id: int) -> tuple[list, list]:
    keys = {identity(v) for v in (record["name"], record["slug"], *record.get("aliases", []))}
    exact, possible = [], []
    for item in items:
        values = {identity(item.name), identity(item.slug)}
        if item.district_id == district_id and values & keys:
            exact.append(item)
            continue
        words = identity(item.name + " " + item.slug)
        if record["slug"] == "umred":
            suspect = item.district_id == district_id and "umred" in words.split("-")
        elif record["record_id"] == "C033":
            suspect = "gajanan" in words and (item.district_id == district_id or "umred" in words)
        else:
            suspect = "vitthal" in words and "rukmini" in words and (item.district_id == district_id or "kawrapeth" in words)
        if suspect:
            possible.append(item)
    return exact, possible


def import_umred(db: Session) -> dict:
    """Preflight identities in every lifecycle state; caller commits or rolls back."""
    data = load_pilot()
    district = db.scalar(select(District).where(District.slug == "nagpur").with_for_update())
    if district is None or not district.is_active:
        raise ValueError("Existing active canonical Nagpur District is required")
    interests = {v.slug: v for v in db.scalars(select(Interest))}
    for record in data["places"]:
        for slug in record["interest_slugs"]:
            if slug not in interests or not interests[slug].is_active:
                raise ValueError(f"Existing active Interest required: {slug}")
        if slugify(record["name"]) != record["slug"]:
            raise ValueError("Reviewed slug must follow existing canonical slug rules")
        questions = [identity(f["question"]) for f in record["faqs"]]
        if len(questions) != len(set(questions)):
            raise ValueError("Duplicate source FAQ question")

    destinations = list(db.scalars(select(Destination).with_for_update()))
    places = list(db.scalars(select(Place).with_for_update()))
    exact, possible = _matches(destinations, data["destination"], district.id)
    events = [{"record_id": v["record_id"], "action": "REVIEW", "decision": "POSSIBLE_DUPLICATE", "reason": v["reason"]} for v in data["held"]]
    if len(exact) > 1 or possible:
        events.append({"record_id": "C030", "action": "REVIEW", "reason": "Ambiguous Umred Destination identity", "matching_ids": [v.id for v in exact + possible]})
        events.extend({"record_id": v["record_id"], "action": "REVIEW", "reason": "Resolve canonical Umred parent first"} for v in data["places"])
        return {"district_id": district.id, "events": events}
    resolved = []
    for record in data["places"]:
        matches, suspects = _matches(places, record, district.id)
        resolved.append((record, matches, suspects))

    destination = exact[0] if exact else None
    if destination is None:
        destination = Destination(district_id=district.id, name="Umred", slug="umred", is_active=False, content_source="MIGRATION")
        db.add(destination)
        db.flush()
        action = "CREATE"
    else:
        action = "SKIP"
    events.append({"record_id": "C030", "action": action, "decision": "CREATE" if action == "CREATE" else "ENRICH_EXISTING", "id": destination.id, "slug": destination.slug, "published": destination.is_active, "reason": "No source overview; no invented summary, FAQs or media. Existing content/state preserved."})

    for record, matches, suspects in resolved:
        if len(matches) > 1 or suspects:
            events.append({"record_id": record["record_id"], "action": "REVIEW", "decision": "REVIEW_REQUIRED", "reason": "Possible spelling/identity collision", "matching_ids": [v.id for v in matches + suspects]})
            continue
        item = matches[0] if matches else None
        if item is not None:
            # Existing Admin/curated content is never implicitly approved for enrichment.
            # Admin edits increase version even for MIGRATION-owned rows.
            events.append({"record_id": record["record_id"], "action": "SKIP", "decision": "ENRICH_EXISTING", "id": item.id, "slug": item.slug, "published": item.is_active, "reason": "Existing record preserved; explicit Admin review required for changes." if item.content_source != "MIGRATION" or item.version != 1 or item.admin_overridden else "Already imported; unchanged", "destination_id": item.destination_id, "faqs": len(item.faqs)})
            continue
        item = Place(district_id=district.id, destination_id=destination.id, name=record["name"], slug=record["slug"], **record["fields"], spiritual_tradition=SpiritualTradition.HINDU, interests=[interests[v] for v in record["interest_slugs"]], visitor_info_source=SOURCE, visitor_info_source_url=record["source_url"], visitor_info_verified_at=None, is_active=False, content_source="MIGRATION")
        item.faqs = [PlaceFAQ(question=v["question"], answer=v["answer"], display_order=index, is_active=True) for index, v in enumerate(record["faqs"])]
        db.add(item)
        db.flush()
        events.append({"record_id": record["record_id"], "action": "CREATE", "decision": "CREATE", "id": item.id, "slug": item.slug, "destination_id": destination.id, "published": False, "faqs": len(item.faqs), "reason": "Source text imported as draft; linked Destination lacks publishable overview."})
    return {"dataset": "umred-text-v1", "district_id": district.id, "destination_id": destination.id, "events": sorted(events, key=lambda v: v["record_id"])}
