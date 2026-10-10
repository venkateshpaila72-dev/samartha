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

        response = test_client.post(
            "/api/v1/auth/register",
            json=payload,
        )

        self.assertIn(response.status_code, [200, 400])

        if response.status_code == 200:
            data = response.json()["data"]
            self.assertIn("access_token", data)
            self.assertEqual(data["user"]["email"], email)

    def test_02_login_success(self):
        email = "login_test@farmshield.org"

        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123",
                "full_name": "User",
                "role": "farmer",
            },
        )

        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "Password123",
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()["data"]

        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "farmer")

    def test_03_login_invalid_password(self):
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@farmshield.org",
                "password": "wrong",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_04_get_profile_me(self):
        email = "profile_me_test@farmshield.org"

        registration = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123",
                "full_name": "Profile Farmer",
                "role": "farmer",
            },
        )

        if registration.status_code == 200:
            token = registration.json()["data"]["access_token"]
        else:
            login_response = test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "Password123",
                },
            )
            token = login_response.json()["data"]["access_token"]

        response = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["email"], email)

    def test_farmer_cannot_use_admin_login(self):
        email = "role_mismatch_test@farmshield.org"

        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123",
                "full_name": "Role Test Farmer",
            },
        )

        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "Password123",
                "login_as": "admin",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_whatsapp_url_is_returned_on_registration(self):
        email = "whatsapp_url_test@farmshield.org"

        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Password123",
                "full_name": "WhatsApp Farmer",
                "phone_number": "+919876543210",
                "whatsapp_url": "https://wa.me/919876543210",
            },
        )

        self.assertIn(response.status_code, [200, 400])

        if response.status_code == 200:
            self.assertEqual(
                response.json()["data"]["user"]["whatsapp_url"],
                "https://wa.me/919876543210",
            )


if __name__ == "__main__":
    unittest.main()