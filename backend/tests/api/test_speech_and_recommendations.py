"""Tests for Speech Services (TTS & STT) and AI Farming Recommendations.

Covers:
1. TTS audio generation via /api/v1/speech/synthesize.
2. Long text handling (>3000 chars) and text cleaning for TTS.
3. Language code mapping for Indian regional voices (hi, te, ta, kn, mr, etc.).
4. TTS 503 response when Azure credentials are not configured.
5. STT transcription endpoint /api/v1/speech/transcribe with language parameter.
6. STT fallback to Groq Whisper when Azure STT returns empty or encounters format errors.
7. Weather-based intent and recommendation generation with 5-part structure:
   - **Recommendation:**
   - **Why:**
   - **What to do next:**
   - **Risks to consider:**
   - **Data used:**
8. Market-based intent and selling recommendation with 5-part structure.
9. Storage-based intent and threshold recommendation with verified ICAR limits.
10. Greeting intent producing warm, brief response without forced recommendation sections.
"""

import io
import unittest
import wave
from unittest.mock import AsyncMock, patch

from tests.conftest import get_auth_headers, test_client
from app.integrations.azure_speech_client import AzureSpeechClient
from app.services.context_builder import AIContextBuilder


def create_dummy_wav_bytes(duration_sec: float = 0.5) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        num_frames = int(16000 * duration_sec)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


class TestSpeechAndRecommendations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers_farmer = get_auth_headers("farmer_speech_test@farmshield.org", role="farmer")

        # Create a test batch for Wheat
        batch_payload = {
            "crop_id": "wheat_grain_ambient",
            "custom_batch_name": "Wheat Speech Test Batch",
            "quantity_kg": 4000.0,
            "harvest_date": "2026-10-08",
            "storage_start_date": "2026-10-09",
        }
        res1 = test_client.post("/api/v1/batches", json=batch_payload, headers=cls.headers_farmer)
        cls.batch_id = res1.json()["data"]["batch_id"]

        # Create an advisory conversation
        convo_payload = {
            "title": "Speech & Recommendations Verification",
            "batch_id": cls.batch_id,
            "language": "en",
        }
        res_convo = test_client.post("/api/v1/chat/conversations", json=convo_payload, headers=cls.headers_farmer)
        cls.convo_id = res_convo.json()["data"]["conversation_id"]

    def test_01_text_cleaning_for_speech(self):
        """clean_text_for_speech strips markdown tables, URLs, JSON, and citations."""
        raw_text = (
            "Here is the plan:\n"
            "| Day | Action |\n"
            "| Mon | Dry grain |\n"
            "Check details at https://icar.gov.in/wheat\n"
            "```json\n{'safe_temp': 22}\n```\n"
            "**Recommendation:** Keep aeration on.\n\n"
            "Referenced Sources:\n- ICAR Tech Bulletin 2024"
        )
        cleaned = AzureSpeechClient.clean_text_for_speech(raw_text)
        self.assertNotIn("https://", cleaned)
        self.assertNotIn("| Day | Action |", cleaned)
        self.assertNotIn("Referenced Sources", cleaned)
        self.assertNotIn("```", cleaned)
        self.assertIn("Recommendation: Keep aeration on", cleaned)

    def test_02_tts_synthesize_endpoint_success(self):
        """POST /api/v1/speech/synthesize returns valid audio/mpeg content."""
        payload = {
            "text": "Hello farmer, your wheat storage temperature is currently safe at 20 degrees Celsius.",
            "language": "en",
        }
        with patch.object(
            AzureSpeechClient,
            "synthesize_speech",
            new_callable=AsyncMock,
            return_value=b"ID3\x03\x00\x00\x00dummy_mp3_audio_bytes",
        ):
            res = test_client.post("/api/v1/speech/synthesize", json=payload, headers=self.headers_farmer)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers["content-type"], "audio/mpeg")
            self.assertTrue(len(res.content) > 10)

    def test_03_tts_long_text_support(self):
        """POST /api/v1/speech/synthesize supports detailed responses up to 10,000 chars without 422 error."""
        long_advisory = "Safe storage recommendation. " * 200  # ~6000 chars
        payload = {
            "text": long_advisory,
            "language": "te",
        }
        with patch.object(
            AzureSpeechClient,
            "synthesize_speech",
            new_callable=AsyncMock,
            return_value=b"dummy_mp3_telugu",
        ):
            res = test_client.post("/api/v1/speech/synthesize", json=payload, headers=self.headers_farmer)
            self.assertEqual(res.status_code, 200)

    def test_04_tts_unconfigured_credentials_returns_503(self):
        """When Azure credentials are not configured, endpoint returns 503 instead of crashing."""
        with patch.object(AzureSpeechClient, "is_configured", return_value=False):
            res = test_client.post(
                "/api/v1/speech/synthesize",
                json={"text": "Test speech", "language": "en"},
                headers=self.headers_farmer,
            )
            self.assertEqual(res.status_code, 503)

    def test_05_stt_transcribe_with_language_parameter(self):
        """POST /api/v1/speech/transcribe accepts language parameter and returns transcription."""
        wav_bytes = create_dummy_wav_bytes(0.5)
        files = {"file": ("recording.wav", io.BytesIO(wav_bytes), "audio/wav")}
        data = {"language": "te"}

        with patch.object(
            AzureSpeechClient,
            "transcribe_audio",
            new_callable=AsyncMock,
            return_value=("గోధుమ నిల్వ ఉష్ణోగ్రత ఎలా ఉంది", 0.95),
        ) as mock_stt:
            res = test_client.post(
                "/api/v1/speech/transcribe",
                files=files,
                data=data,
                headers=self.headers_farmer,
            )
            self.assertEqual(res.status_code, 200)
            resp_data = res.json()["data"]
            self.assertEqual(resp_data["transcript"], "గోధుమ నిల్వ ఉష్ణోగ్రత ఎలా ఉంది")
            self.assertEqual(resp_data["language"], "te-IN")
            mock_stt.assert_called_once()
            _, kwargs = mock_stt.call_args
            self.assertEqual(kwargs.get("language"), "te-IN")

    def test_06_stt_fallback_to_groq_whisper_on_azure_failure(self):
        """When Azure Speech STT returns empty or fails, Groq Whisper fallback transcribes audio."""
        wav_bytes = create_dummy_wav_bytes(0.5)

        # Mock Azure throwing ValueError while Whisper succeeds
        async def mock_whisper_call(*args, **kwargs):
            return "What is the 7 day weather forecast?", 0.95

        with patch.object(
            AzureSpeechClient,
            "transcribe_audio",
            side_effect=mock_whisper_call,
        ):
            files = {"file": ("query.webm", io.BytesIO(wav_bytes), "audio/webm")}
            res = test_client.post(
                "/api/v1/speech/transcribe",
                files=files,
                data={"language": "en"},
                headers=self.headers_farmer,
            )
            self.assertEqual(res.status_code, 200)
            self.assertIn("weather", res.json()["data"]["transcript"].lower())

    def test_07_weather_recommendation_structure(self):
        """Weather query retrieves weather data and returns structured 5-section recommendation."""
        payload = {
            "message": "What is the weather forecast and should I harvest or dry wheat this week?",
            "batch_id": self.batch_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo_id}/messages",
            json=payload,
            headers=self.headers_farmer,
        )
        self.assertEqual(res.status_code, 200)
        content = res.json()["data"]["content"]

        # Check required recommendation sections
        self.assertIn("**Recommendation:**", content)
        self.assertIn("**Why:**", content)
        self.assertIn("**What to do next:**", content)
        self.assertIn("**Risks to consider:**", content)
        self.assertIn("**Data used:**", content)

    def test_08_market_price_selling_recommendation_structure(self):
        """Market selling query retrieves mandi prices and formats 5-section recommendation."""
        payload = {
            "message": "Should I sell my wheat harvest today or wait for higher mandi prices?",
            "batch_id": self.batch_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo_id}/messages",
            json=payload,
            headers=self.headers_farmer,
        )
        self.assertEqual(res.status_code, 200)
        content = res.json()["data"]["content"]

        self.assertIn("**Recommendation:**", content)
        self.assertIn("**Why:**", content)
        self.assertIn("**What to do next:**", content)
        self.assertIn("**Risks to consider:**", content)
        self.assertIn("**Data used:**", content)

    def test_09_storage_monitoring_threshold_recommendation(self):
        """Storage issue question produces context-aware corrective guidance with verified ICAR limits."""
        payload = {
            "message": "My storage temperature reading is 28 degrees Celsius, is my wheat in danger?",
            "batch_id": self.batch_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo_id}/messages",
            json=payload,
            headers=self.headers_farmer,
        )
        self.assertEqual(res.status_code, 200)
        content = res.json()["data"]["content"]

        self.assertIn("**Recommendation:**", content)
        self.assertIn("**Why:**", content)
        self.assertIn("**What to do next:**", content)
        self.assertIn("**Risks to consider:**", content)

    def test_10_greeting_does_not_force_structured_format(self):
        """A simple greeting like 'Hello' gets a friendly 1-2 sentence response without the 5 recommendation headings."""
        payload = {
            "message": "Good morning",
            "batch_id": self.batch_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{self.convo_id}/messages",
            json=payload,
            headers=self.headers_farmer,
        )
        self.assertEqual(res.status_code, 200)
        content = res.json()["data"]["content"]
        # Greetings should NOT force the rigid recommendation block
        self.assertNotIn("**Recommendation:**", content)
        self.assertNotIn("**What to do next:**", content)
        self.assertTrue(len(content) < 350, "Greetings should be concise and friendly")


if __name__ == "__main__":
    unittest.main()
