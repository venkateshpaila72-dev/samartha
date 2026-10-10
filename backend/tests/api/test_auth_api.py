"""Tests for Authentication Endpoints."""

import unittest
from tests.conftest import test_client


class TestAuthAPI(unittest.TestCase):
    def test_01_register_user_success(self):
        email = "farmer_auth_test@farmshield.org"
        payload = {
            "email": email,
            "password": "SecurePassword123",
            "full_name": "Ramesh Kumar",
            "role": "farmer",
            "preferred_language": "hi",
            "phone_number": "+919876543210",
            "village_or_location": "Nashik, Maharashtra",
        }
        res = test_client.post("/api/v1/auth/register", json=payload)
        self.assertIn(res.status_code, [200, 400])
        if res.status_code == 200:
            data = res.json()["data"]
            self.assertIn("access_token", data)
            self.assertEqual(data["user"]["email"], email)

    def test_02_login_success(self):
        # Register user first if not present
        email = "login_test@farmshield.org"
        test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Password123", "full_name": "User", "role": "farmer"},
        )
        res = test_client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "farmer")

    def test_03_login_invalid_password(self):
        res = test_client.post("/api/v1/auth/login", json={"email": "nonexistent@farmshield.org", "password": "wrong"})
        self.assertEqual(res.status_code, 401)

    def test_04_get_profile_me(self):
        email = "profile_me_test@farmshield.org"
        reg = test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Password123", "full_name": "Profile Farmer", "role": "farmer"},
        )
        token = reg.json()["data"]["access_token"] if reg.status_code == 200 else test_client.post("/api/v1/auth/login", json={"email": email, "password": "Password123"}).json()["data"]["access_token"]

        res = test_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["email"], email)


if __name__ == "__main__":
    unittest.main()
