import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models.hotel import Amenity
from app.repositories.hotel_repository import get_amenity_by_slug


AMENITIES = [
    ("Wi-Fi", "wi-fi", "Connectivity"),
    ("Parking", "parking", "Facilities"),
    ("Swimming Pool", "swimming-pool", "Recreation"),
    ("Restaurant", "restaurant", "Dining"),
    ("Gym", "gym", "Wellness"),
    ("Air Conditioning", "air-conditioning", "Room features"),
    ("Room Service", "room-service", "Services"),
]


def main() -> None:
    created = 0
    with SessionLocal() as db:
        for name, slug, category in AMENITIES:
            if get_amenity_by_slug(db, slug) is None:
                db.add(Amenity(name=name, slug=slug, category=category))
                created += 1
        db.commit()
    print(f"Amenity seed complete: {created} created, {len(AMENITIES) - created} already present.")


if __name__ == "__main__":
    main()
