"""Comprehensive Automated Test Suite for Threshold Alerts and Farmer-Specific WhatsApp Delivery.

Verifies:
1. Temperature above configured maximum creates an alert.
2. Reading below configured minimum creates an alert when minimum is defined.
3. Safe reading does not create a new violation.
4. Correct farmer is selected from batch owner.
5. WhatsApp uses farmer's profile number rather than hardcoded number.
6. Preferred language and traditional guidance are included in the outgoing message.
7. Missing or invalid phone numbers are handled safely without losing reading.
8. Twilio errors are recorded on the alert and notification log without failing sensor save.
9. Duplicate notifications are prevented for continuously active violation (cooldown test).
10. Dashboard alert and delivery statuses reflect backend results.
"""

import unittest
from unittest.mock import AsyncMock, patch

from app.integrations.whatsapp_client import WhatsAppDeliveryResult
from app.repositories.alert_repository import AlertRepository
from app.repositories.sensor_repository import SensorRepository
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.repositories.user_repository import UserRepository
from tests.conftest import get_auth_headers, test_client


class TestThresholdWhatsAppAlerts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Register a specific test farmer with 10-digit phone and Telugu preferred language
        cls.headers_farmer = get_auth_headers("farmer_ramu_test@farmshield.org", role="farmer")
        # Update profile to have phone number and preferred language
        me_res = test_client.get("/api/v1/auth/me", headers=cls.headers_farmer)
        cls.farmer_id = me_res.json()["data"]["id"]

        update_payload = {
            "full_name": "Ramu Farmer",
            "phone_number": "7386587706",  # 10 digits without +91 to verify auto-normalization
            "preferred_language": "te",  # Telugu
            "village_or_location": "Vizag Granary",
        }
        res_update = test_client.patch("/api/v1/auth/me", json=update_payload, headers=cls.headers_farmer)
        assert res_update.status_code == 200

        # Create a Wheat batch (Safe Temp: 15.0°C - 22.0°C, RH: 50.0% - 65.0%, Moisture: 11.5%)
        batch_payload = {
            "crop_id": "wheat_grain_ambient",
            "custom_batch_name": "Wheat - Oct 2026 Harvest",
            "quantity_kg": 2500.0,
            "harvest_date": "2026-10-01",
            "storage_start_date": "2026-10-05",
            "storage_structure_type": "Metallic Silo",
            "storage_location": "Farm Main Storage",
        }
        res_batch = test_client.post("/api/v1/batches", json=batch_payload, headers=cls.headers_farmer)
        assert res_batch.status_code == 200
        cls.batch_id = res_batch.json()["data"]["batch_id"]

    def test_01_temperature_above_configured_maximum_creates_alert(self):
        """1. A temperature above the configured maximum (e.g. 24.5°C > 22.0°C for wheat) creates an alert."""
        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 24.5,
            "relative_humidity_percent": 58.0,
            "sensor_id": "sensor_temp_high_01",
            "provenance": "hardware_sensor",
        }

        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            mock_send.return_value = WhatsAppDeliveryResult(
                success=True,
                status="accepted",
                message_sid="SM1234567890",
                recipient_masked="+91 7386****06",
            )
            res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers_farmer)
            self.assertEqual(res.status_code, 200)

        # Check alert is created in DB
        alerts = AlertRepository.list_by_batch(self.batch_id, status="active")
        temp_alerts = [a for a in alerts if a["condition_type"] == "temperature_high"]
        self.assertEqual(len(temp_alerts), 1)
        alert = temp_alerts[0]
        self.assertEqual(alert["measured_value"], 24.5)
        self.assertEqual(alert["target_threshold"], 22.0)
        self.assertEqual(alert["target_range_min"], 15.0)
        self.assertEqual(alert["target_range_max"], 22.0)
        self.assertEqual(alert["whatsapp_delivery_status"], "accepted")
        self.assertTrue(alert["whatsapp_notified"])

    def test_02_temperature_below_configured_minimum_creates_alert(self):
        """2. A reading below the configured minimum (e.g. 12.0°C < 15.0°C for wheat) creates an alert."""
        # Clean up any active temperature alerts first
        for a in AlertRepository.list_by_batch(self.batch_id, status="active"):
            AlertRepository.update_status(a["alert_id"], status="resolved")

        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 12.0,
            "relative_humidity_percent": 55.0,
            "sensor_id": "sensor_temp_low_01",
            "provenance": "hardware_sensor",
        }

        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            mock_send.return_value = WhatsAppDeliveryResult(
                success=True,
                status="accepted",
                message_sid="SM_LOW_123",
                recipient_masked="+91 7386****06",
            )
            res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers_farmer)
            self.assertEqual(res.status_code, 200)

        alerts = AlertRepository.list_by_batch(self.batch_id, status="active")
        low_alerts = [a for a in alerts if a["condition_type"] == "temperature_low"]
        self.assertEqual(len(low_alerts), 1)
        self.assertEqual(low_alerts[0]["measured_value"], 12.0)
        self.assertEqual(low_alerts[0]["target_threshold"], 15.0)

    def test_03_safe_reading_does_not_create_violation_and_resolves_open(self):
        """3. A safe reading within target bounds (18.0°C, 58% RH) does not create violations and auto-resolves existing."""
        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 18.0,
            "relative_humidity_percent": 58.0,
            "sensor_id": "sensor_safe_01",
            "provenance": "hardware_sensor",
        }

        res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers_farmer)
        self.assertEqual(res.status_code, 200)

        # All active alerts should now be resolved
        active_alerts = AlertRepository.list_by_batch(self.batch_id, status="active")
        self.assertEqual(len(active_alerts), 0)

    def test_04_correct_farmer_selected_from_batch_owner(self):
        """4. The correct farmer is retrieved from the batch's owner."""
        # Create an alert via high humidity reading (72% > max 65%)
        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 18.0,
            "relative_humidity_percent": 72.0,
            "sensor_id": "sensor_rh_high_01",
            "provenance": "hardware_sensor",
        }

        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            mock_send.return_value = WhatsAppDeliveryResult(
                success=True,
                status="accepted",
                message_sid="SM_RH_001",
                recipient_masked="+91 7386****06",
            )
            res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers_farmer)
            self.assertEqual(res.status_code, 200)

            # Assert send_alert_notification was called with farmer's normalized phone
            self.assertTrue(mock_send.called)
            call_kwargs = mock_send.call_args.kwargs
            self.assertEqual(call_kwargs["phone_number"], "+917386587706")
            self.assertEqual(call_kwargs["crop_name"], "Wheat")
            self.assertEqual(call_kwargs["batch_name"], "Wheat - Oct 2026 Harvest")

        # Verify alert document stores the farmer_id
        active_alerts = AlertRepository.list_by_batch(self.batch_id, status="active")
        rh_alerts = [a for a in active_alerts if a["condition_type"] == "humidity_high"]
        self.assertEqual(len(rh_alerts), 1)
        self.assertEqual(rh_alerts[0]["farmer_id"], self.farmer_id)

    def test_05_whatsapp_uses_farmer_profile_number_not_hardcoded(self):
        """5. WhatsApp alert uses the farmer's registered profile phone number."""
        # Register Farmer B with a different number
        headers_b = get_auth_headers("farmer_distinct_test@farmshield.org", role="farmer")
        test_client.patch(
            "/api/v1/auth/me",
            json={"phone_number": "+919848012345", "full_name": "Farmer B"},
            headers=headers_b,
        )

        batch_b_res = test_client.post(
            "/api/v1/batches",
            json={
                "crop_id": "wheat_grain_ambient",
                "custom_batch_name": "Wheat B",
                "quantity_kg": 1000.0,
                "harvest_date": "2026-10-01",
                "storage_start_date": "2026-10-02",
                "storage_structure_type": "Metallic Silo",
                "storage_location": "B Silo",
            },
            headers=headers_b,
        )
        batch_b_id = batch_b_res.json()["data"]["batch_id"]

        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            mock_send.return_value = WhatsAppDeliveryResult(
                success=True,
                status="accepted",
                message_sid="SM_B_001",
                recipient_masked="+91 9848****45",
            )
            test_client.post(
                f"/api/v1/batches/{batch_b_id}/readings",
                json={
                    "batch_id": batch_b_id,
                    "temperature_c": 28.0,
                    "relative_humidity_percent": 60.0,
                },
                headers=headers_b,
            )
            self.assertTrue(mock_send.called)
            self.assertEqual(mock_send.call_args.kwargs["phone_number"], "+919848012345")

    def test_06_preferred_language_and_traditional_guidance_included(self):
        """6. Preferred language (te) and traditional guidance (Pusa Bin / ITK) are included in message dispatch."""
        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            mock_send.return_value = WhatsAppDeliveryResult(
                success=True,
                status="accepted",
                message_sid="SM_LANG_001",
                recipient_masked="+91 7386****06",
            )
            # Resolve old alerts
            for a in AlertRepository.list_by_batch(self.batch_id, status="active"):
                AlertRepository.update_status(a["alert_id"], status="resolved")

            test_client.post(
                f"/api/v1/batches/{self.batch_id}/readings",
                json={
                    "batch_id": self.batch_id,
                    "temperature_c": 26.0,
                    "relative_humidity_percent": 60.0,
                },
                headers=self.headers_farmer,
            )

            self.assertTrue(mock_send.called)
            call_kwargs = mock_send.call_args.kwargs
            # Preferred language is farmer's language: Telugu
            self.assertEqual(call_kwargs["preferred_language"], "te")
            # Traditional guidance is non-empty and retrieved from project RAG knowledge
            self.assertTrue(len(call_kwargs["traditional_guidance"]) > 0)
            self.assertTrue(
                any(keyword in call_kwargs["traditional_guidance"] for keyword in ["Pusa Bin", "Agricultural Research", "ICAR", "ITK", "storage"])
            )

    def test_07_missing_or_invalid_phone_handled_safely(self):
        """7. Missing or invalid phone numbers are handled safely without crashing sensor save."""
        headers_c = get_auth_headers("farmer_no_phone@farmshield.org", role="farmer")
        test_client.patch(
            "/api/v1/auth/me",
            json={"phone_number": "invalid-letters-123", "full_name": "Farmer C"},
            headers=headers_c,
        )

        batch_c_res = test_client.post(
            "/api/v1/batches",
            json={
                "crop_id": "wheat_grain_ambient",
                "custom_batch_name": "Wheat No Phone",
                "quantity_kg": 1000.0,
                "harvest_date": "2026-10-01",
                "storage_start_date": "2026-10-02",
                "storage_structure_type": "Metallic Silo",
                "storage_location": "C Silo",
            },
            headers=headers_c,
        )
        batch_c_id = batch_c_res.json()["data"]["batch_id"]

        # Ingest violation reading
        res = test_client.post(
            f"/api/v1/batches/{batch_c_id}/readings",
            json={
                "batch_id": batch_c_id,
                "temperature_c": 29.0,
                "relative_humidity_percent": 60.0,
            },
            headers=headers_c,
        )
        # Sensor reading must succeed!
        self.assertEqual(res.status_code, 200)

        # Check alert records clear failure status
        alerts = AlertRepository.list_by_batch(batch_c_id, status="active")
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertFalse(alert["whatsapp_notified"])
        self.assertEqual(alert["whatsapp_delivery_status"], "invalid_phone_number")
        self.assertIn("not a valid E.164", alert["whatsapp_delivery_error"])

    def test_08_twilio_errors_recorded_without_losing_sensor_reading(self):
        """8. Twilio provider errors or sandbox opt-in errors are recorded without failing sensor save."""
        # Resolve active alerts on main batch
        for a in AlertRepository.list_by_batch(self.batch_id, status="active"):
            AlertRepository.update_status(a["alert_id"], status="resolved")

        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            mock_send.return_value = WhatsAppDeliveryResult(
                success=False,
                status="sandbox_not_opted_in",
                error="Twilio Sandbox opt-in required: recipient +91 7386****06 has not joined the sandbox.",
                recipient_masked="+91 7386****06",
            )

            res = test_client.post(
                f"/api/v1/batches/{self.batch_id}/readings",
                json={
                    "batch_id": self.batch_id,
                    "temperature_c": 25.5,
                    "relative_humidity_percent": 55.0,
                },
                headers=self.headers_farmer,
            )
            # Sensor reading successfully saved!
            self.assertEqual(res.status_code, 200)

            # Alert records delivery error
            alerts = AlertRepository.list_by_batch(self.batch_id, status="active")
            temp_alerts = [a for a in alerts if a["condition_type"] == "temperature_high"]
            self.assertEqual(len(temp_alerts), 1)
            self.assertFalse(temp_alerts[0]["whatsapp_notified"])
            self.assertEqual(temp_alerts[0]["whatsapp_delivery_status"], "sandbox_not_opted_in")
            self.assertIn("Sandbox opt-in required", temp_alerts[0]["whatsapp_delivery_error"])

    def test_09_duplicate_notifications_prevented_for_continuously_active_violation(self):
        """9. Duplicate notifications are prevented when violation remains continuously active within cooldown."""
        # Second reading arrives while temperature_high violation is still active (25.8°C)
        with patch("app.integrations.whatsapp_client.WhatsAppClient.send_alert_notification") as mock_send:
            res = test_client.post(
                f"/api/v1/batches/{self.batch_id}/readings",
                json={
                    "batch_id": self.batch_id,
                    "temperature_c": 25.8,
                    "relative_humidity_percent": 55.0,
                },
                headers=self.headers_farmer,
            )
            self.assertEqual(res.status_code, 200)
            # send_alert_notification should NOT be called due to cooldown
            self.assertFalse(mock_send.called)

        # Still only one active alert for temperature_high
        alerts = AlertRepository.list_by_batch(self.batch_id, status="active")
        temp_alerts = [a for a in alerts if a["condition_type"] == "temperature_high"]
        self.assertEqual(len(temp_alerts), 1)
        self.assertEqual(temp_alerts[0]["measured_value"], 25.8)

    def test_10_dashboard_and_monitoring_summary_reflects_delivery_status(self):
        """10. Monitoring summary and alert endpoints return delivery status, masked phone, and error details."""
        res = test_client.get(f"/api/v1/batches/{self.batch_id}/monitoring", headers=self.headers_farmer)
        self.assertEqual(res.status_code, 200)
        summary = res.json()["data"]

        active_alerts = summary["active_alerts"]
        self.assertGreaterEqual(len(active_alerts), 1)
        al = active_alerts[0]
        self.assertIn("whatsapp_delivery_status", al)
        self.assertIn("whatsapp_recipient_masked", al)
        self.assertIn("whatsapp_delivery_error", al)
        self.assertIn("whatsapp_last_attempt_at", al)
        self.assertEqual(al["whatsapp_recipient_masked"], "+91 7386****06")


if __name__ == "__main__":
    unittest.main()
