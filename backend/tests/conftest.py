"""Test fixtures and helpers for FarmShield."""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Force test environment for isolation.
os.environ["APP_ENV"] = "test"

from app.core.config import settings

settings.APP_ENV = "test"

from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.main import app

test_client = TestClient(app)


def get_auth_headers(
    email: str = "farmer_test@farmshield.org",
    role: str = "farmer",
) -> dict:
    email_clean = email.strip().lower()

    # Admins are seeded directly because public registration
    # creates farmer accounts only.
    if role == "admin":
        existing = UserRepository.get_by_email(email_clean)

        if not existing:
            user_doc = {
                "id": f"admin_test_{len(email_clean)}",
                "email": email_clean,
                "password_hash": hash_password("Password123!"),
                "full_name": "Test Admin",
                "role": "admin",
                "preferred_language": "en",
                "phone_number": "+919876543210",
                "village_or_location": "Admin HQ",
            }

            UserRepository.create(user_doc)
        else:
            UserRepository.update(
                existing["id"],
                {"role": "admin"},
            )

        login_response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email_clean,
                "password": "Password123!",
                "login_as": "admin",
            },
        )

        if login_response.status_code == 200:
            token = login_response.json()["data"]["access_token"]
            return {"Authorization": f"Bearer {token}"}

        raise RuntimeError(
            f"Could not login admin user: {login_response.text}"
        )

    # Standard farmer registration.
    payload = {
        "email": email_clean,
        "password": "Password123!",
        "full_name": "Test Farmer",
        "preferred_language": "en",
    }

    response = test_client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    if response.status_code == 200:
        token = response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # If the account already exists, attempt login.
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": email_clean,
            "password": "Password123!",
        },
    )

    if login_response.status_code == 200:
        token = login_response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    raise RuntimeError(
        f"Could not authenticate test user: "
        f"{response.text} / {login_response.text}"
    )