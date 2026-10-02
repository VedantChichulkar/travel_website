import json
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.hotel import Amenity, Hotel, HotelPolicy, RoomInventory, RoomType, hotel_amenities
from app.models.user import User, UserRole
from app.repositories.user_repository import create_user
from tests.test_auth_integration import request_json


RESULTS: dict[str, dict[str, object]] = {}


def record(name: str, passed: bool, status_code: int | None = None, detail: str = "") -> None:
    RESULTS[name] = {
        "result": "PASS" if passed else "FAIL",
        "status_code": status_code,
        "detail": detail,
    }
    if not passed:
        raise AssertionError(f"{name}: status={status_code}, detail={detail}")


def expect(name: str, actual: int, expected: int, body: object) -> None:
    record(name, actual == expected, actual, "" if actual == expected else repr(body))


def main() -> int:
    suffix = uuid.uuid4().hex[:10]
    digits = str(uuid.uuid4().int)[-9:]
    password = "PhaseTwoVerify123"
    admin_email = f"phase2-admin-{suffix}@example.com"
    user_email = f"phase2-user-{suffix}@example.com"
    account_emails = [admin_email, user_email]

    hotel_payload = {
        "name": "Sea View Resort Goa",
        "slug": "sea-view-resort-goa",
        "description": "A comfortable beachside resort in Goa with modern rooms, swimming pool, restaurant and convenient access to nearby attractions.",
        "property_type": "RESORT",
        "star_rating": 4,
        "address_line1": "Calangute Beach Road",
        "address_line2": "Near Main Beach",
        "city": "Goa",
        "state": "Goa",
        "country": "India",
        "postal_code": "403516",
        "latitude": 15.5449,
        "longitude": 73.7556,
        "contact_email": "seaview@example.com",
        "contact_phone": "+919876543211",
        "check_in_time": "14:00:00",
        "check_out_time": "11:00:00",
        "is_featured": True,
    }
    amenity_payloads = [
        {"name": "Wi-Fi", "slug": "wifi", "icon": "wifi", "category": "GENERAL", "is_active": True},
        {"name": "Swimming Pool", "slug": "swimming-pool", "icon": "pool", "category": "RECREATION", "is_active": True},
        {"name": "Parking", "slug": "parking", "icon": "parking", "category": "GENERAL", "is_active": True},
        {"name": "Restaurant", "slug": "restaurant", "icon": "restaurant", "category": "FOOD", "is_active": True},
        {"name": "Air Conditioning", "slug": "air-conditioning", "icon": "ac", "category": "ROOM", "is_active": True},
    ]
    policy_payload = {
        "cancellation_policy": "Free cancellation up to 48 hours before check-in. Cancellations made within 48 hours of check-in may be charged one night's room rate.",
        "children_policy": "Children are allowed. Children below 5 years may stay without additional room charges when using existing bedding.",
        "pet_policy": "Pets are not allowed.",
        "smoking_policy": "Smoking is not permitted inside rooms. Designated smoking areas may be available.",
        "extra_bed_policy": "Extra beds are subject to availability and additional charges.",
        "additional_rules": "Guests must present a valid government-issued photo ID during check-in.",
    }
    room_payload = {
        "name": "Deluxe Ocean View",
        "description": "Spacious deluxe room with a king-size bed, air conditioning and partial ocean view.",
        "max_adults": 2,
        "max_children": 1,
        "max_guests": 3,
        "bed_type": "KING",
        "bed_count": 1,
        "room_size_sqm": 32,
        "base_price": 4500,
        "currency": "INR",
        "total_rooms": 10,
        "is_active": True,
    }
    inventory_payloads = [
        {"inventory_date": "2026-12-20", "total_inventory": 10, "available_inventory": 10, "blocked_inventory": 0, "price": 4500, "is_closed": False},
        {"inventory_date": "2026-12-21", "total_inventory": 10, "available_inventory": 8, "blocked_inventory": 2, "price": 4800, "is_closed": False},
        {"inventory_date": "2026-12-22", "total_inventory": 10, "available_inventory": 5, "blocked_inventory": 1, "price": 5200, "is_closed": False},
    ]

    hotel_id: int | None = None
    room_id: int | None = None
    amenity_ids: list[int] = []
    inventory_ids: list[int] = []

    try:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email.in_(account_emails)))
            db.commit()
            create_user(
                db,
                full_name="Phase 2 Verification Admin",
                email=admin_email,
                phone=f"+914{digits}",
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
            create_user(
                db,
                full_name="Phase 2 Verification User",
                email=user_email,
                phone=f"+913{digits}",
                password_hash=hash_password(password),
                role=UserRole.USER,
            )

        code, admin_login = request_json("POST", "/auth/login", {"email": admin_email, "password": password})
        expect("ADMIN authentication", code, 200, admin_login)
        admin_token = str(admin_login["access_token"])
        code, user_login = request_json("POST", "/auth/login", {"email": user_email, "password": password})
        expect("USER authentication", code, 200, user_login)
        user_token = str(user_login["access_token"])

        code, body = request_json("GET", "/admin/hotels")
        expect("Unauthorized request", code, 401, body)
        code, body = request_json("POST", "/admin/hotels", hotel_payload, user_token)
        expect("USER authorization rejection", code, 403, body)

        with SessionLocal() as db:
            existing_hotel = db.scalar(select(Hotel).where(Hotel.slug == hotel_payload["slug"]))
        if existing_hotel is None:
            code, hotel = request_json("POST", "/admin/hotels", hotel_payload, admin_token)
            expect("Create Hotel", code, 201, hotel)
            hotel_id = int(hotel["id"])
        else:
            hotel_id = existing_hotel.id
            record("Create Hotel", True, 200, "Existing requested slug reused for idempotent verification")

        code, body = request_json("POST", "/admin/hotels", hotel_payload, admin_token)
        expect("Duplicate hotel slug", code, 409, body)
        invalid_hotel = dict(hotel_payload)
        invalid_hotel["slug"] = f"invalid-rating-{suffix}"
        invalid_hotel["star_rating"] = 6
        code, body = request_json("POST", "/admin/hotels", invalid_hotel, admin_token)
        expect("Invalid star rating", code, 422, body)

        code, hotels = request_json("GET", "/admin/hotels", token=admin_token)
        expect("List Hotels", code, 200, hotels)
        record("Created hotel appears in list", any(int(item["id"]) == hotel_id for item in hotels), code)
        code, hotel_detail = request_json("GET", f"/admin/hotels/{hotel_id}", token=admin_token)
        expect("Get Hotel", code, 200, hotel_detail)
        record("Hotel response fields", hotel_detail["slug"] == "sea-view-resort-goa" and "password_hash" not in hotel_detail, code)
        code, body = request_json("GET", "/admin/hotels/999999999", token=admin_token)
        expect("Nonexistent hotel", code, 404, body)

        code, updated_hotel = request_json(
            "PATCH",
            f"/admin/hotels/{hotel_id}",
            {"description": hotel_payload["description"] + " Verified end-to-end."},
            admin_token,
        )
        expect("Update Hotel", code, 200, updated_hotel)

        code, amenities = request_json("GET", "/admin/amenities", token=admin_token)
        expect("List Amenities (initial)", code, 200, amenities)
        for payload in amenity_payloads:
            code, response = request_json("POST", "/admin/amenities", payload, admin_token)
            if code == 201:
                amenity_ids.append(int(response["id"]))
            elif code == 409:
                matches = [
                    item
                    for item in amenities
                    if item["slug"] == payload["slug"] or item["name"].casefold() == payload["name"].casefold()
                ]
                record(f"Create Amenity {payload['name']}", bool(matches), code, "Existing amenity safely reused")
                amenity_ids.append(int(matches[0]["id"]))
            else:
                expect(f"Create Amenity {payload['name']}", code, 201, response)
        record("Create Amenity", len(amenity_ids) == 5, 201, "Created or safely reused five amenities")
        code, body = request_json("POST", "/admin/amenities", amenity_payloads[1], admin_token)
        expect("Duplicate amenity slug", code, 409, body)
        code, amenities = request_json("GET", "/admin/amenities", token=admin_token)
        expect("List Amenities", code, 200, amenities)
        record("Amenities listed", set(amenity_ids).issubset({int(item["id"]) for item in amenities}), code)

        code, assigned = request_json(
            "PUT", f"/admin/hotels/{hotel_id}/amenities", {"amenity_ids": amenity_ids}, admin_token
        )
        expect("Assign Amenities", code, 200, assigned)
        code, reassigned = request_json(
            "PUT", f"/admin/hotels/{hotel_id}/amenities", {"amenity_ids": amenity_ids}, admin_token
        )
        expect("Reassign Amenities", code, 200, reassigned)
        record("Amenity assignment has no duplicates", len({int(item["id"]) for item in reassigned}) == 5, code)

        code, existing_policy = request_json("GET", f"/admin/hotels/{hotel_id}/policy", token=admin_token)
        if code == 404:
            code, policy = request_json("POST", f"/admin/hotels/{hotel_id}/policy", policy_payload, admin_token)
            expect("Create Policy", code, 201, policy)
        else:
            expect("Get existing Policy", code, 200, existing_policy)
            record("Create Policy", True, 200, "Existing policy reused for idempotent verification")
        code, body = request_json("POST", f"/admin/hotels/{hotel_id}/policy", policy_payload, admin_token)
        expect("Duplicate policy", code, 409, body)
        code, policy = request_json("GET", f"/admin/hotels/{hotel_id}/policy", token=admin_token)
        expect("Get Policy", code, 200, policy)
        code, policy = request_json(
            "PATCH",
            f"/admin/hotels/{hotel_id}/policy",
            {"additional_rules": policy_payload["additional_rules"] + " Digital copies are accepted where permitted."},
            admin_token,
        )
        expect("Update Policy", code, 200, policy)

        with SessionLocal() as db:
            existing_room = db.scalar(
                select(RoomType).where(RoomType.hotel_id == hotel_id, RoomType.name == room_payload["name"])
            )
        if existing_room is None:
            code, room = request_json("POST", f"/admin/hotels/{hotel_id}/rooms", room_payload, admin_token)
            expect("Create Room", code, 201, room)
            room_id = int(room["id"])
        else:
            room_id = existing_room.id
            record("Create Room", True, 200, "Existing requested room reused for idempotent verification")

        code, rooms = request_json("GET", f"/admin/hotels/{hotel_id}/rooms", token=admin_token)
        expect("List Rooms", code, 200, rooms)
        record("Created room appears in list", any(int(item["id"]) == room_id for item in rooms), code)
        code, room = request_json("GET", f"/admin/rooms/{room_id}", token=admin_token)
        expect("Get Room", code, 200, room)
        record("Room belongs to hotel and money is decimal-safe", int(room["hotel_id"]) == hotel_id and Decimal(str(room["base_price"])) == Decimal("4500.00"), code)
        code, body = request_json("GET", "/admin/rooms/999999999", token=admin_token)
        expect("Nonexistent room", code, 404, body)
        code, room = request_json(
            "PATCH", f"/admin/rooms/{room_id}", {"description": room_payload["description"] + " Verified."}, admin_token
        )
        expect("Update Room", code, 200, room)
        code, inactive_room = request_json(
            "PATCH", f"/admin/rooms/{room_id}/status", {"is_active": False}, admin_token
        )
        expect("Deactivate Room", code, 200, inactive_room)
        code, inactive_detail = request_json("GET", f"/admin/rooms/{room_id}", token=admin_token)
        expect("Get inactive Room", code, 200, inactive_detail)
        record("Inactive room remains administratively accessible", inactive_detail["is_active"] is False, code)
        code, room = request_json("PATCH", f"/admin/rooms/{room_id}/status", {"is_active": True}, admin_token)
        expect("Reactivate Room", code, 200, room)

        for payload in inventory_payloads:
            with SessionLocal() as db:
                existing_inventory = db.scalar(
                    select(RoomInventory).where(
                        RoomInventory.room_type_id == room_id,
                        RoomInventory.inventory_date
                        == date.fromisoformat(payload["inventory_date"]),
                    )
                )
            if existing_inventory is None:
                code, inventory = request_json(
                    "POST", f"/admin/rooms/{room_id}/inventory", payload, admin_token
                )
                expect(f"Create Inventory {payload['inventory_date']}", code, 201, inventory)
                inventory_ids.append(int(inventory["id"]))
            else:
                inventory_ids.append(existing_inventory.id)
                record(f"Create Inventory {payload['inventory_date']}", True, 200, "Existing date reused")

        code, body = request_json(
            "POST", f"/admin/rooms/{room_id}/inventory", inventory_payloads[0], admin_token
        )
        expect("Duplicate room inventory date", code, 409, body)
        invalid_inventory_cases = [
            ("Negative inventory", {**inventory_payloads[0], "inventory_date": "2026-12-23", "total_inventory": -1}),
            ("Available exceeds total", {**inventory_payloads[0], "inventory_date": "2026-12-24", "available_inventory": 11}),
            ("Negative inventory price", {**inventory_payloads[0], "inventory_date": "2026-12-25", "price": -1}),
        ]
        for name, payload in invalid_inventory_cases:
            code, body = request_json("POST", f"/admin/rooms/{room_id}/inventory", payload, admin_token)
            expect(name, code, 422, body)

        code, all_inventory = request_json("GET", f"/admin/rooms/{room_id}/inventory", token=admin_token)
        expect("List Inventory", code, 200, all_inventory)
        record("All three inventory rows returned", len([item for item in all_inventory if item["inventory_date"] in {"2026-12-20", "2026-12-21", "2026-12-22"}]) == 3, code)
        filter_paths = {
            "Inventory start-date filter": f"/admin/rooms/{room_id}/inventory?start_date=2026-12-20",
            "Inventory end-date filter": f"/admin/rooms/{room_id}/inventory?end_date=2026-12-22",
            "Inventory date-range filter": f"/admin/rooms/{room_id}/inventory?start_date=2026-12-20&end_date=2026-12-22",
        }
        for name, path in filter_paths.items():
            code, filtered = request_json("GET", path, token=admin_token)
            expect(name, code, 200, filtered)
        code, ranged = request_json(
            "GET",
            f"/admin/rooms/{room_id}/inventory?start_date=2026-12-20&end_date=2026-12-22",
            token=admin_token,
        )
        record("Date range returns exactly three rows", len(ranged) == 3, code)

        code, inventory = request_json(
            "PATCH",
            f"/admin/inventory/{inventory_ids[0]}",
            {"available_inventory": 9, "price": 4750},
            admin_token,
        )
        expect("Update Inventory", code, 200, inventory)
        record("Inventory update persisted in response", inventory["available_inventory"] == 9 and Decimal(str(inventory["price"])) == Decimal("4750.00"), code)
        code, body = request_json(
            "PATCH",
            f"/admin/inventory/{inventory_ids[0]}",
            {"available_inventory": 11},
            admin_token,
        )
        expect("Invalid inventory update", code, 422, body)

        code, hotel_detail = request_json("GET", f"/admin/hotels/{hotel_id}", token=admin_token)
        expect("Retrieve complete Hotel", code, 200, hotel_detail)
        record(
            "Hotel nested design",
            len(hotel_detail["amenities"]) == 5
            and hotel_detail["policy"] is not None
            and any(int(room["id"]) == room_id for room in hotel_detail["room_types"]),
            code,
            "Detail embeds amenities, policy, room types, and images; inventory uses its separate endpoint",
        )

        code, body = request_json(
            "PATCH", f"/admin/hotels/{hotel_id}/status", {"status": "ACTIVE", "reason": "Unauthorized status test"}, user_token
        )
        expect("USER status-change rejection", code, 403, body)
        code, activated = request_json(
            "PATCH", f"/admin/hotels/{hotel_id}/status", {"status": "ACTIVE", "reason": "Activate verified workflow hotel"}, admin_token
        )
        expect("Change Hotel Status", code, 200, activated)
        code, active_detail = request_json("GET", f"/admin/hotels/{hotel_id}", token=admin_token)
        expect("Get active Hotel", code, 200, active_detail)
        record("Hotel status is ACTIVE", active_detail["status"] == "ACTIVE", code)

        with SessionLocal() as db:
            persisted_hotel = db.scalar(select(Hotel).where(Hotel.id == hotel_id))
            persisted_policy = db.scalar(select(HotelPolicy).where(HotelPolicy.hotel_id == hotel_id))
            persisted_room = db.scalar(select(RoomType).where(RoomType.id == room_id))
            persisted_inventory = list(
                db.scalars(select(RoomInventory).where(RoomInventory.room_type_id == room_id))
            )
            relationship_count = db.scalar(
                select(func.count()).select_from(hotel_amenities).where(hotel_amenities.c.hotel_id == hotel_id)
            )
            db_amenity_ids = set(
                db.scalars(
                    select(hotel_amenities.c.amenity_id).where(hotel_amenities.c.hotel_id == hotel_id)
                )
            )
            record("MySQL hotel row", persisted_hotel is not None and persisted_hotel.status.value == "ACTIVE")
            record("MySQL amenity relationships", relationship_count == 5 and db_amenity_ids == set(amenity_ids))
            record("MySQL policy row", persisted_policy is not None)
            record("MySQL room row", persisted_room is not None and persisted_room.hotel_id == hotel_id)
            record("MySQL inventory rows", len(persisted_inventory) == 3)
            first_inventory = next(item for item in persisted_inventory if str(item.inventory_date) == "2026-12-20")
            record("MySQL inventory update", first_inventory.available_inventory == 9 and first_inventory.price == Decimal("4750.00"))

    except Exception as exc:
        print(json.dumps({"results": RESULTS, "error": str(exc)}, indent=2, default=str))
        return 1
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.email.in_(account_emails)))
            db.commit()

    print(
        json.dumps(
            {
                "results": RESULTS,
                "ids": {
                    "HOTEL_ID": hotel_id,
                    "ROOM_TYPE_ID": room_id,
                    "AMENITY_IDS": amenity_ids,
                    "INVENTORY_IDS": inventory_ids,
                },
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
