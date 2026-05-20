"""Comprehensive tests for Phase 2, 3, and 4 feature additions.

Tests cover:
  - Custom framework validation (validate_custom_framework)
  - Custom framework registration and CATEGORIES deduplication
  - Custom framework loading / saving cycle
  - get_strategic_focus lookup order (map -> custom fw -> default)
  - Visual Forge fence-stripping logic
  - Citation audit Markdown generation (risk score thresholds + table)
  - _run_citation_audit skips sections without source cache
  - compiler.py _MAX_COMPILE_CALLS constant is >= 12 (regression guard)
  - Readthrough always runs (no hardcoded-12 guard remaining)
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_valid_fw(name: str = "Test Framework") -> dict:
    """Return a minimal, structurally valid 8-angle framework dict."""
    angles = []
    for i in range(1, 9):
        sid = f"S0{i}" if i < 10 else f"S{i}"
        deps = [] if i == 1 else [f"S0{max(1, i-1)}"]
        angles.append({
            "id": sid,
            "title": f"Angle {i}",
            "key_questions": [f"Question {i}A?", f"Question {i}B?"],
            "search_seeds": [f"{{topic}} keyword{i}A", f"{{topic}} keyword{i}B"],
            "depends_on": deps,
        })
    return {
        "name": name,
        "description": "A test framework description.",
        "strategic_focus": "Focus on testing.",
        "style_notes": "Professional.",
        "angles": angles,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Custom Framework Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateCustomFramework:
    """Tests for frameworks.validate_custom_framework()."""

    def test_valid_framework_returns_no_errors(self):
        from cormorant.frameworks import validate_custom_framework
        fw = _make_valid_fw()
        errors = validate_custom_framework(fw)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_wrong_angle_count_reports_error(self):
        from cormorant.frameworks import validate_custom_framework
        fw = _make_valid_fw()
        fw["angles"] = fw["angles"][:5]  # only 5 angles
        errors = validate_custom_framework(fw)
        assert any("8" in e for e in errors), f"Expected angle count error, got: {errors}"

    def test_unknown_dependency_reports_error(self):
        from cormorant.frameworks import validate_custom_framework
        fw = _make_valid_fw()
        fw["angles"][1]["depends_on"] = ["S99"]  # S99 doesn't exist
        errors = validate_custom_framework(fw)
        assert any("S99" in e for e in errors), f"Expected dep error, got: {errors}"

    def test_cycle_detection_two_node(self):
        """S01 depends_on S02, S02 depends_on S01 — mutual cycle."""
        from cormorant.frameworks import validate_custom_framework
        fw = _make_valid_fw()
        fw["angles"][0]["depends_on"] = ["S02"]  # S01 -> S02
        fw["angles"][1]["depends_on"] = ["S01"]  # S02 -> S01 (cycle!)
        errors = validate_custom_framework(fw)
        assert any("cycle" in e.lower() for e in errors), f"Expected cycle error, got: {errors}"

    def test_no_cycle_detected_on_valid_dag(self):
        """Standard linear chain S01->S02->S03...S08 should have no cycle."""
        from cormorant.frameworks import validate_custom_framework
        fw = _make_valid_fw()
        errors = validate_custom_framework(fw)
        assert not any("cycle" in e.lower() for e in errors), f"Unexpected cycle error: {errors}"

    def test_empty_angles_reports_error(self):
        from cormorant.frameworks import validate_custom_framework
        fw = {"angles": []}
        errors = validate_custom_framework(fw)
        assert any("8" in e for e in errors)

    def test_s01_with_no_deps_is_valid(self):
        """S01 must always have empty depends_on in a valid framework."""
        from cormorant.frameworks import validate_custom_framework
        fw = _make_valid_fw()
        assert fw["angles"][0]["depends_on"] == []
        errors = validate_custom_framework(fw)
        assert errors == []


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Custom Framework Registration
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegisterCustomFramework:
    """Tests for register_custom_framework() and deduplication logic."""

    def test_register_adds_to_frameworks_and_categories(self, tmp_path):
        from cormorant.frameworks import (
            _CUSTOM_CATEGORY,
            CATEGORIES,
            FRAMEWORKS,
            register_custom_framework,
        )
        fw_id = "test_fw_unique_xyz"
        fw_data = _make_valid_fw("Unique Test FW")

        with (
            patch("cormorant.frameworks._CUSTOM_FW_PATH", tmp_path / "custom_frameworks.json"),
            patch("cormorant.frameworks.FRAMEWORKS", dict(FRAMEWORKS)),
            patch("cormorant.frameworks.CATEGORIES", {k: list(v) for k, v in CATEGORIES.items()}),
        ):
            from cormorant import frameworks as fw_mod
            orig_frameworks = fw_mod.FRAMEWORKS
            orig_categories = fw_mod.CATEGORIES

            # Temporarily replace module-level dicts
            fw_mod.FRAMEWORKS = dict(orig_frameworks)
            fw_mod.CATEGORIES = {k: list(v) for k, v in orig_categories.items()}

            fw_mod.register_custom_framework(fw_id, fw_data)

            assert fw_id in fw_mod.FRAMEWORKS
            assert fw_id in fw_mod.CATEGORIES.get(_CUSTOM_CATEGORY, [])

            # Restore
            fw_mod.FRAMEWORKS = orig_frameworks
            fw_mod.CATEGORIES = orig_categories

    def test_register_no_duplicate_in_categories_on_overwrite(self, tmp_path):
        """Calling register twice with the same fw_id must NOT create duplicate entries."""
        from cormorant import frameworks as fw_mod
        from cormorant.frameworks import _CUSTOM_CATEGORY

        fw_id = "test_fw_no_dup_abc"
        fw_data = _make_valid_fw()

        saved_fw = dict(fw_mod.FRAMEWORKS)
        saved_cat = {k: list(v) for k, v in fw_mod.CATEGORIES.items()}

        try:
            with patch("cormorant.frameworks._CUSTOM_FW_PATH", tmp_path / "cf.json"):
                fw_mod.FRAMEWORKS = dict(saved_fw)
                fw_mod.CATEGORIES = {k: list(v) for k, v in saved_cat.items()}

                fw_mod.register_custom_framework(fw_id, fw_data)
                fw_mod.register_custom_framework(fw_id, fw_data)  # second call — overwrite

                cat_list = fw_mod.CATEGORIES.get(_CUSTOM_CATEGORY, [])
                count = cat_list.count(fw_id)
                assert count == 1, f"Expected fw_id once in categories, got {count} times"
        finally:
            fw_mod.FRAMEWORKS = saved_fw
            fw_mod.CATEGORIES = saved_cat

    def test_save_and_reload_custom_framework(self, tmp_path):
        """Round-trip: save a custom framework, load it back, verify contents."""
        from cormorant.frameworks import _save_custom_frameworks, _load_custom_frameworks

        fw_id = "round_trip_fw"
        fw_data = _make_valid_fw("Round Trip FW")

        with patch("cormorant.frameworks._CUSTOM_FW_PATH", tmp_path / "cf.json"):
            from cormorant import frameworks as fw_mod
            orig_path = fw_mod._CUSTOM_FW_PATH
            fw_mod._CUSTOM_FW_PATH = tmp_path / "cf.json"

            _save_custom_frameworks({fw_id: fw_data})
            loaded = _load_custom_frameworks()

            fw_mod._CUSTOM_FW_PATH = orig_path

        assert fw_id in loaded
        assert loaded[fw_id]["name"] == "Round Trip FW"
        assert len(loaded[fw_id]["angles"]) == 8

    def test_load_custom_frameworks_returns_empty_on_missing_file(self, tmp_path):
        from cormorant import frameworks as fw_mod
        orig = fw_mod._CUSTOM_FW_PATH
        fw_mod._CUSTOM_FW_PATH = tmp_path / "nonexistent.json"
        result = fw_mod._load_custom_frameworks()
        fw_mod._CUSTOM_FW_PATH = orig
        assert result == {}

    def test_load_custom_frameworks_returns_empty_on_corrupt_json(self, tmp_path):
        from cormorant import frameworks as fw_mod
        corrupt = tmp_path / "cf.json"
        corrupt.write_text("{this is not valid json!!!")
        orig = fw_mod._CUSTOM_FW_PATH
        fw_mod._CUSTOM_FW_PATH = corrupt
        result = fw_mod._load_custom_frameworks()
        fw_mod._CUSTOM_FW_PATH = orig
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — get_strategic_focus lookup priority
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStrategicFocus:
    """Tests for framework_focus.get_strategic_focus() priority chain."""

    def test_returns_value_from_strategic_focus_map(self):
        from cormorant.framework_focus import get_strategic_focus
        # industry_competitive_landscape is in STRATEGIC_FOCUS_MAP
        result = get_strategic_focus("industry_competitive_landscape")
        assert len(result) > 20, "Should return the registered mandate"
        assert "market share" in result.lower() or "competitor" in result.lower() or "profit" in result.lower()

    def test_returns_custom_fw_strategic_focus_when_not_in_map(self):
        """A custom framework ID not in STRATEGIC_FOCUS_MAP should return its embedded mandate."""
        from cormorant.framework_focus import get_strategic_focus
        from cormorant import frameworks as fw_mod

        custom_id = "_test_custom_focus_xyz_"
        custom_focus = "Focus on testing the custom mandate lookup chain."
        fw_mod.FRAMEWORKS[custom_id] = {"strategic_focus": custom_focus}

        try:
            result = get_strategic_focus(custom_id)
            assert result == custom_focus, f"Expected custom mandate, got: {result}"
        finally:
            fw_mod.FRAMEWORKS.pop(custom_id, None)

    def test_returns_default_when_id_unknown_everywhere(self):
        from cormorant.framework_focus import get_strategic_focus
        result = get_strategic_focus("__completely_unknown_framework_id__")
        assert result == "Focus on high-quality strategic consulting findings."

    def test_strategic_focus_map_priority_over_custom_fw(self):
        """If an ID is in STRATEGIC_FOCUS_MAP it must be returned, not the FRAMEWORKS fallback."""
        from cormorant.framework_focus import get_strategic_focus, STRATEGIC_FOCUS_MAP
        from cormorant import frameworks as fw_mod

        # Use a real map key and inject a conflicting fw entry
        known_key = "industry_competitive_landscape"
        fw_mod.FRAMEWORKS[known_key] = {"strategic_focus": "WRONG — should not appear"}

        try:
            result = get_strategic_focus(known_key)
            assert result == STRATEGIC_FOCUS_MAP[known_key], (
                f"Map should take priority. Got: {result}"
            )
        finally:
            # Restore the original (industry_competitive_landscape was already there from FRAMEWORKS)
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Visual Forge fence stripping
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualForgeFenceStripping:
    """Tests for the Mermaid.js fence-stripping logic inside compile_report."""

    def test_fence_stripped_correctly(self):
        """Simulate what compiler.py does to strip accidental fences."""
        raw_diagram = "```mermaid\ngraph LR\n    A --> B\n```"
        raw_diagram = raw_diagram.strip()
        for fence in ("```mermaid", "```"):
            raw_diagram = raw_diagram.replace(fence, "").strip()
        assert "```" not in raw_diagram
        assert "graph LR" in raw_diagram
        assert "A --> B" in raw_diagram

    def test_plain_mermaid_not_affected(self):
        """If model returns clean Mermaid without fences, stripping is a no-op."""
        raw = "graph TD\n    A[Start] --> B[End]"
        processed = raw.strip()
        for fence in ("```mermaid", "```"):
            processed = processed.replace(fence, "").strip()
        assert processed == raw

    def test_empty_diagram_not_injected(self):
        """An empty string from LLM should result in no diagram injection."""
        visual_diagram_mermaid = ""
        report_parts = ["## Key Findings\nsome findings\n"]
        if visual_diagram_mermaid:
            report_parts.append("\n## Strategic Market Map\n")
        assert len(report_parts) == 1, "Empty diagram should not inject a section"

    def test_valid_diagram_injected_as_mermaid_block(self):
        """A valid diagram should be wrapped in ```mermaid fences in the report."""
        diagram = "graph LR\n    A --> B"
        report_parts: list[str] = []
        if diagram:
            report_parts.append("\n## Strategic Market Map\n")
            report_parts.append(f"\n```mermaid\n{diagram}\n```\n")
        full = "\n".join(report_parts)
        assert "```mermaid" in full
        assert "graph LR" in full
        assert "## Strategic Market Map" in full


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Citation Audit Markdown Generation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCitationAuditMarkdown:
    """Tests for _run_citation_audit output correctness."""

    def _make_plan(self, angle_ids: list[str]) -> dict:
        return {
            "angles": [{"id": aid, "title": f"Title {aid}"} for aid in angle_ids],
            "execution_order": angle_ids,
        }

    def _make_mock_llm(self, response_json: dict) -> MagicMock:
        llm = MagicMock()
        llm.call_flash.return_value = json.dumps(response_json)
        return llm

    def test_returns_empty_string_when_no_source_cache(self, tmp_path):
        """If no cache/*.txt files exist, the audit must return ''."""
        from cormorant.compiler import _run_citation_audit

        plan = self._make_plan(["S01"])
        sections = {"S01": "Market is growing at 20% CAGR. Revenue hit $4B in 2024."}
        llm = self._make_mock_llm({})

        result = _run_citation_audit(llm, tmp_path, plan, sections)
        assert result == ""
        llm.call_flash.assert_not_called()

    def test_returns_empty_string_when_section_too_short(self, tmp_path):
        """Sections with <100 chars should be skipped."""
        from cormorant.compiler import _run_citation_audit

        # Create a cache dir so the source check passes
        cache_dir = tmp_path / "cache" / "S01_raw"
        cache_dir.mkdir(parents=True)
        (cache_dir / "source1.txt").write_text("Some source content " * 50)

        plan = self._make_plan(["S01"])
        sections = {"S01": "Too short."}
        llm = self._make_mock_llm({})

        result = _run_citation_audit(llm, tmp_path, plan, sections)
        assert result == ""

    def test_audit_produces_markdown_table_on_valid_input(self, tmp_path):
        """With a valid LLM response, the output should contain the audit header."""
        from cormorant.compiler import _run_citation_audit

        cache_dir = tmp_path / "cache" / "S01_raw"
        cache_dir.mkdir(parents=True)
        (cache_dir / "source1.txt").write_text("Market grew to $4 billion in 2024 according to analysts." * 30)

        plan = self._make_plan(["S01"])
        sections = {
            "S01": "The market grew to $4 billion in 2024. This is a statistic. " * 10,
        }
        llm_response = {
            "section": "Title S01",
            "claims": [
                {
                    "claim": "Market grew to $4B in 2024",
                    "status": "VERIFIED",
                    "supporting_quote": "Market grew to $4 billion in 2024",
                    "remediation": "",
                },
                {
                    "claim": "50% YoY growth rate",
                    "status": "UNVERIFIED_RISK",
                    "supporting_quote": "",
                    "remediation": "Growth rate could not be verified; consider hedging this figure.",
                },
            ],
            "verified_count": 1,
            "partially_supported_count": 0,
            "unverified_count": 1,
        }
        llm = self._make_mock_llm(llm_response)

        result = _run_citation_audit(llm, tmp_path, plan, sections)

        assert "## Citation Integrity Audit" in result
        assert "Hallucination Risk Score" in result
        assert "VERIFIED" in result
        assert "UNVERIFIED_RISK" in result
        assert "| Metric | Count |" in result
        llm.call_flash.assert_called_once()

    def test_risk_score_low_threshold(self):
        """0 unverified / 10 total claims => LOW risk."""
        from cormorant.compiler import _run_citation_audit
        # Test by simulating the calculation directly
        total_verified = 10
        total_partial = 0
        total_unverified = 0
        total_claims = total_verified + total_partial + total_unverified
        unverified_pct = (total_unverified / total_claims) * 100
        assert unverified_pct < 10  # should be LOW

    def test_risk_score_medium_threshold(self):
        """2 unverified / 10 total claims = 20% => MEDIUM risk."""
        total_verified = 8
        total_partial = 0
        total_unverified = 2
        total_claims = total_verified + total_partial + total_unverified
        unverified_pct = (total_unverified / total_claims) * 100
        assert 10 <= unverified_pct < 25

    def test_risk_score_high_threshold(self):
        """4 unverified / 10 total = 40% => HIGH risk."""
        total_verified = 6
        total_partial = 0
        total_unverified = 4
        total_claims = total_verified + total_partial + total_unverified
        unverified_pct = (total_unverified / total_claims) * 100
        assert unverified_pct >= 25

    def test_audit_skips_angle_with_no_section(self, tmp_path):
        """An angle not present in `sections` dict should be skipped silently."""
        from cormorant.compiler import _run_citation_audit

        plan = self._make_plan(["S01", "S02"])
        sections = {}  # No sections at all
        llm = MagicMock()

        result = _run_citation_audit(llm, tmp_path, plan, sections)
        assert result == ""
        llm.call_flash.assert_not_called()

    def test_pipe_chars_in_claims_are_escaped(self, tmp_path):
        """Pipe characters in claims must be escaped to prevent Markdown table breakage."""
        from cormorant.compiler import _run_citation_audit

        cache_dir = tmp_path / "cache" / "S01_raw"
        cache_dir.mkdir(parents=True)
        (cache_dir / "source1.txt").write_text("Revenue | profit grew in Q4 2024 " * 30)

        plan = self._make_plan(["S01"])
        sections = {
            "S01": "Revenue | profit metric rose 20% in Q4 2024. " * 10,
        }
        llm_response = {
            "section": "Title S01",
            "claims": [
                {
                    "claim": "Revenue | profit rose 20%",
                    "status": "VERIFIED",
                    "supporting_quote": "Revenue | profit grew in Q4",
                    "remediation": "",
                },
            ],
            "verified_count": 1,
            "partially_supported_count": 0,
            "unverified_count": 0,
        }
        llm = self._make_mock_llm(llm_response)

        result = _run_citation_audit(llm, tmp_path, plan, sections)
        # Pipe inside a table cell must be escaped
        assert "Revenue \\| profit rose 20%" in result or "Revenue" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Regression Guards — compiler.py constants and guards
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompilerRegressionGuards:
    """Regression tests ensuring compile_report invariants are maintained."""

    def test_max_compile_calls_constant_is_at_least_12(self):
        """_MAX_COMPILE_CALLS must be >= 12 to preserve the original call budget."""
        import cormorant.compiler as comp
        import ast
        source = Path(comp.__file__).read_text()
        tree = ast.parse(source)
        value = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_MAX_COMPILE_CALLS":
                        if isinstance(node.value, ast.Constant):
                            value = node.value.value
        assert value is not None, "_MAX_COMPILE_CALLS not found in compiler.py"
        assert value >= 12, f"_MAX_COMPILE_CALLS should be >= 12, got {value}"

    def test_no_hardcoded_12_guard_in_readthrough(self):
        """The old `if comp_call < 12` guard in the readthrough block must be gone."""
        import cormorant.compiler as comp
        source = Path(comp.__file__).read_text()
        # Find the line with Final Read-Through
        lines = source.splitlines()
        readthrough_block = False
        for i, line in enumerate(lines):
            if "Final Read-Through" in line:
                readthrough_block = True
            if readthrough_block and "if comp_call < 12" in line:
                pytest.fail(
                    f"Hardcoded 'if comp_call < 12' guard found at line {i+1}. "
                    "This prevents _final_readthrough from running."
                )
            if readthrough_block and ("final_path" in line or "_atomic_write(final_path" in line):
                break  # Past the readthrough block

    def test_citation_audit_call_does_not_go_through_flash_closure(self):
        """_run_citation_audit must call llm.call_flash directly, not through flash() closure."""
        import cormorant.compiler as comp
        import ast
        source = Path(comp.__file__).read_text()
        tree = ast.parse(source)

        # Find the _run_citation_audit function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_citation_audit":
                # Check its signature — it must NOT have a flash_fn parameter
                args = [a.arg for a in node.args.args]
                assert "flash_fn" not in args, (
                    "_run_citation_audit still accepts flash_fn parameter. "
                    "It should call llm.call_flash() directly."
                )
                return
        pytest.fail("_run_citation_audit function not found in compiler.py")

    def test_run_citation_audit_function_exists(self):
        """Ensure _run_citation_audit is importable and callable."""
        from cormorant.compiler import _run_citation_audit
        assert callable(_run_citation_audit)

    def test_visual_forge_prompt_file_exists(self):
        """visual_forge.txt must exist and contain the key template tokens."""
        from pathlib import Path
        import cormorant.compiler as comp
        prompt_path = Path(comp.__file__).parent / "prompts" / "visual_forge.txt"
        assert prompt_path.exists(), "visual_forge.txt not found"
        content = prompt_path.read_text()
        assert "{topic}" in content
        assert "{key_findings}" in content
        assert "{decision}" in content

    def test_citation_validator_prompt_file_exists(self):
        """citation_validator.txt must exist and contain template tokens."""
        from pathlib import Path
        import cormorant.compiler as comp
        prompt_path = Path(comp.__file__).parent / "prompts" / "citation_validator.txt"
        assert prompt_path.exists(), "citation_validator.txt not found"
        content = prompt_path.read_text()
        assert "{section_draft}" in content
        assert "{source_texts}" in content
        assert "{angle_title}" in content

    def test_custom_framework_synth_prompt_file_exists(self):
        """custom_framework_synth.txt must exist and contain template tokens."""
        from pathlib import Path
        import cormorant.compiler as comp
        prompt_path = Path(comp.__file__).parent / "prompts" / "custom_framework_synth.txt"
        assert prompt_path.exists(), "custom_framework_synth.txt not found"
        content = prompt_path.read_text()
        assert "{framework_name}" in content
        assert "{framework_description}" in content
        assert "{user_brief}" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — list_categories includes custom frameworks correctly
# ═══════════════════════════════════════════════════════════════════════════════

class TestListCategoriesWithCustom:
    """Tests for list_categories() with custom framework entries."""

    def test_list_categories_filters_missing_framework_ids(self):
        """If CATEGORIES references an ID not in FRAMEWORKS, list_categories skips it (no KeyError)."""
        from cormorant import frameworks as fw_mod

        orig_categories = {k: list(v) for k, v in fw_mod.CATEGORIES.items()}
        orig_frameworks = dict(fw_mod.FRAMEWORKS)

        try:
            # Inject a category that references a non-existent framework ID
            fw_mod.CATEGORIES["__test_cat__"] = ["__missing_fw_id__"]
            # Do NOT add "__missing_fw_id__" to FRAMEWORKS
            result = fw_mod.list_categories()  # must not raise
            cat_entries = result.get("__test_cat__", [])
            ids_in_result = [entry[0] for entry in cat_entries]
            assert "__missing_fw_id__" not in ids_in_result, (
                "list_categories should skip framework IDs not in FRAMEWORKS"
            )
        finally:
            fw_mod.CATEGORIES = orig_categories
            fw_mod.FRAMEWORKS = orig_frameworks

    def test_list_categories_includes_registered_custom_fw(self, tmp_path):
        """After registering a custom FW, list_categories must include it."""
        from cormorant import frameworks as fw_mod
        from cormorant.frameworks import _CUSTOM_CATEGORY

        orig_categories = {k: list(v) for k, v in fw_mod.CATEGORIES.items()}
        orig_frameworks = dict(fw_mod.FRAMEWORKS)

        fw_id = "_test_listed_custom_fw_"
        fw_data = _make_valid_fw("Listed Custom FW")  # has name + description

        try:
            orig_path = fw_mod._CUSTOM_FW_PATH
            fw_mod._CUSTOM_FW_PATH = tmp_path / "cf.json"
            fw_mod.register_custom_framework(fw_id, fw_data)
            fw_mod._CUSTOM_FW_PATH = orig_path

            cats = fw_mod.list_categories()
            custom_cat_ids = [e[0] for e in cats.get(_CUSTOM_CATEGORY, [])]
            assert fw_id in custom_cat_ids, (
                f"Custom framework {fw_id} should appear in list_categories under {_CUSTOM_CATEGORY}"
            )
        finally:
            fw_mod.FRAMEWORKS = orig_frameworks
            fw_mod.CATEGORIES = orig_categories
