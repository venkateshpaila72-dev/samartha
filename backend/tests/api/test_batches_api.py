"""Tests for Storage Batch Management and Data Isolation API."""

import unittest
from tests.conftest import get_auth_headers, test_client


class TestBatchesAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.farmer_a_headers = get_auth_headers("farmer_a@farmshield.org", role="farmer")
        cls.farmer_b_headers = get_auth_headers("farmer_b@farmshield.org", role="farmer")

    def test_01_create_batch_success(self):
        payload = {
            "crop_id": "paddy_grain_ambient",
            "custom_batch_name": "Kharif 2026 Sona Masoori",
            "quantity_kg": 5000.0,
            "harvest_date": "2026-10-01",
            "storage_start_date": "2026-10-05",
            "storage_structure_type": "Hermetic Pusa Bin",
            "storage_location": "East Granary",
            "initial_crop_condition": "Sun-dried to 12.5% moisture, clean and graded",
            "notes": "First harvest batch stored for 6 months",
        }
        res = test_client.post("/api/v1/batches", json=payload, headers=self.farmer_a_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["custom_batch_name"], "Kharif 2026 Sona Masoori")
        self.assertIsNotNone(data["crop_profile"])
        self.assertEqual(data["crop_profile"]["crop_id"], "paddy_grain_ambient")
        self.assertEqual(data["crop_profile"]["recommended_temperature_min_c"], 15.0)

    def test_02_create_batch_invalid_crop_id(self):
        payload = {
            "crop_id": "non_existent_crop_999",
            "custom_batch_name": "Invalid Crop Batch",
            "quantity_kg": 100.0,
            "harvest_date": "2026-10-01",
            "storage_start_date": "2026-10-05",
        }
        res = test_client.post("/api/v1/batches", json=payload, headers=self.farmer_a_headers)
        self.assertEqual(res.status_code, 400)

    def test_03_data_isolation_between_farmers(self):
        # Farmer A creates a private batch
        payload = {
            "crop_id": "wheat_grain_ambient",
            "custom_batch_name": "Farmer A Secret Wheat Stack",
            "quantity_kg": 2500.0,
            "harvest_date": "2026-04-15",
            "storage_start_date": "2026-04-20",
        }
        res_a = test_client.post("/api/v1/batches", json=payload, headers=self.farmer_a_headers)
        self.assertEqual(res_a.status_code, 200)
        batch_id = res_a.json()["data"]["batch_id"]

        # Farmer B tries to access Farmer A's batch
        res_b = test_client.get(f"/api/v1/batches/{batch_id}", headers=self.farmer_b_headers)
        self.assertEqual(res_b.status_code, 403)


if __name__ == "__main__":
    unittest.main()
