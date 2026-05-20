"""Tests for JSON schema validation against known good/bad outputs."""

import json
import unittest
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).parent.parent / "cormorant" / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text())


class TestCaseBriefSchema(unittest.TestCase):

    def setUp(self):
        self.schema = load_schema("case_brief.json")

    def test_valid_case_brief(self):
        brief = {
            "topic": "AI Semiconductor Investment",
            "decision": "Portfolio allocation for mid-size PE fund",
            "audience": "internal investment team",
            "framework": "market_research_trend_forecasting",
            "thesis_hypothesis": "Demand is durable.",
            "narrative_arc": ["Thesis valid", "Timing off", "Overhyped"],
            "scope": {
                "geography": "global",
                "time_horizon": "6-12 months",
                "depth": "full",
            },
            "emphasis": ["US-China dynamics"],
            "exclude": ["consumer electronics"],
            "created_at": "2026-05-14T09:00:00",
        }
        jsonschema.validate(brief, self.schema)

    def test_invalid_framework(self):
        brief = {
            "topic": "AI",
            "decision": "X",
            "audience": "X",
            "framework": "not_a_real_framework",
            "thesis_hypothesis": "X",
            "narrative_arc": ["A", "B"],
            "scope": {"geography": "global", "time_horizon": "1y", "depth": "full"},
            "emphasis": [],
            "exclude": [],
            "created_at": "2026-01-01",
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(brief, self.schema)

    def test_missing_required_field(self):
        brief = {"topic": "AI"}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(brief, self.schema)


class TestPlanSchema(unittest.TestCase):

    def setUp(self):
        self.schema = load_schema("plan.json")

    def test_valid_plan(self):
        plan = {
            "angles": [
                {
                    "id": f"S0{i}",
                    "title": f"Section {i}",
                    "key_questions": ["Q1", "Q2"],
                    "search_seeds": ["seed 1", "seed 2"],
                    "priority": 10 - i,
                    "depends_on": [],
                }
                for i in range(1, 9)
            ],
            "execution_order": [f"S0{i}" for i in range(1, 9)],
        }
        jsonschema.validate(plan, self.schema)

    def test_wrong_angle_count(self):
        plan = {
            "angles": [
                {
                    "id": "S01",
                    "title": "Only one",
                    "key_questions": ["Q"],
                    "search_seeds": ["s"],
                    "priority": 10,
                    "depends_on": [],
                }
            ],
            "execution_order": ["S01"],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(plan, self.schema)


class TestClaimsSchema(unittest.TestCase):

    def setUp(self):
        self.schema = load_schema("claims.json")

    def test_valid_claims(self):
        data = {
            "claims": [
                {
                    "claim": "NVIDIA data center revenue grew 154% YoY",
                    "source_url": "https://reuters.com/article/123",
                    "source_date": "2024-05",
                    "confidence": "high",
                    "supports_thesis": True,
                    "quote": "NVIDIA reported 154% growth",
                }
            ],
            "evidence_quality": "strong",
            "gaps": ["Competitor breakdown not available"],
        }
        jsonschema.validate(data, self.schema)

    def test_null_supports_thesis_allowed(self):
        data = {
            "claims": [
                {
                    "claim": "Market is growing",
                    "source_url": "https://ft.com/x",
                    "source_date": "2024-01",
                    "confidence": "medium",
                    "supports_thesis": None,
                }
            ],
            "evidence_quality": "adequate",
            "gaps": [],
        }
        jsonschema.validate(data, self.schema)

    def test_invalid_confidence_value(self):
        data = {
            "claims": [
                {
                    "claim": "X",
                    "source_url": "https://x.com",
                    "source_date": "2024-01",
                    "confidence": "very_high",
                    "supports_thesis": True,
                }
            ],
            "evidence_quality": "strong",
            "gaps": [],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema)

    def test_invalid_evidence_quality(self):
        data = {
            "claims": [],
            "evidence_quality": "excellent",
            "gaps": [],
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema)


class TestContradictionsSchema(unittest.TestCase):

    def setUp(self):
        self.schema = load_schema("contradictions.json")

    def test_valid_contradictions(self):
        data = {
            "confirmed_claims": ["Claim A", "Claim B"],
            "contradictions": [
                {
                    "claim_a": "Source A says X",
                    "claim_b": "Source B says Y",
                    "source_a_tier": 1,
                    "source_b_tier": 2,
                    "resolution": "Source A (Tier 1) wins",
                    "is_real_contradiction": True,
                }
            ],
            "gaps": ["Missing data on X"],
            "evidence_quality": "adequate",
            "re_search_needed": False,
            "re_search_suggestions": [],
            "numerical_sanity_flags": [],
        }
        jsonschema.validate(data, self.schema)

    def test_empty_contradictions_valid(self):
        data = {
            "confirmed_claims": [],
            "contradictions": [],
            "gaps": [],
            "evidence_quality": "strong",
            "re_search_needed": False,
            "re_search_suggestions": [],
            "numerical_sanity_flags": [],
        }
        jsonschema.validate(data, self.schema)


if __name__ == "__main__":
    unittest.main()
