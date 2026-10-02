import unittest
import urllib.parse
import uuid

from sqlalchemy import delete, select

from app.data.interests import MAHARASHTRA_INTERESTS_V1
from app.database import SessionLocal
from app.models.destination import Destination, District
from app.models.place import Interest, Place, SpiritualTradition, place_interests
from app.services import destination_service, place_service
from tests.test_auth_integration import request_json


class PlaceFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suffix = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            cls.pune = db.scalar(select(District).where(District.slug == "pune"))
            cls.satara = db.scalar(select(District).where(District.slug == "satara"))
            cls.ancient = db.scalar(select(Interest).where(Interest.slug == "ancient-caves"))
            cls.history = db.scalar(select(Interest).where(Interest.slug == "history-architecture"))
            destination = destination_service.create_destination(
                db,
                district=cls.pune,
                name=f"Place Foundation Destination {cls.suffix}",
            )
            hidden_destination = destination_service.create_destination(
                db,
                district=cls.pune,
                name=f"Hidden Place Destination {cls.suffix}",
                is_active=False,
            )
            active = place_service.create_place(
                db,
                district=cls.pune,
                destination=destination,
                name=f"Canonical Cave {cls.suffix}",
                short_description="Controlled place foundation test record.",
                spiritual_tradition=SpiritualTradition.BUDDHIST,
                interests=[cls.ancient, cls.history, cls.ancient],
                is_featured=True,
            )
            district_only = place_service.create_place(
                db,
                district=cls.pune,
                name=f"District Only Place {cls.suffix}",
                interests=[cls.history],
            )
            inactive = place_service.create_place(
                db,
                district=cls.pune,
                name=f"Inactive Place {cls.suffix}",
                interests=[cls.ancient],
                is_active=False,
            )
            hidden_parent = place_service.create_place(
                db,
                district=cls.pune,
                destination=hidden_destination,
                name=f"Hidden Parent Place {cls.suffix}",
                interests=[cls.ancient],
            )
            db.commit()
            cls.destination_id = destination.id
            cls.destination_slug = destination.slug
            cls.hidden_destination_id = hidden_destination.id
            cls.place_ids = [active.id, district_only.id, inactive.id, hidden_parent.id]
            cls.active_slug = active.slug
            cls.active_name = active.name
            cls.district_only_slug = district_only.slug
            cls.inactive_slug = inactive.slug
            cls.hidden_parent_slug = hidden_parent.slug

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            db.execute(delete(place_interests).where(place_interests.c.place_id.in_(cls.place_ids)))
            db.execute(delete(Place).where(Place.id.in_(cls.place_ids)))
            db.execute(
                delete(Destination).where(
                    Destination.id.in_([cls.destination_id, cls.hidden_destination_id])
                )
            )
            db.commit()

    def test_interest_taxonomy_is_seeded_and_public(self) -> None:
        code, response = request_json("GET", "/interests")
        self.assertEqual(code, 200, response)
        expected = [slug for _, slug, _ in MAHARASHTRA_INTERESTS_V1]
        self.assertEqual([item["slug"] for item in response["items"]], expected)
        self.assertTrue(all(item["path"].startswith("/explore/") for item in response["items"]))

    def test_place_relationships_and_duplicate_classification_protection(self) -> None:
        with SessionLocal() as db:
            place = db.scalar(select(Place).where(Place.slug == self.active_slug))
            self.assertEqual(place.district.slug, "pune")
            self.assertEqual(place.destination.slug, self.destination_slug)
            self.assertEqual({item.slug for item in place.interests}, {"ancient-caves", "history-architecture"})
            self.assertEqual(len(place.interests), 2)
            self.assertEqual(place.spiritual_tradition, SpiritualTradition.BUDDHIST)

            district_only = db.scalar(select(Place).where(Place.slug == self.district_only_slug))
            self.assertIsNone(district_only.destination)
            self.assertIsNone(district_only.spiritual_tradition)

    def test_slug_collision_is_scoped_to_district(self) -> None:
        with SessionLocal() as db:
            first = place_service.create_place(
                db, district=self.pune, name=f"Scoped Place {self.suffix}"
            )
            collision = place_service.create_place(
                db, district=self.pune, name=f"Scoped--Place {self.suffix}"
            )
            other_district = place_service.create_place(
                db, district=self.satara, name=f"Scoped Place {self.suffix}"
            )
            self.assertEqual(collision.slug, f"{first.slug}-2")
            self.assertEqual(other_district.slug, first.slug)
            db.rollback()

    def test_invalid_place_relationship_and_name_are_rejected(self) -> None:
        with SessionLocal() as db:
            destination = db.get(Destination, self.destination_id)
            pune = db.get(District, self.pune.id)
            satara = db.get(District, self.satara.id)
            with self.assertRaises(ValueError):
                place_service.create_place(db, district=pune, destination=destination, name=" ")
            with self.assertRaises(ValueError):
                place_service.create_place(
                    db,
                    district=satara,
                    destination=destination,
                    name=f"Wrong District {self.suffix}",
                )
            db.rollback()

    def test_public_place_detail_uses_canonical_slugs_and_safe_fields(self) -> None:
        code, place = request_json("GET", f"/places/pune/{self.active_slug}")
        self.assertEqual(code, 200, place)
        self.assertEqual(place["path"], f"/places/pune/{self.active_slug}")
        self.assertEqual(place["district"]["slug"], "pune")
        self.assertEqual(place["destination"]["slug"], self.destination_slug)
        self.assertEqual(place["spiritual_tradition"], "BUDDHIST")
        self.assertNotIn("id", place)
        self.assertNotIn("is_active", place)
        self.assertNotIn("created_at", place)

        code, district_only = request_json("GET", f"/places/pune/{self.district_only_slug}")
        self.assertEqual(code, 200, district_only)
        self.assertIsNone(district_only["destination"])
        self.assertIsNone(district_only["spiritual_tradition"])

    def test_search_and_combined_filters(self) -> None:
        query = urllib.parse.quote(self.active_name[:12])
        code, searched = request_json("GET", f"/places?q={query}")
        self.assertEqual(code, 200, searched)
        self.assertIn(self.active_slug, {item["slug"] for item in searched["items"]})

        code, filtered = request_json(
            "GET",
            f"/places?district=pune&destination={self.destination_slug}&interest=ancient-caves",
        )
        self.assertEqual(code, 200, filtered)
        self.assertEqual({item["slug"] for item in filtered["items"]}, {self.active_slug})

        code, district = request_json("GET", "/places?district=pune&interest=history-architecture")
        self.assertEqual(code, 200, district)
        self.assertTrue({self.active_slug, self.district_only_slug}.issubset({item["slug"] for item in district["items"]}))

    def test_inactive_place_and_inactive_destination_are_not_discoverable(self) -> None:
        code, places = request_json("GET", "/places?district=pune&interest=ancient-caves")
        self.assertEqual(code, 200, places)
        slugs = {item["slug"] for item in places["items"]}
        self.assertNotIn(self.inactive_slug, slugs)
        self.assertNotIn(self.hidden_parent_slug, slugs)

        code, inactive = request_json("GET", f"/places/pune/{self.inactive_slug}")
        self.assertEqual(code, 404, inactive)
        code, hidden_parent = request_json("GET", f"/places/pune/{self.hidden_parent_slug}")
        self.assertEqual(code, 404, hidden_parent)
        code, missing = request_json("GET", "/places/pune/not-a-real-place")
        self.assertEqual(code, 404, missing)

    def test_unified_destination_search_includes_places(self) -> None:
        query = urllib.parse.quote(self.active_name[:12])
        code, legacy_results = request_json("GET", f"/destinations/search?q={query}")
        self.assertEqual(code, 200, legacy_results)
        self.assertNotIn(self.active_slug, {item["slug"] for item in legacy_results["items"]})

        code, results = request_json(
            "GET", f"/destinations/search?q={query}&include_places=true"
        )
        self.assertEqual(code, 200, results)
        match = next(item for item in results["items"] if item["slug"] == self.active_slug)
        self.assertEqual(match["kind"], "PLACE")
        self.assertEqual(match["district_slug"], "pune")
        self.assertEqual(match["destination_slug"], self.destination_slug)


if __name__ == "__main__":
    unittest.main(verbosity=2)
