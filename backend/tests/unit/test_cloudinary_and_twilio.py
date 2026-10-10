"""Unit tests for Cloudinary, Twilio, Open-Meteo, and Pinecone RAG integrations."""

import unittest
from app.integrations.cloudinary_client import CloudinaryClient
from app.integrations.whatsapp_client import WhatsAppClient
from app.integrations.weather_client import WeatherClient, KNOWN_LOCATIONS, WMO_WEATHER_DESCRIPTIONS
from app.integrations.rag_adapter import RAGAdapter
from app.core.config import settings


class TestSynchronizedIntegrations(unittest.TestCase):
    def test_cloudinary_configuration(self):
        """Verifies Cloudinary configuration check and settings presence."""
        from unittest.mock import patch
        with patch.object(settings, "CLOUDINARY_CLOUD_NAME", "sample_cloud"), \
             patch.object(settings, "CLOUDINARY_API_KEY", "12345"), \
             patch.object(settings, "CLOUDINARY_API_SECRET", "secret"):
            is_conf = CloudinaryClient.is_configured()
            self.assertTrue(is_conf, "Cloudinary should be detected as configured")

    def test_twilio_configuration(self):
        """Verifies Twilio WhatsApp configuration check."""
        from unittest.mock import patch
        with patch.object(settings, "TWILIO_ACCOUNT_SID", "AC12345"), \
             patch.object(settings, "TWILIO_AUTH_TOKEN", "auth123"), \
             patch.object(settings, "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"):
            is_conf = WhatsAppClient.is_configured()
            self.assertTrue(is_conf, "Twilio should be detected as configured")

    def test_weather_client_mappings(self):
        """Verifies Open-Meteo coordinates lookup and WMO weather codes."""
        self.assertIn("pune", KNOWN_LOCATIONS)
        self.assertIn("new delhi", KNOWN_LOCATIONS)
        self.assertIn(0, WMO_WEATHER_DESCRIPTIONS)
        self.assertEqual(WMO_WEATHER_DESCRIPTIONS[0], "Clear Sky")

    def test_rag_hybrid_retrieval(self):
        """Verifies RAG hybrid retrieval returns valid SourceReference objects."""
        results = RAGAdapter.retrieve_relevant_knowledge(
            query="paddy moisture storage neem leaves",
            crop_name="Paddy (Rice)",
            top_k=2,
        )
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)
        for r in results:
            self.assertTrue(hasattr(r, "title"))
            self.assertTrue(hasattr(r, "source_name"))
            self.assertTrue(hasattr(r, "relevance_score"))


if __name__ == "__main__":
    unittest.main()
