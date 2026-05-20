import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from cormorant.llm import LLMClient, MODELS

class TestLLMClientLite(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lite_model_definition(self):
        self.assertIn("lite", MODELS)
        self.assertEqual(MODELS["lite"]["name"], "gemini-2.5-flash-lite")
        self.assertEqual(MODELS["lite"]["rpm"], 15)
        self.assertEqual(MODELS["lite"]["rpd"], 1500)

    @patch("cormorant.llm.genai.Client")
    def test_lite_rate_gate_initialization(self, mock_genai_client):
        client = LLMClient(api_key="fake-key", project_dir=self.project_dir)
        self.assertTrue(hasattr(client, "lite_gate"))
        self.assertEqual(client.lite_gate.rpm, 15)

    @patch("cormorant.llm.genai.Client")
    def test_lite_calls_used_default(self, mock_genai_client):
        client = LLMClient(api_key="fake-key", project_dir=self.project_dir)
        self.assertEqual(client.lite_calls_used(), 0)

    @patch("cormorant.llm.genai.Client")
    def test_call_lite_chat(self, mock_genai_client):
        # Set up mocks for client and models generate
        mock_client_instance = MagicMock()
        mock_genai_client.return_value = mock_client_instance
        
        mock_response = MagicMock()
        mock_response.text = "Hello from 2.5 Flash Lite"
        mock_client_instance.models.generate_content.return_value = mock_response

        client = LLMClient(api_key="fake-key", project_dir=self.project_dir)
        
        # Call the new method
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "model", "content": "Hi"}
        ]
        
        # Stub time.sleep to run immediately
        with patch("cormorant.llm.time.sleep"):
            response = client.call_lite_chat(history, call_label="test_lite")
            
            self.assertEqual(response, "Hello from 2.5 Flash Lite")
            self.assertEqual(client.lite_calls_used(), 1)
            mock_client_instance.models.generate_content.assert_called_once()

if __name__ == "__main__":
    unittest.main()
