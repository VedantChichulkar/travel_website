import unittest
import urllib.parse
import uuid
from dataclasses import replace
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.data.discovery_stories import CURATED_DISCOVERY_STORIES
from app.data.discovery_stories.types import (
    CuratedDiscoveryStory,
    DestinationReference,
    PlaceReference,
)
from app.data.provenance import SourceProvenance
from app.database import SessionLocal
from app.models.destination import Destination, District
from app.models.discovery import DiscoveryStory
from app.services import destination_service
from app.services.curated_discovery_story_seed import (
    CuratedDiscoveryStoryValidationError,
    seed_curated_discovery_stories,
    validate_curated_discovery_stories,
)
from tests.test_auth_integration import request_json


class DiscoveryStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suffix = uuid.uuid4().hex[:8]
        cls.slugs = {
            "statewide": f"statewide-story-{cls.suffix}",
            "multi": f"multi-district-story-{cls.suffix}",
            "single": f"single-district-story-{cls.suffix}",
            "inactive": f"inactive-story-{cls.suffix}",
        }
        source = (SourceProvenance("Government test source", "https://example.gov.in/story", date.today()),)
        with SessionLocal() as db:
            pune = db.scalar(select(District).where(District.slug == "pune"))
            destination = destination_service.create_destination(
                db, district=pune, name=f"Discovery Destination {cls.suffix}"
            )
            db.flush()
            cls.destination_id = destination.id
            cls.destination_slug = destination.slug
            records = (
                CuratedDiscoveryStory(
                    title=f"Statewide Story {cls.suffix}",
                    slug=cls.slugs["statewide"],
                    short_description="A statewide editorial test story.",
                    body="Statewide body before managed correction.",
                    interest_slugs=("culture-traditions",),
                    sources=source,
                ),
                CuratedDiscoveryStory(
                    title=f"Multi District Story {cls.suffix}",
                    slug=cls.slugs["multi"],
                    short_description="A multi-district editorial test story.",
                    body="This story verifies reusable regional geography.",
                    interest_slugs=("culture-traditions",),
                    district_slugs=("pune", "satara"),
                    destination_references=(DestinationReference("pune", destination.slug),),
                    sources=source,
                ),
                CuratedDiscoveryStory(
                    title=f"Single District Story {cls.suffix}",
                    slug=cls.slugs["single"],
                    short_description="A single-district culinary test story.",
                    body="This story verifies district filters and related Places.",
                    interest_slugs=("food-local-flavours",),
                    district_slugs=("nagpur",),
                    related_place_references=(PlaceReference("nagpur", "deekshabhoomi"),),
                    sources=source,
                ),
                CuratedDiscoveryStory(
                    title=f"Inactive Story {cls.suffix}",
                    slug=cls.slugs["inactive"],
                    short_description="An inactive editorial test story.",
                    body="Inactive content must remain outside public discovery.",
                    interest_slugs=("culture-traditions",),
                    sources=source,
                    is_active=False,
                ),
            )
            cls.first_report = seed_curated_discovery_stories(db, records)
            db.flush()
            statewide = db.scalar(select(DiscoveryStory).where(DiscoveryStory.slug == cls.slugs["statewide"]))
            cls.statewide_id = statewide.id
            cls.statewide_created_at = statewide.created_at
            cls.second_report = seed_curated_discovery_stories(db, records)
            corrected = (replace(records[0], body="Statewide body after managed correction."),) + records[1:]
            cls.update_report = seed_curated_discovery_stories(db, corrected)
            db.commit()

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            db.execute(delete(DiscoveryStory).where(DiscoveryStory.slug.in_(cls.slugs.values())))
            db.execute(delete(Destination).where(Destination.id == cls.destination_id))
            db.commit()

    def test_curated_batch_contains_controlled_culture_and_food_sets(self) -> None:
        culture = [item.title for item in CURATED_DISCOVERY_STORIES if "culture-traditions" in item.interest_slugs]
        food = [item.title for item in CURATED_DISCOVERY_STORIES if "food-local-flavours" in item.interest_slugs]
        self.assertEqual(len(culture), 5)
        self.assertEqual(len(food), 5)
        self.assertIn("Pandharpur Wari", culture)
        self.assertIn("Varhadi Cuisine of Vidarbha", food)
        self.assertTrue(all(item.sources for item in CURATED_DISCOVERY_STORIES))

    def test_seed_is_idempotent_and_updates_only_managed_content(self) -> None:
        self.assertEqual(self.first_report.created, 4)
        self.assertEqual(self.second_report.unchanged, 4)
        self.assertEqual(self.update_report.updated, 1)
        self.assertEqual(self.update_report.unchanged, 3)
        with SessionLocal() as db:
            story = db.scalar(select(DiscoveryStory).where(DiscoveryStory.slug == self.slugs["statewide"]))
            self.assertEqual(story.id, self.statewide_id)
            self.assertEqual(story.created_at, self.statewide_created_at)
            self.assertEqual(story.body, "Statewide body after managed correction.")

    def test_statewide_single_and_multi_district_relationships(self) -> None:
        with SessionLocal() as db:
            statewide = db.scalar(select(DiscoveryStory).where(DiscoveryStory.slug == self.slugs["statewide"]))
            multi = db.scalar(select(DiscoveryStory).where(DiscoveryStory.slug == self.slugs["multi"]))
            single = db.scalar(select(DiscoveryStory).where(DiscoveryStory.slug == self.slugs["single"]))
            self.assertEqual(statewide.districts, [])
            self.assertEqual({item.slug for item in multi.districts}, {"pune", "satara"})
            self.assertEqual({item.slug for item in multi.destinations}, {self.destination_slug})
            self.assertEqual({item.slug for item in single.districts}, {"nagpur"})
            self.assertEqual({item.slug for item in single.related_places}, {"deekshabhoomi"})

    def test_public_api_filters_and_detail_relationships(self) -> None:
        code, culture = request_json("GET", "/discovery-stories?interest=culture-traditions")
        self.assertEqual(code, 200, culture)
        self.assertIn(self.slugs["statewide"], {item["slug"] for item in culture["items"]})
        self.assertNotIn(self.slugs["inactive"], {item["slug"] for item in culture["items"]})

        code, district = request_json("GET", "/discovery-stories?district=nagpur")
        self.assertEqual(code, 200, district)
        self.assertIn(self.slugs["single"], {item["slug"] for item in district["items"]})

        code, detail = request_json("GET", f"/discovery-stories/{self.slugs['single']}")
        self.assertEqual(code, 200, detail)
        self.assertEqual(detail["path"], f"/discover/{self.slugs['single']}")
        self.assertEqual(detail["related_places"][0]["slug"], "deekshabhoomi")
        self.assertNotIn("id", detail)
        self.assertNotIn("is_active", detail)

    def test_inactive_and_missing_stories_return_404(self) -> None:
        code, _ = request_json("GET", f"/discovery-stories/{self.slugs['inactive']}")
        self.assertEqual(code, 404)
        code, _ = request_json("GET", "/discovery-stories/not-a-real-story")
        self.assertEqual(code, 404)

    def test_unified_search_can_include_distinguishable_stories(self) -> None:
        query = urllib.parse.quote(f"Single District Story {self.suffix}")
        code, legacy = request_json("GET", f"/destinations/search?q={query}&include_places=true")
        self.assertEqual(code, 200, legacy)
        self.assertNotIn(self.slugs["single"], {item["slug"] for item in legacy["items"]})
        code, response = request_json(
            "GET", f"/destinations/search?q={query}&include_places=true&include_stories=true"
        )
        self.assertEqual(code, 200, response)
        match = next(item for item in response["items"] if item["slug"] == self.slugs["single"])
        self.assertEqual(match["kind"], "STORY")
        self.assertEqual(match["path"], f"/discover/{self.slugs['single']}")

    def test_validation_rejects_unknown_interest_and_bad_provenance(self) -> None:
        base = CuratedDiscoveryStory(
            title="Invalid test story",
            short_description="Validation fixture.",
            body="Validation fixture body.",
            interest_slugs=("not-an-interest",),
            sources=(SourceProvenance("Source", "https://example.gov.in", date.today()),),
        )
        with SessionLocal() as db:
            with self.assertRaises(CuratedDiscoveryStoryValidationError):
                validate_curated_discovery_stories(db, (base,))
            future = replace(
                base,
                interest_slugs=("culture-traditions",),
                sources=(SourceProvenance("Source", "https://example.gov.in", date.today() + timedelta(days=1)),),
            )
            with self.assertRaises(CuratedDiscoveryStoryValidationError):
                validate_curated_discovery_stories(db, (future,))

    def test_story_slug_and_title_are_unique_constraints(self) -> None:
        unique_names = {
            constraint.name
            for constraint in DiscoveryStory.__table__.constraints
            if constraint.name and constraint.name.startswith("uq_discovery_stories")
        }
        self.assertEqual(unique_names, {"uq_discovery_stories_slug", "uq_discovery_stories_title"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
