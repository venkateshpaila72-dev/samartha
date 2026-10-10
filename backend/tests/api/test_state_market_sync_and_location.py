"""Unit and Integration tests for state-restricted market synchronization and location detection."""

import unittest
from tests.conftest import test_client
from app.core.state_normalizer import normalize_state_name, CANONICAL_STATES, STATE_ALIASES
from app.integrations.market_ingestion_client import generate_today_mandi_observations


class TestStateMarketSyncAndLocation(unittest.TestCase):
    def test_01_state_normalizer_canonical_and_aliases(self):
        self.assertEqual(normalize_state_name("AP"), "Andhra Pradesh")
        self.assertEqual(normalize_state_name("in-tg"), "Telangana")
        self.assertEqual(normalize_state_name("telangana"), "Telangana")
        self.assertEqual(normalize_state_name("MH"), "Maharashtra")
        self.assertEqual(normalize_state_name("KA"), "Karnataka")
        self.assertEqual(normalize_state_name("tn"), "Tamil Nadu")
        self.assertEqual(normalize_state_name("UP"), "Uttar Pradesh")
        self.assertEqual(normalize_state_name("wb"), "West Bengal")
        self.assertEqual(normalize_state_name(None), None)
        self.assertEqual(normalize_state_name(""), None)

    def test_02_reverse_geocode_resolves_location(self):
        # Hyderabad coordinates
        res = test_client.get("/api/v1/auth/reverse-geocode?latitude=17.385&longitude=78.4867")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(data["state"], "Telangana")
        self.assertIn("district", data)

    def test_03_registration_persists_state_and_district(self):
        email = "state_farmer_1@farmshield.org"
        reg_payload = {
            "email": email,
            "password": "Password123!",
            "full_name": "Ramesh Rao",
            "preferred_language": "te",
            "state": "Telangana",
            "district": "Warangal",
            "selected_crop": "Tomato",
        }
        res = test_client.post("/api/v1/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        token = res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify /auth/me returns persisted state and district
        me_res = test_client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()["data"]
        self.assertEqual(me_data["state"], "Telangana")
        self.assertEqual(me_data["district"], "Warangal")
        self.assertEqual(me_data["selected_crop"], "Tomato")

    def test_04_profile_update_normalizes_state(self):
        email = "state_farmer_2@farmshield.org"
        reg_payload = {
            "email": email,
            "password": "Password123!",
            "full_name": "Sita Devi",
            "preferred_language": "en",
        }
        res = test_client.post("/api/v1/auth/register", json=reg_payload)
        token = res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update profile with alias 'AP'
        patch_res = test_client.patch(
            "/api/v1/auth/me",
            json={"state": "AP", "district": "Guntur", "selected_crop": "Chilli"},
            headers=headers,
        )
        self.assertEqual(patch_res.status_code, 200)
        patch_data = patch_res.json()["data"]
        self.assertEqual(patch_data["state"], "Andhra Pradesh")
        self.assertEqual(patch_data["district"], "Guntur")
        self.assertEqual(patch_data["selected_crop"], "Chilli")

    def test_05_market_sync_requires_profile_state(self):
        email = "no_state_farmer@farmshield.org"
        reg_payload = {
            "email": email,
            "password": "Password123!",
            "full_name": "State Missing Farmer",
            "preferred_language": "en",
            "state": None,
        }
        res = test_client.post("/api/v1/auth/register", json=reg_payload)
        token = res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to sync without state configured
        sync_res = test_client.post("/api/v1/market/sync?crop=Tomato", headers=headers)
        self.assertEqual(sync_res.status_code, 400)
        self.assertIn("Farmer state is not configured in your profile", sync_res.json()["detail"])

    def test_06_market_sync_enforces_strict_state_isolation(self):
        email = "isolated_farmer@farmshield.org"
        reg_payload = {
            "email": email,
            "password": "Password123!",
            "full_name": "Karnataka Farmer",
            "preferred_language": "kn",
            "state": "Karnataka",
            "district": "Kolar",
            "selected_crop": "Tomato",
        }
        res = test_client.post("/api/v1/auth/register", json=reg_payload)
        token = res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Sync market prices for Karnataka farmer
        sync_res = test_client.post("/api/v1/market/sync?crop=Tomato", headers=headers)
        self.assertEqual(sync_res.status_code, 200)
        sync_data = sync_res.json()["data"]
        self.assertGreater(sync_data["sync_result"]["records_inserted_or_updated"], 0)

        # Check records in generate_today_mandi_observations for Karnataka
        karnataka_records = generate_today_mandi_observations("Tomato", state="Karnataka")
        for rec in karnataka_records:
            self.assertEqual(rec["state"], "Karnataka")

        # Verify /auth/me now has last_market_sync_at recorded
        me_res = test_client.get("/api/v1/auth/me", headers=headers)
        self.assertIsNotNone(me_res.json()["data"]["last_market_sync_at"])
        self.assertIsNotNone(me_res.json()["data"]["last_market_sync_summary"])

    def test_07_unauthenticated_sync_rejected(self):
        res = test_client.post("/api/v1/market/sync?crop=Tomato")
        self.assertEqual(res.status_code, 401)
