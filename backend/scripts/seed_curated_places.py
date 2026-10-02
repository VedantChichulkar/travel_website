"""Intentionally apply the reviewed Place dataset; never called at app startup."""

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.data.places import CURATED_PLACES_V1
from app.database import SessionLocal
from app.services.curated_place_seed import CuratedPlaceValidationError, seed_curated_places


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and upsert Maharashtra Tourist Places' curated Place dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and calculate changes, then roll back.")
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            report = seed_curated_places(db, CURATED_PLACES_V1)
            if args.dry_run:
                db.rollback()
            else:
                db.commit()
        except CuratedPlaceValidationError as error:
            db.rollback()
            print(f"Curated Place seed failed: {error}", file=sys.stderr)
            return 1

    mode = "dry-run" if args.dry_run else "committed"
    print(f"Curated Place seed {mode} (dataset v1):")
    for line in report.lines():
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

