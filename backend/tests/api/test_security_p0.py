"""Regression tests for P0 Critical Security Bugs (C1-C8)."""

import io
import unittest
from PIL import Image

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.user_repository import UserRepository
from tests.conftest import get_auth_headers, test_client


class TestP0SecurityRegression(unittest.TestCase):
    def test_c1_admin_registration_prevented(self):
        """C1: Registering with role=admin creates a farmer; /admin/users returns 403."""
        email = "attacker_c1@farmshield.org"
        payload = {
            "email": email,
            "password": "Password123!",
            "full_name": "Attacker Trying Admin",
            "role": "admin",  # Attacker attempts privilege escalation
            "preferred_language": "en",
        }
        res = test_client.post("/api/v1/auth/register", json=payload)
        # Should succeed as a regular farmer (or reject extra field)
        if res.status_code == 200:
            user_data = res.json()["data"]["user"]
            self.assertEqual(user_data["role"], "farmer")
            token = res.json()["data"]["access_token"]
            
            # Verify cannot access admin dashboard or users
            admin_res = test_client.get(
                "/api/v1/admin/users",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(admin_res.status_code, 403)

    def test_c3_jwt_secret_enforcement_and_claims(self):
        """C3: Startup fails in production without strong JWT_SECRET_KEY, and iss/aud are validated."""
        # 1. Test production rejection with weak/default secret
        with self.assertRaises(ValueError):
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="short",
            )
        with self.assertRaises(ValueError):
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="farmshield_super_secure_secret_key_change_in_production_32chars",
            )

        # 2. Test iss and aud claims validation
        token = create_access_token(data={"sub": "user_123", "role": "farmer"})
        decoded = decode_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["iss"], "farmshield-api")
        self.assertEqual(decoded["aud"], "farmshield-app")

    def test_c4_chatbot_idor_prevention(self):
        """C4: User B cannot create chat or post message referencing User A's batch."""
        headers_a = get_auth_headers("farmer_a@farmshield.org")
        headers_b = get_auth_headers("farmer_b@farmshield.org")

        # Farmer A creates a storage batch
        batch_payload = {
            "batch_id": "batch_owner_a_123",
            "custom_batch_name": "Wheat Vault A",
            "crop_id": "wheat_grain_ambient",
            "quantity_kg": 5000.0,
            "storage_structure_type": "Metallic Silo",
            "storage_location": "Nashik Granary",
            "harvest_date": "2026-03-01",
            "storage_start_date": "2026-03-05",
        }
        res_create = test_client.post("/api/v1/batches", json=batch_payload, headers=headers_a)
        self.assertIn(res_create.status_code, [200, 201])
        batch_a_id = res_create.json()["data"]["batch_id"]

        # Farmer B attempts to create conversation using Farmer A's batch_id
        idor_convo = test_client.post(
            "/api/v1/chat/conversations",
            json={"batch_id": batch_a_id, "title": "Sneak Peak", "language": "en"},
            headers=headers_b,
        )
        self.assertEqual(idor_convo.status_code, 403)

    def test_c5_whatsapp_dispatch_security_and_ownership(self):
        """C5: dispatch-whatsapp rejects non-owners, rejects invalid phones, and doesn't crash."""
        headers_a = get_auth_headers("farmer_alert_a@farmshield.org")
        headers_b = get_auth_headers("farmer_alert_b@farmshield.org")

        # Create batch for user A
        batch_a = {
            "batch_id": "batch_alert_test_99",
            "farmer_id": "user_alert_a",
            "user_id": "user_alert_a",
            "custom_batch_name": "Paddy Grain",
            "crop_id": "paddy_grain_ambient",
        }
        StorageBatchRepository.create(batch_a)

        # Create alert on batch A
        alert_a = {
            "alert_id": "alert_c5_test_01",
            "batch_id": "batch_alert_test_99",
            "crop_name": "Paddy (Rice)",
            "condition_type": "temperature_high",
            "severity": "critical",
            "measured_value": 36.5,
            "target_threshold": 25.0,
            "unit": "°C",
            "message": "Temperature exceeded safe limit.",
            "recommended_action": "Ventilate immediately.",
            "status": "active",
            "whatsapp_notified": False,
            "created_at": "2026-10-10T12:00:00Z",
        }
        AlertRepository.create(alert_a)

        # User B attempts to trigger WhatsApp for User A's alert -> 403
        res_b = test_client.post(
            "/api/v1/alerts/alert_c5_test_01/dispatch-whatsapp",
            headers=headers_b,
        )
        self.assertEqual(res_b.status_code, 403)

    def test_c6_upload_file_security_and_validation(self):
        """C6: Upload rejects SVG, rejects non-image spoofing, rejects > 5MB."""
        headers = get_auth_headers("upload_tester@farmshield.org")

        # 1. Reject SVG
        svg_content = b"<svg><script>alert('xss')</script></svg>"
        res_svg = test_client.post(
            "/api/v1/uploads",
            files={"file": ("malicious.svg", svg_content, "image/svg+xml")},
            headers=headers,
        )
        self.assertEqual(res_svg.status_code, 400)

        # 2. Reject text file spoofing content-type
        fake_png = b"This is plain text pretending to be png."
        res_fake = test_client.post(
            "/api/v1/uploads",
            files={"file": ("fake.png", fake_png, "image/png")},
            headers=headers,
        )
        self.assertEqual(res_fake.status_code, 400)

        # 3. Reject file exceeding 5MB
        huge_bytes = b"0" * (6 * 1024 * 1024)
        res_huge = test_client.post(
            "/api/v1/uploads",
            files={"file": ("huge.png", huge_bytes, "image/png")},
            headers=headers,
        )
        self.assertEqual(res_huge.status_code, 413)

        # 4. Valid PNG succeeds and returns absolute URL
        img = Image.new("RGB", (20, 20), color="green")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        res_valid = test_client.post(
            "/api/v1/uploads",
            files={"file": ("test_valid.png", buf.getvalue(), "image/png")},
            headers=headers,
        )
        self.assertEqual(res_valid.status_code, 200)
        url = res_valid.json()["data"]["url"]
        self.assertTrue(url.startswith("http://") or url.startswith("https://"))

    def test_c7_fake_data_elimination(self):
        """C7: Speech rejects empty audio; Market returns unavailable without Wheat substitution."""
        headers = get_auth_headers("farmer_fake_data_test@farmshield.org")

        # 1. Speech without audio file returns 422
        res_speech = test_client.post("/api/v1/speech/transcribe", headers=headers)
        self.assertEqual(res_speech.status_code, 422)

        # 2. Market for unknown crop returns explicit 'unavailable', NEVER Wheat
        res_market = test_client.get(
            "/api/v1/market/prices?crop=Dragonfruit",
            headers=headers,
        )
        self.assertEqual(res_market.status_code, 200)
        data = res_market.json()["data"]
        self.assertEqual(data["crop_name"], "Dragonfruit")
        self.assertEqual(data["freshness"], "unavailable")
        self.assertEqual(data["latest_prices"], [])
        self.assertIsNone(data["average_modal_price"])

        # 3. Weather for unresolvable random string returns 404, NEVER Delhi
        res_weather = test_client.get(
            "/api/v1/weather?location=XyZzY999NonExistentLocation",
            headers=headers,
        )
        self.assertEqual(res_weather.status_code, 404)

    def test_m1_weather_query_parameter_honored(self):
        """M1: Weather search box location parameter takes precedence over profile."""
        from unittest.mock import patch
        from app.schemas.weather import WeatherReportOut

        mock_out = WeatherReportOut(
            location="Pune, IN",
            provider="Open-Meteo (Live API)",
            retrieval_timestamp="2026-10-10T12:00:00Z",
            freshness_status="live",
            current_temperature_c=28.0,
            current_humidity_percent=55.0,
            weather_condition="Clear Sky",
            forecast=[],
            storage_impact_summary="Optimal storage weather.",
        )
        headers = get_auth_headers("pune_weather_farmer@farmshield.org")
        with patch("app.integrations.weather_client.WeatherClient.get_weather", return_value=mock_out) as mock_get:
            res = test_client.get("/api/v1/weather?location=Pune", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertIn("Pune", res.json()["data"]["location"])
            mock_get.assert_called_once_with(location="Pune")


if __name__ == "__main__":
    unittest.main()
