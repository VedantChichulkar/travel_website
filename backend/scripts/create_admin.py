import argparse
import getpass
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import create_user, get_user_by_email, get_user_by_phone
from app.schemas.user import UserCreate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the first admin account safely.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--phone", required=True, help="E.164 format, such as +919876543210")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = getpass.getpass("Admin password: ")
    password_confirmation = getpass.getpass("Confirm admin password: ")
    if password != password_confirmation:
        print("Admin passwords do not match.", file=sys.stderr)
        return 1

    try:
        data = UserCreate(
            full_name=args.full_name,
            email=args.email,
            phone=args.phone,
            password=password,
        )
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 1

    with SessionLocal() as db:
        existing_email = get_user_by_email(db, str(data.email))
        if existing_email:
            if existing_email.role == UserRole.ADMIN:
                print("An admin with this email already exists; no changes made.")
                return 0
            print("This email belongs to a non-admin account; no changes made.", file=sys.stderr)
            return 1
        if get_user_by_phone(db, data.phone):
            print("This phone number is already registered; no changes made.", file=sys.stderr)
            return 1

        try:
            admin = create_user(
                db,
                full_name=data.full_name,
                email=str(data.email),
                phone=data.phone,
                password_hash=hash_password(data.password),
                role=UserRole.ADMIN,
            )
        except IntegrityError:
            db.rollback()
            print("An account with that email or phone already exists; no changes made.", file=sys.stderr)
            return 1

    print(f"Admin account created for {admin.email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
