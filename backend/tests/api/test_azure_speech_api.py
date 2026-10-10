"""Tests for Azure Speech STT and TTS endpoints."""

import io
import unittest
from tests.conftest import get_auth_headers, test_client


class TestAzureSpeechAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("speech_tester@farmshield.org", role="farmer")

    def test_01_synthesize_speech_success(self):
        payload = {
            "text": "Storage observation recorded successfully. Temperature is within safe range.",
            "language": "en",
        }
        res = test_client.post("/api/v1/speech/synthesize", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("audio_base64", data)
        self.assertGreater(len(data["audio_base64"]), 10)
        self.assertEqual(data["media_type"], "audio/mpeg")
        self.assertIn("Neerja", data["voice_name"])

    def test_02_synthesize_speech_indian_languages(self):
        for lang, expected_voice in [("hi", "Swara"), ("te", "Shruti")]:
            payload = {
                "text": "नमस्ते किसान भाई",
                "language": lang,
            }
            res = test_client.post("/api/v1/speech/synthesize", json=payload, headers=self.headers)
            self.assertEqual(res.status_code, 200)
            data = res.json()["data"]
            self.assertIn(expected_voice, data["voice_name"])

    def test_03_synthesize_empty_text_rejected(self):
        payload = {"text": "   "}
        res = test_client.post("/api/v1/speech/synthesize", json=payload, headers=self.headers)
        self.assertIn(res.status_code, [400, 422])

    def test_04_transcribe_missing_file_rejected(self):
        res = test_client.post("/api/v1/speech/transcribe", headers=self.headers)
        self.assertEqual(res.status_code, 422)

    def test_05_transcribe_audio_file(self):
        dummy_audio = io.BytesIO(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        files = {"file": ("recording.wav", dummy_audio, "audio/wav")}
        res = test_client.post("/api/v1/speech/transcribe", files=files, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("transcript", data)
        self.assertIn("confidence", data)
