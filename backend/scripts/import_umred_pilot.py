"""Controlled text-only pilot, dry-run by default. No image or publication operations."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.core.config import settings
from app.database import SessionLocal, engine
from app.services.umred_pilot_import import import_umred


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the reviewed drafts to the configured local development database")
    parser.add_argument("--report", type=Path, help="Save the action report as JSON")
    args = parser.parse_args()
    if args.apply and (settings.ENVIRONMENT != "development" or engine.url.host not in (None, "localhost", "127.0.0.1", "::1")):
        parser.error("This pilot applies only to the local development database")
    with SessionLocal() as db:
        try:
            report = import_umred(db)
            report["mode"] = "committed" if args.apply else "dry-run (rolled back)"
            db.commit() if args.apply else db.rollback()
        except Exception:
            db.rollback()
            raise
    output = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
