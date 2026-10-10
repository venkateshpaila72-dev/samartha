"""Tests for weather, database-backed market prices, and translation."""

import unittest
from tests.conftest import get_auth_headers, test_client


class TestWeatherMarketAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("farmer_wm_test@farmshield.org", role="farmer")

    def test_01_get_weather(self):
        res = test_client.get("/api/v1/weather?location=Nashik", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("current_temperature_c", data)
        self.assertIn("forecast", data)
        self.assertGreaterEqual(len(data["forecast"]), 1)
        self.assertIn("storage_impact_summary", data)

    def test_02_market_prices_requires_selected_crop(self):
        res = test_client.get("/api/v1/market/prices", headers=self.headers)
        self.assertEqual(res.status_code, 422)

    def test_03_market_prices_does_not_fabricate_benchmarks(self):
        res = test_client.get(
            "/api/v1/market/prices?crop=CropWithoutDataset&state=Telangana",
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["crop_name"], "CropWithoutDataset")
        self.assertEqual(data["latest_prices"], [])
        self.assertIsNone(data["average_modal_price"])
        self.assertEqual(data["freshness"], "unavailable")
        self.assertIn("No stored market-price records", data["recommendation"])

    def test_04_translate_text(self):
        res = test_client.post(
            "/api/v1/translation",
            json={"text": "Storage Advisory: Temperature is high", "target_language": "hi"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["target_language"], "hi")
        self.assertIn("भंडारण सलाह", data["translated_text"])


    def test_05_farmer_market_sync_loads_today_records_to_database(self):
        # 1. Sync market prices for Onion
        res = test_client.post(
            "/api/v1/market/sync?crop=Onion&state=Maharashtra",
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("sync_result", data)
        self.assertGreater(data["sync_result"]["records_inserted_or_updated"], 0)

        # 2. Query market prices for Onion now that it is synced
        res_prices = test_client.get(
            "/api/v1/market/prices?crop=Onion&state=Maharashtra",
            headers=self.headers,
        )
        self.assertEqual(res_prices.status_code, 200)
        price_data = res_prices.json()["data"]
        self.assertEqual(price_data["crop_name"], "Onion")
        self.assertGreater(len(price_data["latest_prices"]), 0)
        self.assertIsNotNone(price_data["average_modal_price"])
        self.assertGreater(price_data["average_modal_price"], 0)
        self.assertIn(price_data["freshness"], ["live", "cached"])
        self.assertEqual(len(price_data["forecast_prices"]), 7)


if __name__ == "__main__":
    unittest.main()
