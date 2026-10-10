"""Tests for AI Farmer Assistant Enhancements.

Covers:
1. Friendly greetings and language-aware replies (0 citations on greetings).
2. Relevant RAG retrieval and structured response formatting (ICAR limits, capped citations).
3. Read-aloud Speech API (synthesize speech endpoint, language mapping, error handling).
4. Harvest date intent parsing, confirmation, and database update.
5. Cross-farmer data isolation on harvest scheduling actions.
6. 7-day weather forecast with agronomic operations.
7. 30-day extended seasonal outlook with uncertainty disclaimers.
8. Market price selling recommendations with ranked mandis and transport net return.
9. Farmer profile auto_read_aloud preference persistence.
"""

import unittest
from unittest.mock import patch
from tests.conftest import get_auth_headers, test_client
from app.repositories.storage_batch_repository import StorageBatchRepository
from app.integrations.azure_speech_client import AzureSpeechClient
from app.integrations.market_client import MarketClient
from app.schemas.market import MarketPriceItem, MarketPricePoint, MarketPriceForecastPoint


class TestAIAssistantEnhancements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers_farmer1 = get_auth_headers("farmer_enhancement_1@farmshield.org", role="farmer")
        cls.headers_farmer2 = get_auth_headers("farmer_enhancement_2@farmshield.org", role="farmer")

        # Create a test batch for Farmer 1 (Wheat)
        batch_payload = {
            "crop_id": "wheat_grain_ambient",
            "custom_batch_name": "Wheat Harvest Oct 2026",
            "quantity_kg": 5000.0,
            "harvest_date": "2026-10-10",
            "storage_start_date": "2026-10-11",
        }
        res1 = test_client.post("/api/v1/batches", json=batch_payload, headers=cls.headers_farmer1)
        cls.batch1_id = res1.json()["data"]["batch_id"]

        # Create a conversation for Farmer 1
        convo_payload = {
            "title": "Wheat Storage Advice",
            "batch_id": cls.batch1_id,
            "language": "en",
        }
        res_convo = test_client.post("/api/v1/chat/conversations", json=convo_payload, headers=cls.headers_farmer1)
        cls.convo1_id = res_convo.json()["data"]["conversation_id"]

    def test_01_friendly_greeting_no_rag_citations(self):
        """Farmer saying 'Hello' should receive a warm, brief reply with ZERO RAG citations."""
        payload = {
            "message": "Hello",
            "batch_id": self.batch1_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo1_id}/messages",
            json=payload,
            headers=self.headers_farmer1,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["role"], "assistant")
        content = data["content"].lower()
        # Should contain a warm greeting
        self.assertTrue(any(g in content for g in ["hello", "hi", "welcome", "namaste", "good morning", "farm"]))
        # Crucial requirement: greetings MUST NOT have forced RAG citations
        self.assertEqual(len(data.get("sources", [])), 0, "Greetings must not dump RAG citations")

    def test_02_storage_violation_structured_response(self):
        """Storage issue query receives a structured response with ICAR guidelines and max 1-2 citations."""
        payload = {
            "message": "My wheat storage temperature is too high at 26C. What should I do?",
            "batch_id": self.batch1_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo1_id}/messages",
            json=payload,
            headers=self.headers_farmer1,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        content = data["content"]
        self.assertIn("Wheat", content)
        # Citations must be concise (at most 2 sources)
        sources = data.get("sources", [])
        self.assertLessEqual(len(sources), 2, "Citations should be concise and capped at 2 sources")

    def test_03_harvest_date_intent_prompts_confirmation(self):
        """Stating 'I want to harvest my wheat on October 18' should stage a pending_action and ask for confirmation."""
        payload = {
            "message": "I want to harvest my wheat on October 18",
            "batch_id": self.batch1_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo1_id}/messages",
            json=payload,
            headers=self.headers_farmer1,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        content = data["content"]
        self.assertIn("October 18", content)
        pending = data.get("pending_action")
        self.assertIsNotNone(pending, "Should attach a pending_action for the harvest date update")
        self.assertEqual(pending.get("action_type"), "update_harvest_date")
        self.assertEqual(pending.get("date"), "2026-10-18")
        self.assertEqual(pending.get("batch_id"), self.batch1_id)

    def test_04_harvest_date_confirmation_executes_database_update(self):
        """Replying 'Yes, confirm it' executes the pending harvest date update in repository."""
        payload = {
            "message": "Yes, confirm it",
            "batch_id": self.batch1_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo1_id}/messages",
            json=payload,
            headers=self.headers_farmer1,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        action_executed = data.get("action_executed")
        self.assertIsNotNone(action_executed, "Should record action_executed upon confirmation")
        self.assertEqual(action_executed.get("date"), "2026-10-18")

        # Verify database record actually reflects new harvest_date
        updated_batch = StorageBatchRepository.get_by_id(self.batch1_id)
        self.assertIsNotNone(updated_batch)
        self.assertEqual(updated_batch.get("harvest_date"), "2026-10-18")

    def test_05_cross_farmer_action_isolation(self):
        """Farmer 2 cannot confirm or modify Farmer 1's batch actions or conversation."""
        # Farmer 2 tries to confirm action on Farmer 1's conversation
        payload = {
            "action_type": "update_harvest_date",
            "batch_id": self.batch1_id,
            "harvest_date": "2026-10-18",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo1_id}/confirm-action",
            json=payload,
            headers=self.headers_farmer2,
        )
        self.assertIn(res.status_code, [400, 403, 404])

        # Farmer 2 tries to post message to Farmer 1's conversation
        msg_payload = {
            "message": "Hello from another farmer",
            "language": "en",
        }
        res_msg = test_client.post(
            f"/api/v1/chat/conversations/{self.convo1_id}/messages",
            json=msg_payload,
            headers=self.headers_farmer2,
        )
        self.assertIn(res_msg.status_code, [403, 404])

    def test_06_speech_synthesis_endpoint(self):
        """Speech synthesis endpoint returns MP3 or graceful 503 when unconfigured."""
        req_payload = {
            "text": "Hello, your wheat storage temperature is safe at 18 degrees Celsius.",
            "language": "en",
        }
        with patch.object(AzureSpeechClient, "is_configured", return_value=True), \
             patch.object(AzureSpeechClient, "synthesize_speech", return_value=b"FAKE_MP3_DATA"):
            res = test_client.post("/api/v1/speech/synthesize", json=req_payload, headers=self.headers_farmer1)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("content-type"), "audio/mpeg")
            self.assertEqual(res.content, b"FAKE_MP3_DATA")

        # When unconfigured, should return 503 Service Unavailable without crashing
        with patch.object(AzureSpeechClient, "is_configured", return_value=False):
            res_fail = test_client.post("/api/v1/speech/synthesize", json=req_payload, headers=self.headers_farmer1)
            self.assertEqual(res_fail.status_code, 503)

    def test_07_seven_day_weather_forecast_and_operations(self):
        """Weather endpoint returns 7-day daily forecast with agronomic operations."""
        res = test_client.get("/api/v1/weather?location=Indore", headers=self.headers_farmer1)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        seven_day = data.get("seven_day_forecast", [])
        self.assertGreaterEqual(len(seven_day), 5, "Should provide multi-day forecast items")
        day1 = seven_day[0]
        self.assertIn("date", day1)
        self.assertIn("temp_max_c", day1)
        self.assertIn("temp_min_c", day1)
        self.assertIn("precipitation_probability_percent", day1)
        self.assertIn("harvest_recommendation", day1)
        self.assertIn("drying_recommendation", day1)
        self.assertIn("irrigation_recommendation", day1)
        self.assertIn("ventilation_recommendation", day1)
        self.assertIn("pest_disease_risk", day1)

    def test_08_thirty_day_outlook_with_uncertainty_notice(self):
        """Extended outlook provides multi-week seasonal outlook with clear uncertainty disclaimers."""
        res = test_client.get("/api/v1/weather?location=Indore", headers=self.headers_farmer1)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        outlook = data.get("thirty_day_outlook")
        self.assertIsNotNone(outlook)
        self.assertTrue(len(outlook.get("periods", [])) >= 2)
        notice = outlook.get("uncertainty_level", "")
        self.assertIn("uncertainty", notice.lower())

    def test_09_market_selling_recommendation_and_ranking(self):
        """Market recommendation engine generates transparent rankings and net return calculations."""
        # Test the algorithmic recommendation generator directly with realistic mandi data
        sample_items = [
            MarketPriceItem(
                crop_name="Wheat",
                variety="Lokwan",
                market_name="Indore APMC",
                district="Indore",
                state="Madhya Pradesh",
                modal_price_per_quintal=2550.0,
                min_price_per_quintal=2400.0,
                max_price_per_quintal=2650.0,
                price_date="2026-10-10",
                source="Agmarknet APMC",
            ),
            MarketPriceItem(
                crop_name="Wheat",
                variety="Lokwan",
                market_name="Ujjain Mandi",
                district="Ujjain",
                state="Madhya Pradesh",
                modal_price_per_quintal=2620.0,
                min_price_per_quintal=2450.0,
                max_price_per_quintal=2700.0,
                price_date="2026-10-10",
                source="Agmarknet APMC",
            ),
        ]
        sample_history = [
            MarketPricePoint(date="2026-10-01", average_modal_price_per_quintal=2480.0, observations=3),
            MarketPricePoint(date="2026-10-05", average_modal_price_per_quintal=2520.0, observations=4),
            MarketPricePoint(date="2026-10-10", average_modal_price_per_quintal=2550.0, observations=5),
        ]
        sample_forecast = [
            MarketPriceForecastPoint(date="2026-10-12", predicted_modal_price_per_quintal=2570.0, lower_estimate=2520.0, upper_estimate=2620.0),
        ]

        rec = MarketClient.generate_selling_recommendation(
            crop_name="Wheat",
            items=sample_items,
            historical=sample_history,
            forecasts=sample_forecast,
            trend="upward",
            average_price=2585.0,
            storage_risk_high=False,
            quantity_quintals=50.0,
        )

        self.assertIsNotNone(rec)
        self.assertIn("Recommendation:", rec.decision_summary)
        self.assertEqual(rec.current_market_price_per_quintal, 2620.0)
        self.assertIn("storage_risk_assessment", rec.model_dump())
        self.assertIn("weather_considerations", rec.model_dump())
        self.assertIn("short_term_price_outlook", rec.model_dump())
        self.assertIn(rec.confidence_level.lower(), ["strong", "moderate", "limited"])

        ranked_options = rec.ranked_options
        self.assertGreaterEqual(len(ranked_options), 1)
        top = ranked_options[0]
        self.assertEqual(top.rank, 1)
        self.assertIsNotNone(top.estimated_net_return_per_quintal)
        self.assertIn("Ujjain", top.market_name)  # Highest price after transport

        # Also test immediate sale trigger when storage risk is high
        rec_urgent = MarketClient.generate_selling_recommendation(
            crop_name="Wheat",
            items=sample_items,
            historical=sample_history,
            forecasts=sample_forecast,
            trend="upward",
            average_price=2585.0,
            storage_risk_high=True,
            quantity_quintals=50.0,
        )
        self.assertIn("Immediate sale recommended", rec_urgent.decision_summary)

    def test_10_farmer_auto_read_aloud_preference_toggle(self):
        """Farmer can toggle and persist auto_read_aloud preference via /auth/me."""
        patch_payload = {
            "auto_read_aloud": True,
        }
        res = test_client.patch("/api/v1/auth/me", json=patch_payload, headers=self.headers_farmer1)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertTrue(data.get("auto_read_aloud"))

        # Verify GET /auth/me reflects the updated value
        me_res = test_client.get("/api/v1/auth/me", headers=self.headers_farmer1)
        self.assertEqual(me_res.status_code, 200)
        self.assertTrue(me_res.json()["data"].get("auto_read_aloud"))


if __name__ == "__main__":
    unittest.main()
