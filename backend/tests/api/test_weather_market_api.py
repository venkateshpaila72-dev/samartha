"""Tests for Weather and Market Prices Endpoints."""

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

    def test_02_get_market_prices(self):
        res = test_client.get("/api/v1/market/prices?crop=Onion", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["crop_name"], "Onion")
        self.assertGreater(data["average_modal_price"], 0)
        self.assertIn("latest_prices", data)
        self.assertGreaterEqual(len(data["latest_prices"]), 1)
        self.assertIn("Lasalgaon APMC", [p["market_name"] for p in data["latest_prices"]])

    def test_03_translate_text(self):
        res = test_client.post(
            "/api/v1/translation",
            json={"text": "Storage Advisory: Temperature is high", "target_language": "hi"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["target_language"], "hi")
        self.assertIn("भंडारण सलाह", data["translated_text"])


if __name__ == "__main__":
    unittest.main()
