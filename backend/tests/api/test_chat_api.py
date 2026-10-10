"""Tests for Chatbot and RAG Integration API."""

import unittest
from tests.conftest import get_auth_headers, test_client


class TestChatAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers = get_auth_headers("farmer_chat_test@farmshield.org", role="farmer")
        # Create a test batch for Paddy
        batch_payload = {
            "crop_id": "paddy_grain_ambient",
            "custom_batch_name": "Paddy Grain Bag Stack 1",
            "quantity_kg": 4000.0,
            "harvest_date": "2026-10-01",
            "storage_start_date": "2026-10-05",
        }
        res = test_client.post("/api/v1/batches", json=batch_payload, headers=cls.headers)
        cls.batch_id = res.json()["data"]["batch_id"]

    def test_01_create_conversation(self):
        payload = {
            "title": "Paddy Storage Consultation",
            "batch_id": self.batch_id,
            "language": "en",
        }
        res = test_client.post("/api/v1/chat/conversations", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.__class__.conversation_id = data["conversation_id"]
        self.assertEqual(data["batch_id"], self.batch_id)

    def test_02_post_chat_message_with_rag_retrieval(self):
        convo_id = getattr(self.__class__, "conversation_id", None)
        self.assertIsNotNone(convo_id)

        payload = {
            "message": "How can I protect my stored paddy from rice weevil using neem leaves?",
            "batch_id": self.batch_id,
            "language": "en",
        }
        res = test_client.post(
            f"/api/v1/chat/conversations/{convo_id}/messages",
            json=payload,
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["role"], "assistant")
        self.assertIn("content", data)
        # Check source references are returned
        sources = data["sources"]
        self.assertGreaterEqual(len(sources), 1)
        # Check either crop profile or traditional knowledge is referenced
        source_titles = [s["title"] for s in sources]
        self.assertTrue(any("Paddy" in t or "Neem" in t for t in source_titles))

    def test_03_list_conversation_messages(self):
        convo_id = getattr(self.__class__, "conversation_id", None)
        res = test_client.get(
            f"/api/v1/chat/conversations/{convo_id}/messages",
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        msgs = res.json()["data"]
        self.assertGreaterEqual(len(msgs), 2)  # User question and assistant response


if __name__ == "__main__":
    unittest.main()
