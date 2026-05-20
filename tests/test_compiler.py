"""Tests for final compiled report and final readthrough in compiler."""

import json
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from cormorant.compiler import _final_readthrough


class TestFinalReadthrough(unittest.TestCase):

    def test_final_readthrough_no_edits(self):
        llm = MagicMock()
        # Mock LLM to return JSON with issues_found = False
        llm.call_flash.return_value = json.dumps({
            "issues_found": False,
            "edits": []
        })

        content = "## Section 1\nThis is content."
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            with patch("cormorant.compiler._load_prompt", return_value="Dummy prompt template"):
                result = _final_readthrough(llm, content, project_dir, max_calls=3)
                self.assertEqual(result, content)

    def test_final_readthrough_with_edits(self):
        llm = MagicMock()
        # Mock LLM to return JSON with issues_found = True and some edits
        llm.call_flash.return_value = json.dumps({
            "issues_found": True,
            "edits": [
                {"find": "This is content.", "replace": "This is corrected content."}
            ]
        })

        content = "## Section 1\nThis is content."
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            with patch("cormorant.compiler._load_prompt", return_value="Dummy prompt template"):
                result = _final_readthrough(llm, content, project_dir, max_calls=3)
                self.assertIn("This is corrected content.", result)
                self.assertNotIn("This is content.", result)


if __name__ == "__main__":
    unittest.main()
