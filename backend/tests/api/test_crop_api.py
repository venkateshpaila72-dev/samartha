"""Tests for Crop Profiles and Matching API."""

import unittest
from tests.conftest import get_auth_headers, test_client


class TestCropAPI(unittest.TestCase):
    def test_01_list_crops(self):
        res = test_client.get("/api/v1/crops")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertGreaterEqual(len(data), 15)
        # Check Paddy and Wheat exist in seeded data
        crop_names = [c["crop_name"] for c in data]
        self.assertTrue(any("Paddy" in name for name in crop_names))
        self.assertTrue(any("Wheat" in name for name in crop_names))

    def test_02_get_crop_by_id(self):
        res = test_client.get("/api/v1/crops/paddy_grain_ambient")
        self.assertEqual(res.status_code, 200)
        crop = res.json()["data"]
        self.assertEqual(crop["crop_id"], "paddy_grain_ambient")
        self.assertEqual(crop["verification_status"], "verified")
        self.assertIn("recommended_temperature_min_c", crop)
        self.assertIn("recommended_relative_humidity_max_percent", crop)

    def test_03_match_crop_deterministic(self):
        payload = {
            "crop_name": "Wheat",
            "variety": "Bread Wheat",
            "crop_form": "Clean Threshed Wheat Grain",
            "storage_type": "Metallic Silo",
        }
        res = test_client.post("/api/v1/crops/match", json=payload)
        self.assertEqual(res.status_code, 200)
        match = res.json()["data"]
        self.assertEqual(match["matched_profile"]["crop_id"], "wheat_grain_ambient")
        self.assertEqual(match["match_confidence"], "high")
        self.assertIn("ICAR", match["applicability_explanation"])

    def test_04_admin_create_crop(self):
        admin_headers = get_auth_headers("admin_crop_test@farmshield.org", role="admin")
        payload = {
            "crop_id": "barley_grain_ambient",
            "crop_name": "Barley (Jau)",
            "crop_category": "Cereals & Grains",
            "variety": "K-125",
            "crop_form": "Threshed Clean Grain",
            "region": "Rajasthan / Haryana",
            "storage_type": "Gunny Bags / Silo",
            "intended_storage_duration": "6 to 9 months",
            "recommended_temperature_min_c": 15.0,
            "recommended_temperature_max_c": 22.0,
            "recommended_relative_humidity_min_percent": 50.0,
            "recommended_relative_humidity_max_percent": 65.0,
            "recommended_crop_moisture_percent": 12.0,
            "moisture_basis": "w.b.",
            "traditional_storage_methods": ["Neem leaf admixture"],
            "ventilation_guidance": "Aerate during dry sunny afternoons",
            "pest_prevention_guidance": "Guard against grain weevil",
            "spoilage_warning_signs": ["Musty smell"],
            "recommended_actions": ["Sun dry if moisture > 12%"],
            "source_name": "ICAR-IIWBR Karnal",
            "verification_status": "verified",
        }
        res = test_client.post("/api/v1/admin/crops", json=payload, headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["crop_id"], "barley_grain_ambient")


if __name__ == "__main__":
    unittest.main()
