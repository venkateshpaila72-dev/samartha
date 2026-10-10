
"""Create the initial FarmShield admin account."""

import datetime
import json
import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.security import hash_password
from app.db.mongo import MongoDBManager
from app.repositories.user_repository import UserRepository


def main() -> int:
    seed_path = Path(
        os.getenv(
            "ADMIN_SEED_FILE",
            str(BACKEND_DIR / "data" / "admin_seed.json"),
        )
    )

    if not seed_path.is_absolute():
        seed_path = (BACKEND_DIR / seed_path).resolve()

    if not seed_path.exists():
        print(f"Admin seed file not found: {seed_path}")
        return 1

    data = json.loads(seed_path.read_text(encoding="utf-8"))

    email = os.getenv(
        "ADMIN_EMAIL",
        data.get("email", ""),
    ).strip().lower()

    password = os.getenv(
        "ADMIN_PASSWORD",
        data.get("password", ""),
    )

    full_name = os.getenv(
        "ADMIN_FULL_NAME",
        data.get("full_name", "FarmShield Administrator"),
    ).strip()

    if not email or not password or len(password) < 8:
        print(
            "A valid admin email and a password of at least "
            "8 characters are required."
        )
        return 1

    if (
        settings.APP_ENV == "production"
        and password == "FarmShieldAdmin@2026"
    ):
        print(
            "Set a strong ADMIN_PASSWORD before seeding in production."
        )
        return 1

    db = MongoDBManager.connect()

    if db is None:
        print(
            "Could not connect to MongoDB. Check backend/.env "
            "and MONGODB_URI."
        )
        return 1

    existing = UserRepository.get_by_email(email)

    if existing:
        if existing.get("role") != "admin":
            print(
                "An account with this email already exists as a "
                "non-admin. Choose a separate admin email."
            )
            return 1

        print(
            f"Admin already exists: {email}. "
            "No duplicate account was created."
        )
        return 0

    now = datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()

    admin_doc = {
        "id": f"admin_{uuid.uuid4().hex[:10]}",
        "email": email,
        "password_hash": hash_password(password),
        "full_name": full_name,
        "role": "admin",
        "preferred_language": data.get(
            "preferred_language",
            "en",
        ),
        "phone_number": None,
        "village_or_location": None,
        "whatsapp_url": None,
        "created_at": now,
    }

    UserRepository.create(admin_doc)

    print("Admin account created successfully.")
    print(f"Email: {email}")
    print("Password is configured; it will not be printed.")
    print(f"Database: {settings.MONGODB_DATABASE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
