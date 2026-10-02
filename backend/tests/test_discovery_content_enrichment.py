import unittest
import uuid

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.destination import Destination, District
from app.models.place import Interest, Place
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user
from tests.test_auth_integration import request_json


class DiscoveryContentEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suffix = uuid.uuid4().hex[:8]
        cls.email = f"rich-discovery-{cls.suffix}@example.com"
        cls.password = "StrongPass123"
        with SessionLocal() as db:
            user = create_user(db, full_name="Rich Discovery Admin", email=cls.email, phone=f"+917{str(uuid.uuid4().int)[-9:]}", password_hash=hash_password(cls.password), role=UserRole.ADMIN)
            db.commit(); cls.user_id = user.id
            cls.district_id = db.scalar(select(District.id).where(District.slug == "nagpur"))
            cls.other_district_id = db.scalar(select(District.id).where(District.slug == "pune"))
            cls.interest_id = db.scalar(select(Interest.id).where(Interest.slug == "nature-hills"))
        code, login = request_json("POST", "/auth/login", {"email": cls.email, "password": cls.password, "portal": "ADMIN"})
        if code != 200: raise AssertionError(login)
        cls.token = login["access_token"]
        cls.destination_ids = []
        cls.place_ids = []

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            for place in db.scalars(select(Place).where(Place.id.in_(cls.place_ids))): place.interests = []
            db.flush()
            if cls.place_ids: db.execute(delete(Place).where(Place.id.in_(cls.place_ids)))
            if cls.destination_ids: db.execute(delete(Destination).where(Destination.id.in_(cls.destination_ids)))
            db.execute(delete(User).where(User.id == cls.user_id)); db.commit()

    def create_destination(self, name: str):
        code, value = request_json("POST", "/admin/discovery/destinations", {
            "district_id": self.district_id, "name": name, "short_summary": "A short destination summary.",
            "description": "A detailed destination overview.",
            "faqs": [{"question": "When should I visit?", "answer": "Use current local guidance.", "display_order": 0, "is_active": True}, {"question": "Hidden?", "answer": "Not public.", "display_order": 1, "is_active": False}],
        }, token=self.token)
        self.assertEqual(code, 201, value); self.destination_ids.append(value["id"])
        code, published = request_json("POST", f"/admin/discovery/destinations/{value['id']}/publish", {"expected_version": value["version"], "reason": "Ready for enrichment test"}, token=self.token)
        self.assertEqual(code, 200, published)
        return published["entity"]

    def create_place(self, destination_id, name: str, *, publish: bool, district_id=None):
        payload = {"district_id": district_id or self.district_id, "destination_id": destination_id, "name": name, "short_description": "Short place summary.", "description": "Detailed place overview.", "interest_ids": [self.interest_id], "address": "Central Nagpur", "opening_hours": "Confirm locally before visiting.", "getting_there": "Use the canonical road approach.", "visitor_info_source": "Local tourism office", "visitor_info_verified_at": "2026-09-30", "faqs": [{"question": "Is planning required?", "answer": "Check local conditions.", "display_order": 0, "is_active": True}]}
        code, value = request_json("POST", "/admin/discovery/places", payload, token=self.token)
        self.assertEqual(code, 201, value); self.place_ids.append(value["id"])
        if publish:
            code, publication = request_json("POST", f"/admin/discovery/places/{value['id']}/publish", {"expected_version": value["version"], "reason": "Ready for destination listing"}, token=self.token)
            self.assertEqual(code, 200, publication); return publication["entity"]
        return value

    def test_destination_places_are_automatic_and_enrichment_is_conditional(self) -> None:
        destination = self.create_destination(f"Umred Capability {self.suffix}")
        other_destination = self.create_destination(f"Other Destination {self.suffix}")
        first = self.create_place(destination["id"], f"First Place {self.suffix}", publish=True)
        second = self.create_place(destination["id"], f"Second Place {self.suffix}", publish=True)
        draft = self.create_place(destination["id"], f"Draft Place {self.suffix}", publish=False)
        self.create_place(other_destination["id"], f"Other Place {self.suffix}", publish=True)
        self.create_place(None, f"District Only {self.suffix}", publish=True)

        path = f"/destinations/nagpur/{destination['slug']}"
        code, public = request_json("GET", path)
        self.assertEqual(code, 200, public)
        self.assertEqual({first["slug"], second["slug"]}, {item["slug"] for item in public["places"]})
        self.assertEqual(["When should I visit?"], [item["question"] for item in public["faqs"]])

        code, published = request_json("POST", f"/admin/discovery/places/{draft['id']}/publish", {"expected_version": draft["version"], "reason": "Now ready for automatic display"}, token=self.token)
        self.assertEqual(code, 200, published)
        code, public = request_json("GET", path)
        self.assertEqual(3, len(public["places"]))

        code, unpublished = request_json("POST", f"/admin/discovery/places/{first['id']}/unpublish", {"expected_version": first["version"], "reason": "Verify automatic removal behavior"}, token=self.token)
        self.assertEqual(code, 200, unpublished)
        code, public = request_json("GET", path)
        self.assertEqual({second["slug"], draft["slug"]}, {item["slug"] for item in public["places"]})

        code, detail = request_json("GET", f"/places/nagpur/{second['slug']}")
        self.assertEqual(code, 200, detail)
        self.assertEqual("Central Nagpur", detail["address"])
        self.assertEqual("Local tourism office", detail["visitor_info_source"])
        self.assertEqual(["Is planning required?"], [item["question"] for item in detail["faqs"]])
        self.assertTrue(all(item["slug"] != second["slug"] for item in detail["related_places"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
