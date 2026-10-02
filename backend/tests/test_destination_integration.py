import unittest
import urllib.parse
import uuid
from datetime import time
from decimal import Decimal

from sqlalchemy import delete, select

from app.core.slug import slugify
from app.data.maharashtra import MAHARASHTRA_DISTRICTS_V1
from app.database import SessionLocal
from app.models.destination import Destination, District
from app.models.hotel import BookingGatewayStatus, Hotel, HotelStatus, PropertyType
from app.models.hotel_verification import BusinessType, HotelVerification, VerificationStatus
from app.services import destination_service
from tests.test_auth_integration import request_json


class DestinationFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suffix = uuid.uuid4().hex[:8]
        with SessionLocal() as db:
            cls.chandrapur_id = db.scalar(select(District.id).where(District.slug == "chandrapur"))
            district = db.get(District, cls.chandrapur_id)
            destination = destination_service.create_destination(
                db, district=district, name=f"Tadoba Test {cls.suffix}"
            )
            hidden = destination_service.create_destination(
                db, district=district, name=f"Hidden Place {cls.suffix}", is_active=False
            )
            linked = cls._hotel(
                slug=f"destination-linked-{cls.suffix}",
                city="Moharli",
                district="Historical location text",
                district_id=district.id,
                destination_id=destination.id,
            )
            legacy = cls._hotel(
                slug=f"destination-legacy-{cls.suffix}",
                city=destination.name,
                district="Chandrapur",
            )
            hidden_hotel = cls._hotel(
                slug=f"destination-hidden-{cls.suffix}",
                city=hidden.name,
                district="Chandrapur",
                district_id=district.id,
                destination_id=hidden.id,
            )
            db.add_all([linked, legacy, hidden_hotel])
            db.flush()
            db.add_all(
                HotelVerification(
                    hotel_id=hotel.id,
                    business_name=hotel.name,
                    business_type=BusinessType.PROPRIETORSHIP,
                    verification_status=VerificationStatus.APPROVED,
                )
                for hotel in (linked, legacy, hidden_hotel)
            )
            db.commit()
            cls.destination_id = destination.id
            cls.destination_slug = destination.slug
            cls.destination_name = destination.name
            cls.hidden_id = hidden.id
            cls.hidden_slug = hidden.slug
            cls.hotel_ids = [linked.id, legacy.id, hidden_hotel.id]

    @staticmethod
    def _hotel(**location) -> Hotel:
        slug = location.pop("slug")
        return Hotel(
            name=f"Destination Test Hotel {slug}",
            slug=slug,
            property_type=PropertyType.RESORT,
            star_rating=Decimal("4.0"),
            status=HotelStatus.ACTIVE,
            partner_booking_gateway_status=BookingGatewayStatus.ACTIVE,
            address_line1="Destination test address",
            state="Maharashtra",
            country="India",
            postal_code="442401",
            check_in_time=time(14),
            check_out_time=time(11),
            **location,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        with SessionLocal() as db:
            db.execute(delete(HotelVerification).where(HotelVerification.hotel_id.in_(cls.hotel_ids)))
            db.execute(delete(Hotel).where(Hotel.id.in_(cls.hotel_ids)))
            db.execute(delete(Destination).where(Destination.id.in_([cls.destination_id, cls.hidden_id])))
            db.commit()

    def test_slug_generation_and_scoped_uniqueness(self) -> None:
        self.assertEqual(slugify("Chhatrapati Sambhajinagar"), "chhatrapati-sambhajinagar")
        with SessionLocal() as db:
            first = destination_service.create_district(
                db, name=f"Slug District {self.suffix}", division="Test"
            )
            second = destination_service.create_district(
                db, name=f"Slug--District {self.suffix}", division="Test"
            )
            other = destination_service.create_district(
                db, name=f"Other District {self.suffix}", division="Test"
            )
            first_place = destination_service.create_destination(
                db, district=first, name=f"Shared Place {self.suffix}"
            )
            collision = destination_service.create_destination(
                db, district=first, name=f"Shared--Place {self.suffix}"
            )
            other_place = destination_service.create_destination(
                db, district=other, name=f"Shared Place {self.suffix}"
            )
            self.assertEqual(second.slug, f"{first.slug}-2")
            self.assertEqual(collision.slug, f"{first_place.slug}-2")
            self.assertEqual(other_place.slug, first_place.slug)
            db.rollback()

    def test_seed_contains_all_36_canonical_districts(self) -> None:
        expected = {(name, slug, division) for name, slug, division in MAHARASHTRA_DISTRICTS_V1}
        with SessionLocal() as db:
            actual = set(db.execute(select(District.name, District.slug, District.division)).all())
        self.assertEqual(len(expected), 36)
        self.assertEqual(actual, expected)

    def test_public_district_and_nested_destination_contracts(self) -> None:
        code, district = request_json("GET", "/destinations/chandrapur")
        self.assertEqual(code, 200, district)
        self.assertEqual(district["slug"], "chandrapur")
        self.assertIn(self.destination_slug, {item["slug"] for item in district["destinations"]})
        self.assertNotIn(self.hidden_slug, {item["slug"] for item in district["destinations"]})

        code, places = request_json("GET", "/destinations/chandrapur/places")
        self.assertEqual(code, 200, places)
        self.assertIn(self.destination_slug, {item["slug"] for item in places["items"]})
        code, place = request_json(
            "GET", f"/destinations/chandrapur/{self.destination_slug}"
        )
        self.assertEqual(code, 200, place)
        self.assertEqual(place["path"], f"/destinations/chandrapur/{self.destination_slug}")

        code, hidden = request_json("GET", f"/destinations/chandrapur/{self.hidden_slug}")
        self.assertEqual(code, 404, hidden)
        code, missing = request_json("GET", "/destinations/not-a-district")
        self.assertEqual(code, 404, missing)

    def test_autocomplete_searches_districts_and_destinations(self) -> None:
        query = urllib.parse.quote(self.destination_name[:10])
        code, results = request_json("GET", f"/destinations/search?q={query}")
        self.assertEqual(code, 200, results)
        match = next(item for item in results["items"] if item["slug"] == self.destination_slug)
        self.assertEqual(match["kind"], "DESTINATION")
        self.assertEqual(match["district_slug"], "chandrapur")

        code, district_results = request_json("GET", "/destinations/search?q=nagpur")
        self.assertEqual(code, 200, district_results)
        self.assertIn("nagpur", {item["slug"] for item in district_results["items"]})

    def test_hotel_filter_uses_links_and_legacy_fallback(self) -> None:
        code, district = request_json("GET", "/hotels?destination=chandrapur")
        self.assertEqual(code, 200, district)
        district_ids = {item["id"] for item in district["items"]}
        self.assertTrue(set(self.hotel_ids).issubset(district_ids))

        query = urllib.parse.quote(self.destination_slug)
        code, destination = request_json("GET", f"/hotels?destination={query}")
        self.assertEqual(code, 200, destination)
        self.assertEqual(
            {self.hotel_ids[0], self.hotel_ids[1]},
            {item["id"] for item in destination["items"]},
        )
        code, nested = request_json(
            "GET", f"/hotels?destination=chandrapur%2F{self.destination_slug}"
        )
        self.assertEqual(code, 200, nested)
        self.assertEqual(
            {self.hotel_ids[0], self.hotel_ids[1]}, {item["id"] for item in nested["items"]}
        )

        code, hidden = request_json("GET", f"/hotels?destination={self.hidden_slug}")
        self.assertEqual(code, 200, hidden)
        self.assertEqual(hidden["total"], 0)
        code, missing = request_json("GET", "/hotels?destination=not-a-real-place")
        self.assertEqual(code, 200, missing)
        self.assertEqual(missing["total"], 0)

    def test_existing_city_search_remains_compatible(self) -> None:
        city = urllib.parse.quote(self.destination_name)
        code, response = request_json("GET", f"/hotels?city={city}")
        self.assertEqual(code, 200, response)
        self.assertIn(self.hotel_ids[1], {item["id"] for item in response["items"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
