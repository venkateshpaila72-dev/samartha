"""Tests for Farmer Diary API."""

import unittest
from tests.conftest import get_auth_headers, test_client


class TestDiaryAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("farmer_diary_test@farmshield.org", role="farmer")
        batch_payload = {
            "crop_id": "chickpea_pulse_ambient",
            "custom_batch_name": "Kabuli Chana 2026",
            "quantity_kg": 1500.0,
            "harvest_date": "2026-03-20",
            "storage_start_date": "2026-03-25",
        }
        res = test_client.post("/api/v1/batches", json=batch_payload, headers=cls.headers)
        cls.batch_id = res.json()["data"]["batch_id"]

    def test_01_create_diary_entry(self):
        payload = {
            "batch_id": self.batch_id,
            "observation_text": "Inspected top sand layer in storage bin. No pulse beetle exit holes observed. Odor is normal and dry.",
            "observation_category": "general_inspection",
            "severity_assessment": "normal",
            "provenance": "farmer_visual_report",
        }
        res = test_client.post(f"/api/v1/batches/{self.batch_id}/diary", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.__class__.entry_id = data["entry_id"]
        self.assertEqual(data["batch_id"], self.batch_id)
        self.assertEqual(data["severity_assessment"], "normal")

    def test_02_list_batch_diary_entries(self):
        res = test_client.get(f"/api/v1/batches/{self.batch_id}/diary", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        entries = res.json()["data"]
        self.assertGreaterEqual(len(entries), 1)

    def test_03_update_diary_entry(self):
        entry_id = getattr(self.__class__, "entry_id", None)
        if entry_id:
            res = test_client.patch(
                f"/api/v1/diary/{entry_id}",
                json={"observation_text": "Updated note: Inspected bottom dunnage too."},
                headers=self.headers,
            )
            self.assertEqual(res.status_code, 200)
            self.assertIn("bottom dunnage", res.json()["data"]["observation_text"])


if __name__ == "__main__":
    unittest.main()
