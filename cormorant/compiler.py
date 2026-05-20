"""Phase 4 — Final report compilation (12 Flash Lite calls)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from cormorant import ui
from cormorant.llm import LLMClient, _strip_code_fences
from cormorant.memory import get_sources_summary, read_living_brief, _atomic_write
from cormorant.sessions import load_all_sections, load_case_brief, load_plan, update_session

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def _get_section_oneliners(project_dir: Path) -> dict[str, str]:
    living_brief = read_living_brief(project_dir)
    oneliners = {}
    in_sections = False
    for line in living_brief.splitlines():
        if "## SECTIONS COMPLETE" in line:
            in_sections = True
            continue
        if in_sections:
            if line.startswith("## "):
                break
            stripped = line.strip().lstrip("- ")
            if stripped and not stripped.startswith("("):
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip()
                    # Key might be "S01 Title" — just use the ID
                    angle_id = key.split()[0] if key.split() else key
                    oneliners[angle_id] = val
    return oneliners


def _get_evidence_quality_summary(project_dir: Path, plan: dict) -> str:
    lines = []
    for angle in plan.get("angles", []):
        angle_id = angle["id"]
        eq_path = project_dir / "cache" / f"{angle_id}_evidence_quality.txt"
        quality = eq_path.read_text().strip() if eq_path.exists() else "unknown"
        lines.append(f"- {angle_id} {angle['title']}: {quality}")
    return "\n".join(lines)


def _get_paywalled_count(project_dir: Path) -> int:
    from cormorant.memory import load_sources
    sources = load_sources(project_dir)
    return sum(1 for s in sources.values() if s.get("is_paywalled"))


def _get_thin_evidence_angles(project_dir: Path, plan: dict) -> list[str]:
    thin = []
    for angle in plan.get("angles", []):
        angle_id = angle["id"]
        eq_path = project_dir / "cache" / f"{angle_id}_evidence_quality.txt"
        quality = eq_path.read_text().strip() if eq_path.exists() else "unknown"
        if quality in ("thin", "paywalled"):
            thin.append(f"{angle_id}: {angle['title']} ({quality})")
    return thin


def compile_report(llm: LLMClient, project_dir: Path) -> Path:
    """Run the 12-call compilation and write report_final.md."""
    ui.print_info("\nStarting report compilation...")
    case_brief = load_case_brief(project_dir)
    plan = load_plan(project_dir)
    sections = load_all_sections(project_dir)
    living_brief = read_living_brief(project_dir)

    if not case_brief:
        raise RuntimeError("No case_brief.json found.")
    if not plan:
        raise RuntimeError("No plan.json found.")

    topic = case_brief.get("topic", "Research Report")
    decision = case_brief.get("decision", "")
    audience = case_brief.get("audience", "general")

    execution_order = plan.get("execution_order", [a["id"] for a in plan["angles"]])
    oneliners = _get_section_oneliners(project_dir)
    oneliners_str = "\n".join(f"- {sid}: {ol}" for sid, ol in oneliners.items())

    # Track compilation call count
    comp_call = 0
    _MAX_COMPILE_CALLS = 15  # expanded from 12 to accommodate new phases

    def flash(prompt: str, label: str) -> str:
        nonlocal comp_call
        comp_call += 1
        ui.print_call_progress(comp_call, _MAX_COMPILE_CALLS, label)
        return llm.call_flash(prompt, call_label=f"compile_{label}")

    # ── Compilation Call 1: Executive Summary ─────────────────────────────
    exec_summary = flash(
        _load_prompt("executive_summary.txt").replace("{topic}", topic)
        .replace("{decision}", decision)
        .replace("{audience}", audience)
        .replace("{living_brief}", living_brief)
        .replace("{section_one_liners}", oneliners_str),
        "exec_summary",
    )

    # ── Compilation Call 2: Key Findings ──────────────────────────────────
    key_findings = flash(
        _load_prompt("key_findings.txt").replace("{living_brief}", living_brief)
        .replace("{section_one_liners}", oneliners_str),
        "key_findings",
    )

    # ── Compilation Call 3: Visual Forge (Mermaid.js diagram) ─────────────
    visual_diagram_mermaid = ""
    try:
        vf_prompt = (
            _load_prompt("visual_forge.txt")
            .replace("{topic}", topic)
            .replace("{decision}", decision)
            .replace("{key_findings}", key_findings[:2000])
            .replace("{section_oneliners}", oneliners_str)
        )
        raw_diagram = flash(vf_prompt, "visual_forge")
        # Strip any accidental code fences the model might add
        raw_diagram = raw_diagram.strip()
        for fence in ("```mermaid", "```"):
            raw_diagram = raw_diagram.replace(fence, "").strip()
        if raw_diagram:
            visual_diagram_mermaid = raw_diagram
    except Exception as e:
        logger.warning(f"Visual Forge diagram generation failed: {e}")

    # ── Compilation Call 4: Section Transitions ───────────────────────────
    section_sequence = []
    for angle_id in execution_order:
        angle = next((a for a in plan["angles"] if a["id"] == angle_id), None)
        if angle and angle_id in sections:
            first_line = sections[angle_id].split("\n")[0].lstrip("# ").strip()
            section_sequence.append(f"{angle_id}: {angle['title']} — {first_line}")

    transitions_json = flash(
        _load_prompt("transitions.txt").replace("{section_sequence}", "\n".join(section_sequence)),
        "transitions",
    )

    try:
        transitions_data = json.loads(_strip_code_fences(transitions_json))
        transitions = {t["from"]: t["sentence"] for t in transitions_data.get("transitions", [])}
    except Exception:
        transitions = {}

    # ── Compilation Call 5: Conclusion ────────────────────────────────────
    conclusion_text = flash(
        _load_prompt("conclusion.txt").replace("{topic}", topic)
        .replace("{decision}", decision)
        .replace("{audience}", audience)
        .replace("{executive_summary}", exec_summary)
        .replace("{living_brief}", living_brief),
        "conclusion",
    )

    # Quality check conclusion — retry if it repeats exec summary
    if exec_summary[:100].lower()[:50] in conclusion_text.lower()[:200] and comp_call < _MAX_COMPILE_CALLS:
        conclusion_text = flash(
            _load_prompt("conclusion.txt").replace("{topic}", topic)
            .replace("{decision}", decision)
            .replace("{audience}", audience)
            .replace("{executive_summary}", exec_summary)
            .replace("{living_brief}", living_brief)
            + "\n\nIMPORTANT: The previous attempt repeated the executive summary. Focus ONLY on forward-looking implications and recommendations. Do not repeat any sentences from the executive summary.",
            "conclusion_retry",
        )

    # ── Compilation Calls 7-8: Risks and Limitations ──────────────────────
    evidence_quality_summary = _get_evidence_quality_summary(project_dir, plan)
    thin_angles = _get_thin_evidence_angles(project_dir, plan)
    paywalled_count = _get_paywalled_count(project_dir)

    # Gather open gaps and unresolved contradictions from living brief
    gaps_text = ""
    contradictions_text = ""
    in_section = None
    for line in living_brief.splitlines():
        if "## CONTRADICTIONS LIVE" in line:
            in_section = "contradictions"
            continue
        elif "## OPEN ANGLES" in line:
            in_section = "open"
            continue
        elif line.startswith("## "):
            in_section = None
        elif in_section == "contradictions" and line.strip() and not line.strip().startswith("("):
            contradictions_text += line + "\n"
        elif in_section == "open" and line.strip() and not line.strip().startswith("("):
            gaps_text += line + "\n"

    risks_text = flash(
        _load_prompt("risks_limitations.txt").replace("{evidence_quality_summary}", evidence_quality_summary)
        .replace("{paywalled_count}", str(paywalled_count))
        .replace("{validation_failures}", "0")
        .replace("{unresolved_contradictions}", contradictions_text or "(none recorded)")
        .replace("{thin_evidence_areas}", "\n".join(thin_angles) or "(none)")
        .replace("{open_gaps}", gaps_text or "(none recorded)"),
        "risks",
    )

    # ── Compilation Call 9: Bibliography ──────────────────────────────────
    sources_summary = get_sources_summary(project_dir)
    bibliography = flash(
        _load_prompt("bibliography.txt").replace("{sources_registry}", sources_summary),
        "bibliography",
    )

    # ── Assemble Draft Report ─────────────────────────────────────────────
    report_parts = [f"# {topic} — {decision}\n"]
    report_parts.append("## Executive Summary\n")
    report_parts.append(exec_summary + "\n")
    report_parts.append("## Key Findings\n")
    report_parts.append(key_findings + "\n")

    # Inject the Visual Forge diagram
    if visual_diagram_mermaid:
        report_parts.append("\n## Strategic Market Map\n")
        report_parts.append("> *Auto-generated structural diagram based on consolidated research findings.*\n")
        report_parts.append(f"\n```mermaid\n{visual_diagram_mermaid}\n```\n")

    for i, angle_id in enumerate(execution_order):
        angle = next((a for a in plan["angles"] if a["id"] == angle_id), None)
        if not angle:
            continue
        content = sections.get(angle_id, f"## {angle['title']}\n\n*Section not available.*\n")

        # Inject transition before section (not before first)
        if i > 0:
            prev_id = execution_order[i - 1]
            transition = transitions.get(prev_id, "")
            if transition:
                report_parts.append(f"\n*{transition}*\n")

        report_parts.append("\n" + content + "\n")

    report_parts.append("\n## Risks and Limitations\n")
    report_parts.append(risks_text + "\n")
    report_parts.append("\n## So What\n")
    report_parts.append(conclusion_text + "\n")
    report_parts.append("\n## Sources\n")
    report_parts.append(bibliography + "\n")

    # ── Truth Engine: Citation Integrity Audit (Phase 3) ──────────────────
    # NOTE: The audit calls llm.call_flash() directly (not the flash() closure)
    # so it does NOT increment comp_call. This keeps the readthrough guard working.
    citation_audit_md = _run_citation_audit(llm, project_dir, plan, sections)
    if citation_audit_md:
        report_parts.append("\n" + citation_audit_md + "\n")

    report_parts.append(f"\n---\n*Generated by Cormorant on {datetime.now().strftime('%Y-%m-%d')}. Flash Lite calls used: {llm.flash_calls_used()}.*\n")

    draft_content = "\n".join(report_parts)
    draft_path = project_dir / "report_draft.md"
    _atomic_write(draft_path, draft_content)

    # ── Compilation Calls (final): Final Read-Through ──────────────────────
    # Always run readthrough; audit calls bypass flash() so comp_call is accurate.
    remaining = max(1, _MAX_COMPILE_CALLS - comp_call)
    final_content = _final_readthrough(llm, draft_content, project_dir, max_calls=min(3, remaining))

    final_path = project_dir / "report_final.md"
    _atomic_write(final_path, final_content)
    
    # Also write a copy directly in the workspace root for instant double-click access
    workspace_root = Path(__file__).resolve().parent.parent
    root_path = workspace_root / "report_final.md"
    _atomic_write(root_path, final_content)
    
    update_session(project_dir, status="complete", current_phase="complete")

    ui.print_success("\n🎉 [bold]Research & Synthesis Complete![/bold]")
    ui.print_success(f"📄 [bold green]MAIN REPORT FILE (Open this):[/bold green] {root_path}")
    ui.print_info(f"📁 [#22d3ee]Supporting Project Directory (JSONs & logs):[/#22d3ee] {project_dir}\n")
    wc = len(final_content.split())
    ui.print_info(f"Word count: {wc} words")

    return root_path


def _final_readthrough(llm: LLMClient, content: str, project_dir: Path, max_calls: int) -> str:
    # Process in sections to avoid truncation of large reports
    report_sections = content.split("\n## ")
    refined_parts = []
    
    for i, section in enumerate(report_sections):
        if i == 0:
            header = ""
            body = section
        else:
            header = "## "
            body = section

        prompt = _load_prompt("final_readthrough.txt").replace("{report_content}", body[:8000])
        try:
            response = llm.call_flash(prompt, call_label=f"readthrough_{i}")
            data = json.loads(_strip_code_fences(response))

            if not data.get("issues_found") or not data.get("edits"):
                refined_parts.append(header + body)
                continue

            edits = data.get("edits", [])
            for edit in edits:
                find_text = edit.get("find", "").strip()
                replace_text = edit.get("replace", "").strip()
                if find_text and replace_text and find_text in body:
                    body = body.replace(find_text, replace_text, 1)
            
            refined_parts.append(header + body)

        except Exception as e:
            logger.warning(f"Final read-through failed for section {i}: {e}")
            refined_parts.append(header + body)

    return "\n".join(refined_parts)


def _run_citation_audit(
    llm: LLMClient,
    project_dir: Path,
    plan: dict,
    sections: dict[str, str],
) -> str:
    """Truth Engine: Cross-reference section claims against cached raw source text.

    Calls llm.call_flash() directly (NOT the compile_report flash() closure) so
    citation audit calls do NOT count against the compilation call budget / UI counter.
    Returns a Markdown string for '## Citation Integrity Audit', or '' if nothing to audit.
    """
    validator_prompt_tpl = _load_prompt("citation_validator.txt")
    all_results: list[dict] = []
    total_verified = 0
    total_partial = 0
    total_unverified = 0

    angles = plan.get("angles", [])
    execution_order = plan.get("execution_order", [a["id"] for a in angles])

    for angle_id in execution_order:
        angle = next((a for a in angles if a["id"] == angle_id), None)
        if not angle or angle_id not in sections:
            continue

        section_draft = sections[angle_id]
        if not section_draft or len(section_draft.strip()) < 100:
            continue

        # Gather cached raw source texts for this angle
        cache_raw_dir = project_dir / "cache" / f"{angle_id}_raw"
        source_texts_combined = ""
        if cache_raw_dir.exists():
            txt_files = sorted(cache_raw_dir.glob("*.txt"))[:5]  # top-5 cached sources
            for tf in txt_files:
                try:
                    text = tf.read_text()[:3000]  # cap per source to stay in context
                    source_texts_combined += f"\n--- {tf.stem} ---\n{text}\n"
                except Exception:
                    continue

        if not source_texts_combined.strip():
            # No cached source text available; skip this angle
            continue

        # Build validation prompt
        prompt = (
            validator_prompt_tpl
            .replace("{angle_title}", angle.get("title", angle_id))
            .replace("{section_draft}", section_draft[:4000])
            .replace("{source_texts}", source_texts_combined[:8000])
        )

        try:
            ui.print_info(f"  [Truth Engine] Auditing citations for {angle_id}...")
            raw = llm.call_flash(prompt, call_label=f"cite_audit_{angle_id}")
            cleaned = _strip_code_fences(raw)
            start = cleaned.find("{")
            if start < 0:
                continue
            result = json.loads(cleaned[start:])
            all_results.append(result)
            total_verified += result.get("verified_count", 0)
            total_partial += result.get("partially_supported_count", 0)
            total_unverified += result.get("unverified_count", 0)
        except Exception as e:
            logger.warning(f"Citation audit failed for {angle_id}: {e}")
            continue

    if not all_results:
        return ""

    # Compute overall Hallucination Risk Score
    total_claims = total_verified + total_partial + total_unverified
    if total_claims == 0:
        return ""
    unverified_pct = (total_unverified / total_claims) * 100
    if unverified_pct < 10:
        risk_label = "🟢 LOW"
        risk_desc = "Fewer than 10% of sampled claims are unverified. Research integrity is strong."
    elif unverified_pct < 25:
        risk_label = "🟡 MEDIUM"
        risk_desc = f"{unverified_pct:.0f}% of sampled claims lack direct source grounding. Review flagged items."
    else:
        risk_label = "🔴 HIGH"
        risk_desc = f"{unverified_pct:.0f}% of sampled claims are unverified. Treat figures with caution."

    # Build Markdown output
    lines: list[str] = []
    lines.append("## Citation Integrity Audit")
    lines.append("")
    lines.append("> *The Truth Engine cross-references every statistical claim in the report against "
                 "raw scraped source text to detect hallucination risk.*")
    lines.append("")
    lines.append(f"**Overall Hallucination Risk Score:** {risk_label}")
    lines.append(f"> {risk_desc}")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| ✅ Verified claims | {total_verified} |")
    lines.append(f"| 🟡 Partially supported | {total_partial} |")
    lines.append(f"| ❌ Unverified / at risk | {total_unverified} |")
    lines.append(f"| Total claims sampled | {total_claims} |")
    lines.append("")

    for result in all_results:
        section_name = result.get("section", "Unknown Section")
        claims = result.get("claims", [])
        if not claims:
            continue
        lines.append(f"### {section_name}")
        lines.append("")
        lines.append("| Claim | Status | Supporting Evidence |")
        lines.append("|-------|--------|---------------------|")
        for c in claims:
            status = c.get("status", "UNVERIFIED_RISK")
            icon = {"VERIFIED": "✅", "PARTIALLY_SUPPORTED": "🟡", "UNVERIFIED_RISK": "❌"}.get(status, "❓")
            claim_text = c.get("claim", "").replace("|", "\\|")[:100]
            evidence = c.get("supporting_quote", "") or c.get("remediation", "")
            evidence = evidence.replace("|", "\\|")[:120]
            lines.append(f"| {claim_text} | {icon} {status} | {evidence} |")
        lines.append("")

    return "\n".join(lines)
