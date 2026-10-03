import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.data.interests import MAHARASHTRA_INTERESTS_V1
from app.data.maharashtra import MAHARASHTRA_DISTRICTS_V1
from app.data.places import CURATED_PLACES_V1
from app.database import Base
from app.models import Destination, DestinationFAQ, DestinationMedia, District, Interest, Place, PlaceFAQ, PlaceMedia, PublicMediaAsset
from app.services import admin_discovery_service, destination_service, place_service
from app.services.curated_place_seed import seed_curated_places
from app.services.umred_pilot_import import import_umred, load_pilot


class UmredPilotTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.db.add_all(District(name=n, slug=s, division=d) for n, s, d in MAHARASHTRA_DISTRICTS_V1)
        self.db.add_all(Interest(name=n, slug=s, display_order=o) for n, s, o in MAHARASHTRA_INTERESTS_V1)
        self.db.flush()
        seed_curated_places(self.db, CURATED_PLACES_V1)
        self.db.commit()
        self.nagpur = self.db.scalar(select(District).where(District.slug == "nagpur"))
        self.data = load_pilot()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def count(self, model):
        return self.db.scalar(select(func.count()).select_from(model))

    def migrate(self):
        report = import_umred(self.db)
        self.db.commit()
        return report

    def imported(self):
        return list(self.db.scalars(select(Place).where(Place.content_source == "MIGRATION")))

    def test_idempotent_relationships_faqs_and_stable_slugs(self):
        first = self.migrate()
        ids = [(v.id, v.slug, v.version) for v in self.imported()]
        second = self.migrate()
        self.assertEqual(3, sum(v["action"] == "CREATE" for v in first["events"]))
        self.assertEqual(3, sum(v["action"] == "SKIP" for v in second["events"]))
        self.assertEqual(ids, [(v.id, v.slug, v.version) for v in self.imported()])
        self.assertEqual((1, 51, 15, 0), tuple(self.count(m) for m in (Destination, Place, PlaceFAQ, DestinationFAQ)))
        parent = self.db.get(Destination, first["destination_id"])
        self.assertEqual(("umred", self.nagpur.id, None, None, False), (parent.slug, parent.district_id, parent.description, parent.short_summary, parent.is_active))
        for item in self.imported():
            source = next(v for v in self.data["places"] if v["slug"] == item.slug)
            self.assertEqual((self.nagpur.id, parent.id), (item.district_id, item.destination_id))
            self.assertEqual(source["fields"]["description"], item.description)
            self.assertEqual(source["faqs"], [{"question": f.question, "answer": f.answer} for f in item.faqs])
            self.assertEqual(list(range(len(item.faqs))), [f.display_order for f in item.faqs])
            self.assertIsNone(item.visitor_info_verified_at)
            self.assertIn("OLD_SITE_UNVERIFIED", item.visitor_info_source)
            self.assertIsNone(item.nearest_airport)
            self.assertIsNone(item.nearest_railway_station)
            self.assertIsNone(item.recommended_visit_duration)

    def test_lake_park_and_media_remain_unimported(self):
        report = self.migrate()
        self.assertEqual({"C031", "C032"}, {v["record_id"] for v in report["events"] if v["action"] == "REVIEW"})
        self.assertFalse(any("gandhi-sagar" in v.slug for v in self.db.scalars(select(Place))))
        self.assertEqual((0, 0, 0), tuple(self.count(m) for m in (PublicMediaAsset, PlaceMedia, DestinationMedia)))
        for item in self.imported():
            self.assertIsNone(item.image_url)
            self.assertIsNone(item.media_asset_id)
            self.assertNotIn("/wp-content/", item.description)

    def test_curated_rows_and_taxonomy_preserved(self):
        before = {v.id: (v.name, v.slug, v.description, v.image_url, v.is_active, v.version, tuple(i.id for i in v.interests)) for v in self.db.scalars(select(Place))}
        self.migrate()
        after = {v.id: (v.name, v.slug, v.description, v.image_url, v.is_active, v.version, tuple(i.id for i in v.interests)) for v in self.db.scalars(select(Place).where(Place.content_source == "CURATED"))}
        self.assertEqual(before, after)
        self.assertEqual((36, 9), (self.count(District), self.count(Interest)))

    def test_admin_and_curated_matches_preserve_content_media_state_and_slug(self):
        for record, source in zip(self.data["places"], ("ADMIN", "CURATED")):
            item = Place(district_id=self.nagpur.id, name=record["name"], slug="stable-" + record["record_id"].lower(), content_source=source, description="Existing approved description", image_url="/approved.webp", is_active=True)
            item.faqs = [PlaceFAQ(question="Existing FAQ", answer="Keep this", display_order=7)]
            self.db.add(item)
        self.db.commit()
        before = self.count(Place)
        report = self.migrate()
        self.assertEqual(before, self.count(Place))
        for event in report["events"]:
            if event["record_id"] not in ("C033", "C034"):
                continue
            self.assertEqual("SKIP", event["action"])
            item = self.db.get(Place, event["id"])
            self.assertEqual(("Existing approved description", "/approved.webp", True, None, 1), (item.description, item.image_url, item.is_active, item.destination_id, item.version))
            self.assertEqual("Existing FAQ", item.faqs[0].question)

    def test_admin_edits_to_imported_content_survive_rerun(self):
        self.migrate()
        item = self.imported()[0]
        item.description = "Admin correction"
        item.version += 1
        item.faqs[0].answer = "Admin FAQ correction"
        self.db.commit()
        self.migrate()
        self.assertEqual("Admin correction", item.description)
        self.assertEqual("Admin FAQ correction", item.faqs[0].answer)

    def test_variant_identity_preserves_existing_stable_slug(self):
        self.db.add(Place(district_id=self.nagpur.id, name="Shri Gajanan Maharaj Devasthan W.C.L, Umred", slug="owner-temple", content_source="ADMIN", is_active=False))
        self.db.commit()
        report = self.migrate()
        event = next(v for v in report["events"] if v["record_id"] == "C033")
        self.assertEqual(("SKIP", "owner-temple"), (event["action"], event["slug"]))

    def test_uncertain_place_variant_is_reviewed_not_duplicated(self):
        self.db.add(Place(district_id=self.nagpur.id, name="Gajanan Maharaj Temple", slug="gajanan-temple", content_source="ADMIN", is_active=False))
        self.db.commit()
        report = self.migrate()
        self.assertEqual("REVIEW", next(v["action"] for v in report["events"] if v["record_id"] == "C033"))
        self.assertEqual(1, len(self.imported()))

    def test_existing_parent_publication_copy_and_slug_preserved(self):
        parent = Destination(district_id=self.nagpur.id, name="Umred", slug="owner-umred", description="Owner overview", short_summary="Owner summary", content_source="ADMIN", is_active=True)
        self.db.add(parent)
        self.db.commit()
        self.migrate()
        self.assertEqual(1, self.count(Destination))
        self.assertEqual(("owner-umred", "Owner overview", "Owner summary", True, 1), (parent.slug, parent.description, parent.short_summary, parent.is_active, parent.version))
        self.assertTrue(all(v.destination_id == parent.id and not v.is_active for v in self.imported()))

    def test_ambiguous_parent_stops_all_creation(self):
        self.db.add(Destination(district_id=self.nagpur.id, name="Umred region", slug="umred-region", content_source="ADMIN", is_active=False))
        self.db.commit()
        report = self.migrate()
        self.assertTrue(all(v["action"] == "REVIEW" for v in report["events"]))
        self.assertEqual((1, 49, 0), tuple(self.count(m) for m in (Destination, Place, PlaceFAQ)))

    def test_missing_reference_fails_before_writes_and_dry_run_rolls_back(self):
        interest = self.db.scalar(select(Interest).where(Interest.slug == "sacred-spiritual"))
        interest.is_active = False
        self.db.commit()
        with self.assertRaises(ValueError):
            import_umred(self.db)
        self.assertEqual(0, self.count(Destination))
        interest.is_active = True
        self.db.commit()
        import_umred(self.db)
        self.db.rollback()
        self.assertEqual((0, 49, 0), tuple(self.count(m) for m in (Destination, Place, PlaceFAQ)))

    def test_drafts_excluded_and_existing_public_membership_search_interest_work(self):
        report = self.migrate()
        with self.assertRaises(HTTPException) as error:
            destination_service.get_destination(self.db, "nagpur", "umred")
        self.assertEqual(404, error.exception.status_code)
        parent = self.db.get(Destination, report["destination_id"])
        with self.assertRaises(HTTPException):
            admin_discovery_service._publication_ready(parent)
        # Synthetic test-only overview establishes existing query behavior; never production copy.
        parent.description = "Test fixture overview"
        parent.is_active = True
        first, draft = self.imported()
        first.is_active = True
        self.db.commit()
        public = destination_service.get_destination(self.db, "nagpur", "umred")
        self.assertEqual([first.slug], [v.slug for v in public.places])
        detail = place_service.get_place(self.db, "nagpur", first.slug)
        self.assertEqual("umred", detail.destination.slug)
        self.assertEqual(len(first.faqs), len(detail.faqs))
        with self.assertRaises(HTTPException):
            place_service.get_place(self.db, "nagpur", draft.slug)
        listing = place_service.list_places(self.db, query=None, district_slug="nagpur", destination_slug="umred", interest_slug="sacred-spiritual", limit=100, offset=0)
        self.assertEqual([first.slug], [v.slug for v in listing.items])
        search = destination_service.search(self.db, "Umred", 50, include_places=True, include_stories=True)
        paths = {v.path for v in search.items}
        self.assertIn(f"/places/nagpur/{first.slug}", paths)
        self.assertNotIn(f"/places/nagpur/{draft.slug}", paths)


if __name__ == "__main__":
    unittest.main()
