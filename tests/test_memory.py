"""Tests for Living Brief updates, token cap enforcement, and atomic writes."""

import os
import tempfile
import unittest
from pathlib import Path

from cormorant.memory import (
    GRANULAR_MAX_ITEMS,
    apply_brief_delta,
    count_tokens,
    init_living_brief,
    read_living_brief,
    _atomic_write,
    _parse_brief,
    _render_brief,
)


class TestAtomicWrite(unittest.TestCase):

    def test_atomic_write_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            _atomic_write(path, "hello world")
            self.assertEqual(path.read_text(), "hello world")

    def test_atomic_write_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            _atomic_write(path, "first")
            _atomic_write(path, "second")
            self.assertEqual(path.read_text(), "second")

    def test_atomic_write_no_temp_file_left(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            _atomic_write(path, "content")
            tmp_files = [f for f in os.listdir(tmpdir) if f.startswith(".tmp_")]
            self.assertEqual(tmp_files, [])


class TestLivingBrief(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_dir = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_init_creates_brief(self):
        init_living_brief(self.project_dir, "AI Chips", "Demand is durable.")
        brief = read_living_brief(self.project_dir)
        self.assertIn("AI Chips", brief)
        self.assertIn("Demand is durable.", brief)
        self.assertIn("LIVING BRIEF", brief)

    def test_parse_and_render_roundtrip(self):
        init_living_brief(self.project_dir, "Test Topic", "Test thesis.")
        text = read_living_brief(self.project_dir)
        parsed = _parse_brief(text)
        rendered = _render_brief(parsed)
        parsed2 = _parse_brief(rendered)
        self.assertEqual(parsed["thesis"], parsed2["thesis"])
        self.assertEqual(parsed["topic"], parsed2["topic"])

    def test_delta_adds_confirmed_facts(self):
        init_living_brief(self.project_dir, "Test", "Thesis here.")
        apply_brief_delta(self.project_dir, {
            "confirmed_add": ["Fact A from reuters.com", "Fact B from ft.com"],
            "confirmed_drop": [],
            "thesis_nuance": "",
            "contradictions_add": [],
            "contradictions_resolved": [],
            "section_complete": {
                "id": "S01",
                "title": "Demand",
                "one_liner": "Demand is strong.",
            },
            "new_angles_discovered": [],
        })
        brief = read_living_brief(self.project_dir)
        self.assertIn("Fact A from reuters.com", brief)
        self.assertIn("Fact B from ft.com", brief)
        self.assertIn("S01", brief)

    def test_confirmed_cap_enforced(self):
        init_living_brief(self.project_dir, "Test", "Thesis.")
        # Add 12 facts — should cap at GRANULAR_MAX_ITEMS (10)
        for i in range(12):
            apply_brief_delta(self.project_dir, {
                "confirmed_add": [f"Fact {i:02d}"],
                "confirmed_drop": [],
                "thesis_nuance": "",
                "contradictions_add": [],
                "contradictions_resolved": [],
                "section_complete": {},
                "new_angles_discovered": [],
            })
        parsed = _parse_brief(read_living_brief(self.project_dir))
        self.assertLessEqual(len(parsed["granular"]), GRANULAR_MAX_ITEMS)

    def test_thesis_nuance_appended_not_replaced(self):
        init_living_brief(self.project_dir, "Test", "Original thesis.")
        apply_brief_delta(self.project_dir, {
            "confirmed_add": [],
            "confirmed_drop": [],
            "thesis_nuance": "Additional nuance.",
            "contradictions_add": [],
            "contradictions_resolved": [],
            "section_complete": {},
            "new_angles_discovered": [],
        })
        brief = read_living_brief(self.project_dir)
        self.assertIn("Original thesis.", brief)
        self.assertIn("Additional nuance.", brief)

    def test_token_count_reasonable(self):
        text = "Hello world this is a test"
        tokens = count_tokens(text)
        # Rough check: 6 words ~ 6-8 tokens
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 20)

    def test_contradiction_add_and_resolve(self):
        init_living_brief(self.project_dir, "Test", "Thesis.")
        apply_brief_delta(self.project_dir, {
            "confirmed_add": [],
            "confirmed_drop": [],
            "thesis_nuance": "",
            "contradictions_add": ["Source A says X, Source B says Y"],
            "contradictions_resolved": [],
            "section_complete": {},
            "new_angles_discovered": [],
        })
        brief = read_living_brief(self.project_dir)
        self.assertIn("Source A says X", brief)

        # Now resolve it
        apply_brief_delta(self.project_dir, {
            "confirmed_add": [],
            "confirmed_drop": [],
            "thesis_nuance": "",
            "contradictions_add": [],
            "contradictions_resolved": ["Source A says X"],
            "section_complete": {},
            "new_angles_discovered": [],
        })
        brief2 = read_living_brief(self.project_dir)
        self.assertNotIn("Source A says X", brief2)


if __name__ == "__main__":
    unittest.main()
