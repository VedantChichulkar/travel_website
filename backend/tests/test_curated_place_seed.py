import unittest
from dataclasses import replace
from datetime import date, timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers all relationship targets with SQLAlchemy
from app.core.slug import slugify
from app.data.interests import MAHARASHTRA_INTERESTS_V1
from app.data.maharashtra import MAHARASHTRA_DISTRICTS_V1
from app.data.places import CURATED_PLACES_V1, CuratedPlace, SourceProvenance
from app.data.places.beaches_coast import BEACH_COAST_PLACES
from app.data.places.nature_hills import NATURE_HILL_PLACES
from app.data.places.wildlife_forests import WILDLIFE_FOREST_PLACES
from app.database import Base
from app.models.destination import Destination, District
from app.models.place import Interest, Place, SpiritualTradition
from app.models.safari import Safari
from app.services.curated_place_seed import CuratedPlaceValidationError, seed_curated_places


class CuratedPlaceSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, expire_on_commit=False)()
        self.db.add_all(
            District(name=name, slug=slug, division=division)
            for name, slug, division in MAHARASHTRA_DISTRICTS_V1
        )
        self.db.add_all(
            Interest(name=name, slug=slug, display_order=order)
            for name, slug, order in MAHARASHTRA_INTERESTS_V1
        )
        self.db.flush()
        pune = self.db.scalar(select(District).where(District.slug == "pune"))
        self.db.add(Destination(district_id=pune.id, name="Test Destination", slug="test-destination"))
        self.db.commit()
        self.sample = CURATED_PLACES_V1[0]

    def tearDown(self) -> None:
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def assert_invalid(self, record: CuratedPlace, message: str) -> None:
        with self.assertRaisesRegex(CuratedPlaceValidationError, message):
            seed_curated_places(self.db, (record,))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 0)

    def test_first_seed_creates_and_second_seed_is_idempotent(self) -> None:
        first = seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        second = seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        self.assertEqual((first.created, first.updated, first.unchanged), (1, 0, 0))
        self.assertEqual((second.created, second.updated, second.unchanged), (0, 0, 1))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 1)

    def test_changed_managed_content_and_classifications_update(self) -> None:
        seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        changed = replace(
            self.sample,
            short_description="Corrected reviewed summary.",
            description="Corrected reviewed description from the curated dataset.",
            interest_slugs=("ancient-caves",),
            is_featured=False,
        )
        report = seed_curated_places(self.db, (changed,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.slug == "ajanta-caves"))
        self.assertEqual(report.updated, 1)
        self.assertEqual(place.short_description, "Corrected reviewed summary.")
        self.assertEqual({item.slug for item in place.interests}, {"ancient-caves"})
        self.assertFalse(place.is_featured)

    def test_admin_override_is_never_reset_by_seed_rerun(self) -> None:
        seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.slug == "ajanta-caves"))
        place.short_description = "Administrator-reviewed copy that must survive."
        place.admin_overridden = True
        self.db.commit()

        report = seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        self.db.refresh(place)
        self.assertEqual((report.updated, report.unchanged), (0, 1))
        self.assertEqual(place.short_description, "Administrator-reviewed copy that must survive.")

    def test_admin_owned_identity_collision_is_not_overwritten_or_duplicated(self) -> None:
        district = self.db.scalar(select(District).where(District.slug == self.sample.district_slug))
        admin_place = Place(
            district_id=district.id,
            name="Administrator-owned Ajanta record",
            slug="ajanta-caves",
            short_description="Admin-owned content.",
            description="Admin-owned content must not be converted into curated content.",
            content_source="ADMIN",
            is_active=False,
        )
        self.db.add(admin_place)
        self.db.commit()

        report = seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        self.assertEqual((report.created, report.updated, report.unchanged), (0, 0, 1))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 1)
        self.assertEqual(admin_place.short_description, "Admin-owned content.")
        self.assertFalse(admin_place.is_active)

    def test_unknown_district_fails_before_writes(self) -> None:
        self.assert_invalid(replace(self.sample, district_slug="not-a-district"), "unknown district")

    def test_unknown_destination_fails_before_writes(self) -> None:
        self.assert_invalid(replace(self.sample, destination_slug="missing"), "unknown destination")

    def test_destination_district_mismatch_fails_before_writes(self) -> None:
        mismatch = replace(self.sample, district_slug="satara", destination_slug="test-destination")
        self.assert_invalid(mismatch, "different district")

    def test_unknown_interest_fails_before_writes(self) -> None:
        self.assert_invalid(replace(self.sample, interest_slugs=("ancient-caves-typo",)), "unknown Interest")

    def test_invalid_spiritual_tradition_fails_before_writes(self) -> None:
        self.assert_invalid(replace(self.sample, spiritual_tradition="ISLAM"), "invalid spiritual tradition")

    def test_duplicate_curated_place_fails_before_writes(self) -> None:
        with self.assertRaisesRegex(CuratedPlaceValidationError, "duplicate curated Place identity"):
            seed_curated_places(self.db, (self.sample, self.sample))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 0)

    def test_inactive_visibility_is_managed(self) -> None:
        inactive = replace(self.sample, is_active=False)
        seed_curated_places(self.db, (inactive,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.slug == "ajanta-caves"))
        self.assertFalse(place.is_active)

    def test_source_metadata_validation(self) -> None:
        cases = (
            (replace(self.sample, sources=()), "authoritative source"),
            (replace(self.sample, sources=(SourceProvenance("Official", "not-a-url", date.today()),)), "malformed source URL"),
            (replace(self.sample, sources=(SourceProvenance("Official", "https://example.gov.in/place", date.today() + timedelta(days=1)),)), "cannot be in the future"),
        )
        for record, message in cases:
            with self.subTest(message=message):
                self.assert_invalid(record, message)

    def test_unrelated_identity_and_creation_fields_are_preserved(self) -> None:
        seed_curated_places(self.db, (self.sample,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.slug == "ajanta-caves"))
        original = (place.id, place.slug, place.created_at)
        changed = replace(
            self.sample,
            name="Ajanta Cave Complex",
            slug="ajanta-caves",
            description=self.sample.description + " Reviewed correction.",
        )
        seed_curated_places(self.db, (changed,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.id == original[0]))
        self.assertEqual((place.id, place.slug, place.created_at), original)
        self.assertEqual(place.name, "Ajanta Cave Complex")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 1)

    def test_second_batch_first_run_and_second_run_are_idempotent(self) -> None:
        second_batch = NATURE_HILL_PLACES + WILDLIFE_FOREST_PLACES + BEACH_COAST_PLACES
        first = seed_curated_places(self.db, second_batch)
        self.db.commit()
        second = seed_curated_places(self.db, second_batch)
        self.db.commit()
        self.assertEqual((first.created, first.updated, first.unchanged), (23, 0, 0))
        self.assertEqual((second.created, second.updated, second.unchanged), (0, 0, 23))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 23)

        representatives = {
            "kaas-plateau": ("satara", {"nature-hills"}),
            "tadoba-andhari-tiger-reserve": ("chandrapur", {"wildlife-forests"}),
            "navegaon-national-park": ("gondia", {"wildlife-forests"}),
            "ganpatipule-beach-and-temple": ("ratnagiri", {"beaches-coast", "sacred-spiritual"}),
            "tarkarli-beach": ("sindhudurg", {"beaches-coast"}),
        }
        for slug, expected in representatives.items():
            with self.subTest(slug=slug):
                place = self.db.scalar(select(Place).where(Place.slug == slug))
                self.assertEqual(place.district.slug, expected[0])
                self.assertEqual({item.slug for item in place.interests}, expected[1])

    def test_optional_destination_mapping_does_not_touch_safari_domain(self) -> None:
        destination = self.db.scalar(select(Destination).where(Destination.slug == "test-destination"))
        linked = replace(NATURE_HILL_PLACES[3], destination_slug=destination.slug)
        safari_count = self.db.scalar(select(func.count()).select_from(Safari))
        seed_curated_places(self.db, (linked,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.slug == "lonavala-hill-station"))
        self.assertEqual(place.destination_id, destination.id)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Safari)), safari_count)

    def test_existing_coastal_fort_interest_is_updated_without_duplicate(self) -> None:
        sindhudurg = next(record for record in CURATED_PLACES_V1 if record.name == "Sindhudurg Fort")
        previous = replace(sindhudurg, interest_slugs=("forts-heritage", "history-architecture"))
        seed_curated_places(self.db, (previous,))
        self.db.commit()
        report = seed_curated_places(self.db, (sindhudurg,))
        self.db.commit()
        place = self.db.scalar(select(Place).where(Place.slug == "sindhudurg-fort"))
        self.assertEqual((report.created, report.updated), (0, 1))
        self.assertEqual(
            {item.slug for item in place.interests},
            {"forts-heritage", "history-architecture", "beaches-coast"},
        )
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Place)), 1)

    def test_second_batch_uses_district_only_fallbacks_and_no_fake_images(self) -> None:
        second_batch = NATURE_HILL_PLACES + WILDLIFE_FOREST_PLACES + BEACH_COAST_PLACES
        self.assertTrue(all(record.destination_slug is None for record in second_batch))
        self.assertTrue(all(record.image_url is None for record in second_batch))

    def test_full_v1_dataset_and_representative_records(self) -> None:
        report = seed_curated_places(self.db, CURATED_PLACES_V1)
        self.db.commit()
        self.assertEqual(report.created, 49)
        self.assertEqual(report.total_places, 49)
        representatives = {
            "ajanta-caves": ("chhatrapati-sambhajinagar", SpiritualTradition.BUDDHIST, {"ancient-caves", "history-architecture", "sacred-spiritual"}),
            "ellora-caves": ("chhatrapati-sambhajinagar", SpiritualTradition.MULTI_TRADITION, {"ancient-caves", "history-architecture", "sacred-spiritual"}),
            "raigad-fort": ("raigad", None, {"forts-heritage", "history-architecture"}),
            "deekshabhoomi": ("nagpur", SpiritualTradition.BUDDHIST, {"sacred-spiritual", "history-architecture"}),
            "takht-sachkhand-sri-hazur-sahib": ("nanded", SpiritualTradition.SIKH, {"sacred-spiritual", "history-architecture"}),
            "kaas-plateau": ("satara", None, {"nature-hills"}),
            "tadoba-andhari-tiger-reserve": ("chandrapur", None, {"wildlife-forests"}),
            "ganpatipule-beach-and-temple": ("ratnagiri", SpiritualTradition.HINDU, {"beaches-coast", "sacred-spiritual"}),
        }
        for slug, expected in representatives.items():
            with self.subTest(slug=slug):
                place = self.db.scalar(select(Place).where(Place.slug == slug))
                self.assertEqual(place.district.slug, expected[0])
                self.assertEqual(place.spiritual_tradition, expected[1])
                self.assertEqual({item.slug for item in place.interests}, expected[2])
                self.assertEqual(place.slug, slugify(place.name, max_length=180))


if __name__ == "__main__":
    unittest.main(verbosity=2)
