import unittest
import urllib.parse
import uuid

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.destination import Destination, District
from app.models.place import Interest, Place
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user
from tests.test_auth_integration import request_json


class AdminDiscoveryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suffix = uuid.uuid4().hex[:10]
        cls.email = f"discovery-admin-{cls.suffix}@example.com"
        cls.customer_email = f"discovery-customer-{cls.suffix}@example.com"
        cls.password = "StrongPass123"
        with SessionLocal() as db:
            admin = create_user(
                db,
                full_name="Discovery Test Admin",
                email=cls.email,
                phone=f"+916{str(uuid.uuid4().int)[-9:]}",
                password_hash=hash_password(cls.password),
                role=UserRole.ADMIN,
            )
            customer = create_user(
                db,
                full_name="Discovery Test Customer",
                email=cls.customer_email,
                phone=f"+915{str(uuid.uuid4().int)[-9:]}",
                password_hash=hash_password(cls.password),
                role=UserRole.CUSTOMER,
            )
            db.commit()
            cls.admin_id = admin.id
            cls.customer_id = customer.id
            cls.pune_id = db.scalar(select(District.id).where(District.slug == "pune"))
            cls.raigad_id = db.scalar(select(District.id).where(District.slug == "raigad"))
            cls.nature_id = db.scalar(select(Interest.id).where(Interest.slug == "nature-hills"))
        code, login = request_json("POST", "/auth/login", {"email": cls.email, "password": cls.password, "portal": "ADMIN"})
        if code != 200:
            raise AssertionError(login)
        cls.token = str(login["access_token"])
        code, customer_login = request_json("POST", "/auth/login", {"email": cls.customer_email, "password": cls.password, "portal": "CUSTOMER"})
        if code != 200:
            raise AssertionError(customer_login)
        cls.customer_token = str(customer_login["access_token"])
        cls.destination_ids: list[int] = []
        cls.place_ids: list[int] = []

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            if cls.place_ids:
                places = list(db.scalars(select(Place).where(Place.id.in_(cls.place_ids))))
                for item in places:
                    item.interests = []
                db.flush()
                db.execute(delete(Place).where(Place.id.in_(cls.place_ids)))
            if cls.destination_ids:
                db.execute(delete(Destination).where(Destination.id.in_(cls.destination_ids)))
            db.execute(delete(User).where(User.id.in_([cls.admin_id, cls.customer_id])))
            db.commit()

    def test_admin_only_reference_contract(self) -> None:
        code, body = request_json("GET", "/admin/discovery/reference")
        self.assertEqual(code, 401, body)
        code, body = request_json("GET", "/admin/discovery/reference", token=self.customer_token)
        self.assertEqual(code, 403, body)
        code, body = request_json("POST", "/admin/discovery/media/PLACE/999", token=self.customer_token)
        self.assertEqual(code, 403, body)
        code, body = request_json("GET", "/admin/discovery/reference", token=self.token)
        self.assertEqual(code, 200, body)
        self.assertEqual(len(body["districts"]), 36)
        self.assertEqual(len(body["interests"]), 9)
        self.assertIn("MULTI_TRADITION", body["spiritual_traditions"])

    def test_destination_draft_preview_publish_unpublish_and_concurrency(self) -> None:
        name = f"Admin Destination {self.suffix}"
        code, created = request_json("POST", "/admin/discovery/destinations", {"district_id": self.pune_id, "name": name, "description": "A verified destination description."}, token=self.token)
        self.assertEqual(code, 201, created)
        self.destination_ids.append(created["id"])
        self.assertEqual(created["status"], "DRAFT")
        original_slug = created["slug"]
        code, hidden = request_json("GET", f"/destinations/pune/{original_slug}")
        self.assertEqual(code, 404, hidden)
        code, draft_search = request_json("GET", f"/destinations/search?q={urllib.parse.quote(name)}")
        self.assertNotIn(original_slug, {value["slug"] for value in draft_search["items"]})

        code, updated = request_json("PATCH", f"/admin/discovery/destinations/{created['id']}", {"expected_version": created["version"], "name": name + " Updated"}, token=self.token)
        self.assertEqual(code, 200, updated)
        self.assertEqual(updated["slug"], original_slug)
        code, stale = request_json("PATCH", f"/admin/discovery/destinations/{created['id']}", {"expected_version": created["version"], "description": "Stale edit"}, token=self.token)
        self.assertEqual(code, 409, stale)

        code, published = request_json("POST", f"/admin/discovery/destinations/{created['id']}/publish", {"expected_version": updated["version"], "reason": "Approved for public discovery"}, token=self.token)
        self.assertEqual(code, 200, published)
        self.assertEqual(published["entity"]["status"], "PUBLISHED")
        code, public = request_json("GET", f"/destinations/pune/{original_slug}")
        self.assertEqual(code, 200, public)
        code, public_search = request_json("GET", f"/destinations/search?q={urllib.parse.quote(name)}")
        self.assertIn(original_slug, {value["slug"] for value in public_search["items"]})

        code, unpublished = request_json("POST", f"/admin/discovery/destinations/{created['id']}/unpublish", {"expected_version": published["entity"]["version"], "reason": "Temporarily removed for editorial review"}, token=self.token)
        self.assertEqual(code, 200, unpublished)
        self.assertEqual(unpublished["entity"]["status"], "UNPUBLISHED")
        code, hidden_again = request_json("GET", f"/destinations/pune/{original_slug}")
        self.assertEqual(code, 404, hidden_again)
        code, unpublished_search = request_json("GET", f"/destinations/search?q={urllib.parse.quote(name)}")
        self.assertNotIn(original_slug, {value["slug"] for value in unpublished_search["items"]})

    def test_place_relationship_validation_and_publication(self) -> None:
        destination_name = f"Place Parent {self.suffix}"
        code, destination = request_json("POST", "/admin/discovery/destinations", {"district_id": self.pune_id, "name": destination_name, "description": "Parent destination."}, token=self.token)
        self.assertEqual(code, 201, destination)
        self.destination_ids.append(destination["id"])
        code, destination_publication = request_json("POST", f"/admin/discovery/destinations/{destination['id']}/publish", {"expected_version": destination["version"], "reason": "Needed for linked place testing"}, token=self.token)
        self.assertEqual(code, 200, destination_publication)

        invalid = {"district_id": self.raigad_id, "destination_id": destination["id"], "name": f"Invalid Place {self.suffix}", "short_description": "Short factual copy", "description": "Long factual copy", "interest_ids": [self.nature_id], "display_order": 0, "is_featured": False}
        code, mismatch = request_json("POST", "/admin/discovery/places", invalid, token=self.token)
        self.assertEqual(code, 422, mismatch)
        duplicate = {**invalid, "district_id": self.pune_id, "destination_id": None, "interest_ids": [self.nature_id, self.nature_id]}
        code, duplicated = request_json("POST", "/admin/discovery/places", duplicate, token=self.token)
        self.assertEqual(code, 422, duplicated)

        payload = {**invalid, "district_id": self.pune_id, "name": f"Managed Place {self.suffix}"}
        code, place = request_json("POST", "/admin/discovery/places", payload, token=self.token)
        self.assertEqual(code, 201, place)
        self.place_ids.append(place["id"])
        self.assertEqual(place["content_source"], "ADMIN")
        code, filtered_admin = request_json("GET", f"/admin/discovery/places?district_id={self.pune_id}&destination_id={destination['id']}&interest_id={self.nature_id}", token=self.token)
        self.assertEqual(code, 200, filtered_admin)
        self.assertIn(place["id"], {value["id"] for value in filtered_admin["items"]})
        code, hidden = request_json("GET", f"/places/pune/{place['slug']}")
        self.assertEqual(code, 404, hidden)
        code, publication = request_json("POST", f"/admin/discovery/places/{place['id']}/publish", {"expected_version": place["version"], "reason": "Editorial and taxonomy checks complete"}, token=self.token)
        self.assertEqual(code, 200, publication)
        code, public = request_json("GET", f"/places/pune/{place['slug']}")
        self.assertEqual(code, 200, public)
        self.assertEqual(public["image_status"], None)
        code, district_places = request_json("GET", "/places?district=pune")
        self.assertIn(place["slug"], {value["slug"] for value in district_places["items"]})
        code, interest_places = request_json("GET", "/places?interest=nature-hills")
        self.assertIn(place["slug"], {value["slug"] for value in interest_places["items"]})
        code, search = request_json("GET", f"/destinations/search?q={urllib.parse.quote(place['name'])}&include_places=true")
        self.assertIn(place["slug"], {value["slug"] for value in search["items"]})

        code, unpublished = request_json("POST", f"/admin/discovery/places/{place['id']}/unpublish", {"expected_version": publication["entity"]["version"], "reason": "Completed publication lifecycle test"}, token=self.token)
        self.assertEqual(code, 200, unpublished)
        code, hidden_again = request_json("GET", f"/places/pune/{place['slug']}")
        self.assertEqual(code, 404, hidden_again)
        code, hidden_search = request_json("GET", f"/destinations/search?q={urllib.parse.quote(place['name'])}&include_places=true")
        self.assertNotIn(place["slug"], {value["slug"] for value in hidden_search["items"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
