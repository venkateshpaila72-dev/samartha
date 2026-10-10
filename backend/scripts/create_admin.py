"""Script to securely create an administrative account in FarmShield.
Usage:
    python scripts/create_admin.py --email admin@farmshield.org --password SuperSecurePassword123 --name "Admin User"
"""

import argparse
import datetime
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.security import hash_password
from app.db.mongo import MongoDBManager
from app.repositories.user_repository import UserRepository


def create_admin(email: str, password: str, full_name: str, phone: str = None, location: str = "HQ"):
    email_clean = email.strip().lower()
    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    # Initialize DB connection
    MongoDBManager.connect()

    existing = UserRepository.get_by_email(email_clean)
    if existing:
        print(f"User with email '{email_clean}' already exists. Updating role to admin.")
        UserRepository.update(existing["id"], {"role": "admin"})
        print(f"Successfully promoted user '{email_clean}' to role: admin.")
        return

    user_id = f"admin_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    admin_doc = {
        "id": user_id,
        "email": email_clean,
        "password_hash": hash_password(password),
        "full_name": full_name,
        "role": "admin",
        "preferred_language": "en",
        "phone_number": phone,
        "village_or_location": location,
        "created_at": now_iso,
    }

    UserRepository.create(admin_doc)
    print(f"Successfully created admin account: {email_clean} (ID: {user_id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create FarmShield Admin User")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--name", default="System Administrator", help="Admin full name")
    parser.add_argument("--phone", default=None, help="Admin phone number")
    parser.add_argument("--location", default="HQ", help="Admin location")

    args = parser.parse_args()
    create_admin(args.email, args.password, args.name, args.phone, args.location)
