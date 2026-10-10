"""Tests for Sensor Ingestion, Threshold Rules, and Alert Management API."""

import unittest
from tests.conftest import get_auth_headers, test_client


class TestMonitoringAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("farmer_monitoring_test@farmshield.org", role="farmer")
        # Create a test batch for Onion (Safe Temp: 25-30°C, RH: 65-72%)
        batch_payload = {
            "crop_id": "onion_bulb_ambient_ventilated",
            "custom_batch_name": "Rabi Onion Chawl 1",
            "quantity_kg": 3000.0,
            "harvest_date": "2026-04-10",
            "storage_start_date": "2026-04-15",
            "storage_structure_type": "Traditional Thatched Chawl",
            "storage_location": "Nashik Field Granary",
        }
        res = test_client.post("/api/v1/batches", json=batch_payload, headers=cls.headers)
        cls.batch_id = res.json()["data"]["batch_id"]

    def test_01_ingest_normal_reading(self):
        # Normal reading within target range (27°C, 68% RH)
        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 27.0,
            "relative_humidity_percent": 68.0,
            "crop_moisture_percent": 13.5,
            "sensor_id": "dht22_sensor_01",
            "provenance": "manual",
            "notes": "Afternoon inspection reading",
        }
        res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertTrue(data["is_temperature_in_range"])
        self.assertTrue(data["is_humidity_in_range"])

    def test_02_ingest_abnormal_reading_triggers_alert(self):
        # High temperature violation (34°C > max 30°C) and high humidity (78% > max 72%)
        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 34.0,
            "relative_humidity_percent": 78.0,
            "sensor_id": "dht22_sensor_01",
            "provenance": "simulated",
            "notes": "Hot humid afternoon spike",
        }
        res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertFalse(data["is_temperature_in_range"])
        self.assertFalse(data["is_humidity_in_range"])

        # Check alerts created
        alerts_res = test_client.get(f"/api/v1/alerts?batch_id={self.batch_id}", headers=self.headers)
        self.assertEqual(alerts_res.status_code, 200)
        alerts = alerts_res.json()["data"]
        self.assertGreaterEqual(len(alerts), 1)
        conditions = [a["condition_type"] for a in alerts]
        self.assertIn("temperature_high", conditions)

    def test_03_monitoring_summary_reflects_status(self):
        res = test_client.get(f"/api/v1/batches/{self.batch_id}/monitoring", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        summary = res.json()["data"]
        self.assertEqual(summary["batch_id"], self.batch_id)
        self.assertEqual(summary["sensor_freshness_status"], "online")
        self.assertEqual(summary["current_temperature_c"], 34.0)
        self.assertEqual(summary["target_temperature_max_c"], 30.0)
        self.assertEqual(summary["target_humidity_max_percent"], 72.0)

    def test_04_auto_resolution_when_normal(self):
        # Measurement returns back into safe range (26°C, 67% RH)
        payload = {
            "batch_id": self.batch_id,
            "temperature_c": 26.0,
            "relative_humidity_percent": 67.0,
            "sensor_id": "dht22_sensor_01",
            "provenance": "hardware_sensor",
        }
        res = test_client.post(f"/api/v1/batches/{self.batch_id}/readings", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)

        # Check that temperature_high and humidity_high alerts were automatically resolved!
        alerts_res = test_client.get(f"/api/v1/alerts?batch_id={self.batch_id}&status=active", headers=self.headers)
        self.assertEqual(alerts_res.status_code, 200)
        active_alerts = alerts_res.json()["data"]
        self.assertEqual(len(active_alerts), 0)


if __name__ == "__main__":
    unittest.main()
