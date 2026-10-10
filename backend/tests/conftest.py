"""Test fixtures and helpers for FarmShield."""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app

test_client = TestClient(app)


def get_auth_headers(email: str = "farmer_test@farmshield.org", role: str = "farmer") -> dict:
    # Register/login test user
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test User",
        "role": role,
        "preferred_language": "en",
    }
    resp = test_client.post("/api/v1/auth/register", json=payload)
    if resp.status_code == 200:
        token = resp.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # If already exists, login
    login_resp = test_client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    if login_resp.status_code == 200:
        token = login_resp.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    raise RuntimeError(f"Could not authenticate test user: {resp.text} / {login_resp.text}")
