"""Phase 3 — High-Depth "Atomic Lossless" Research Pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema

from cormorant import ui
from cormorant.frameworks import DOMAIN_TIERS
from cormorant.llm import LLMClient, _strip_code_fences
from cormorant.memory import (
    apply_brief_delta,
    read_living_brief,
    register_sources,
    load_sources,
)
from cormorant.search import search_and_fetch, Source
from cormorant.sessions import (
    save_section,
    section_word_count,
    update_session,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
SCHEMAS_DIR = Path(__file__).parent / "schemas"

ATOMS_SCHEMA = json.loads((SCHEMAS_DIR / "atoms.json").read_text())
FACT_POOL_SCHEMA = json.loads((SCHEMAS_DIR / "fact_pool.json").read_text())
GAP_SCHEMA = json.loads((SCHEMAS_DIR / "gap_analysis.json").read_text())
CONTRADICTION_SCHEMA = json.loads((SCHEMAS_DIR / "contradictions.json").read_text())


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def _compress_brief(brief: str, max_chars: int = 1200) -> str:
    if len(brief) <= max_chars:
        return brief
    return brief[:max_chars] + "\n...[truncated]"


def _format_fact_pool(pool: dict) -> str:
    lines = []
    for f in pool.get("consolidated_facts", []):
        lines.append(f"- [{f['category'].upper()}] (Imp: {f['importance']}) {f['claim']}")
    for c in pool.get("contradictions", []):
        lines.append(f"- [CONFLICT] {c['claim_a']} VS {c['claim_b']} : {c['resolution_attempt']}")
    return "\n".join(lines) or "(empty pool)"


def _extract_atoms(
    llm: LLMClient,
    angle: dict,
    source: Source,
    call_label: str,
    dashboard: ui.ResearchDashboard | None = None,
) -> list[dict]:
    """Extract atomic facts from a single source."""
    if not source.chunks:
        return []
    
    # Increase chunk budget for deep research (Consulting Grade)
    # Read up to 15 chunks (~20k tokens) to ensure we don't miss the middle of long PDFs
    source_text = f"URL: {source.url}\nTITLE: {source.title}\nCONTENT:\n" + "\n\n".join(source.chunks[:15])
    
    prompt = _load_prompt("atomic_extraction.txt").replace("SOURCE BATCH (multiple sources for comparative extraction):\n{source_batch}\n", source_text)
    prompt = prompt.replace("{angle_title}", angle["title"])
    prompt = prompt.replace("{key_questions}", "\n".join(f"- {q}" for q in angle["key_questions"]))
    
    try:
        response = llm.call_flash(prompt, call_label=call_label, schema=ATOMS_SCHEMA)
        parsed = json.loads(_strip_code_fences(response))
        jsonschema.validate(parsed, ATOMS_SCHEMA)
        # Tag with source
        for atom in parsed.get("atoms", []):
            atom["source_url"] = source.url
            if dashboard:
                dashboard.update(atom=atom.get("claim", "New fact found..."))
        return parsed.get("atoms", [])
    except Exception as e:
        logger.warning(f"Atomic extraction failed for {source.url}: {e}")
        return []


def _consolidate_facts(
    llm: LLMClient,
    atoms: list[dict],
    call_label: str,
) -> dict:
    """Merge and rank atoms into a consolidated fact pool."""
    prompt = _load_prompt("fact_consolidation.txt").replace("{fact_pool}", json.dumps(atoms, indent=2))
    
    try:
        response = llm.call_flash(prompt, call_label=call_label, schema=FACT_POOL_SCHEMA)
        parsed = json.loads(_strip_code_fences(response))
        jsonschema.validate(parsed, FACT_POOL_SCHEMA)
        return parsed
    except Exception as e:
        logger.warning(f"Fact consolidation failed: {e}")
        return {"consolidated_facts": [], "contradictions": []}


def _gap_analysis(
    llm: LLMClient,
    pool: dict,
    case_brief: dict,
    call_label: str,
) -> dict:
    """Identify gaps and adversarial queries."""
    prompt = _load_prompt("gap_analysis.txt").replace("{consolidated_facts}", _format_fact_pool(pool))
    prompt = prompt.replace("{thesis}", case_brief.get("thesis_hypothesis", ""))
    
    try:
        response = llm.call_flash(prompt, call_label=call_label, schema=GAP_SCHEMA)
        parsed = json.loads(_strip_code_fences(response))
        jsonschema.validate(parsed, GAP_SCHEMA)
        return parsed
    except Exception as e:
        logger.warning(f"Gap analysis failed: {e}")
        return {"gaps": [], "adversarial_queries": []}


def _persona_review(
    llm: LLMClient,
    draft: str,
    pool: dict,
    case_brief: dict,
    persona_type: str,
    call_label: str,
) -> str:
    """Run a specific persona review on a draft."""
    prompt_name = f"review_{persona_type}.txt"
    prompt = _load_prompt(prompt_name).replace("{draft}", draft)
    prompt = prompt.replace("{fact_pool}", _format_fact_pool(pool))
    prompt = prompt.replace("{case_brief}", json.dumps(case_brief, indent=2))
    
    try:
        return llm.call_flash(prompt, call_label=call_label)
    except Exception as e:
        logger.warning(f"{persona_type} review failed: {e}")
        return "Review unavailable."


def _generate_research_queries(
    llm: LLMClient,
    angle: dict,
    case_brief: dict,
    living_brief: str,
    completed_section_oneliners: dict[str, str],
) -> list[str]:
    """Call 1: Generate targeted search queries for this angle."""
    angle_id = angle["id"]
    query_prompt = _load_prompt("query_generation.txt").replace("{case_brief_compressed}", _compress_brief(json.dumps(case_brief)))
    query_prompt = query_prompt.replace("{living_brief}", _compress_brief(living_brief))
    query_prompt = query_prompt.replace("{angle_id}", angle_id)
    query_prompt = query_prompt.replace("{angle_title}", angle["title"])
    query_prompt = query_prompt.replace("{key_questions}", "\n".join(f"- {q}" for q in angle["key_questions"]))
    query_prompt = query_prompt.replace("{search_seeds}", "\n".join(f"- {s}" for s in angle["search_seeds"]))
    query_prompt = query_prompt.replace("{completed_sections}", "\n".join(f"- {k}: {v}" for k, v in completed_section_oneliners.items()) or "(none)")
    query_prompt = query_prompt.replace("{strategic_focus}", case_brief.get("strategic_focus", ""))

    queries = angle["search_seeds"][:5]
    try:
        qr = llm.call_flash(query_prompt, call_label=f"{angle_id}_queries")
        parsed_q = json.loads(_strip_code_fences(qr))
        queries = parsed_q.get("queries", queries)
    except Exception:
        logger.warning(f"Query generation failed for {angle_id}, using seeds.")
    return queries


def _extract_all_atoms(
    llm: LLMClient,
    angle: dict,
    sources: list[Source],
    project_dir: Path,
    dashboard: ui.ResearchDashboard,
    start_call_idx: int = 3,
) -> list[dict]:
    """Deep extraction using Triplet Batching (3 sources per call)."""
    all_atoms = []
    angle_id = angle["id"]
    active_sources = [s for s in sources[:9] if not s.is_paywalled]
    
    # Process in triplets
    for i in range(0, len(active_sources), 3):
        batch = active_sources[i:i+3]
        batch_text = ""
        for idx, src in enumerate(batch):
            text = "\n\n".join(src.chunks[:15])
            batch_text += f"\n--- SOURCE {idx+1} (URL: {src.url}) ---\n{text}\n"

        dashboard.update(progress=start_call_idx + i, step=f"Comparative extraction (Batch {i//3 + 1})")
        
        prompt = _load_prompt("atomic_extraction.txt").replace("{source_batch}", batch_text)
        prompt = prompt.replace("{angle_title}", angle["title"])
        prompt = prompt.replace("{key_questions}", "\n".join(f"- {q}" for q in angle["key_questions"]))
        
        try:
            response = llm.call_flash(prompt, call_label=f"{angle_id}_batch_{i}", schema=ATOMS_SCHEMA)
            parsed = json.loads(_strip_code_fences(response))
            for atom in parsed.get("atoms", []):
                s_idx = atom.get("source_idx", 1) - 1
                # Clip to batch size
                s_idx = max(0, min(s_idx, len(batch) - 1))
                atom["source_url"] = batch[s_idx].url
                all_atoms.append(atom)
                dashboard.update(atom=atom.get("claim", "New fact found..."))
        except Exception as e:
            logger.warning(f"Batch extraction failed: {e}")

        update_session(project_dir, current_call=start_call_idx + (i // 3))
        
    return all_atoms


def _draft_section(
    llm: LLMClient,
    angle: dict,
    case_brief: dict,
    fact_pool: dict,
    project_dir: Path,
    completed_section_oneliners: dict[str, str],
    data_tables: str = "",
) -> str:
    """Call 16: Expert drafting based on consolidated facts."""
    # Only pass top-ranked facts to drafting to maintain SNR
    top_facts = [f for f in fact_pool.get("consolidated_facts", []) if f["importance"] >= 6]
    draft_prompt = _load_prompt("section_draft.txt").replace("{topic}", case_brief.get("topic", ""))
    draft_prompt = draft_prompt.replace("{decision}", case_brief.get("decision", ""))
    draft_prompt = draft_prompt.replace("{thesis}", case_brief.get("thesis_hypothesis", ""))
    draft_prompt = draft_prompt.replace("{angle_id}", angle["id"])
    draft_prompt = draft_prompt.replace("{angle_title}", angle["title"])
    
    # Format confirmed claims WITH domain names to prevent hallucinated citations
    from urllib.parse import urlparse
    formatted_claims = []
    for f in top_facts:
        sources = f.get("sources", [])
        domains = []
        for url in sources:
            if url:
                try:
                    loc = urlparse(url).netloc
                    if loc:
                        domains.append(loc.replace("www.", ""))
                except Exception:
                    continue
        source_str = f" [Verified Sources: {', '.join(domains)}]" if domains else ""
        formatted_claims.append(f"- {f['claim']}{source_str}")
        
    draft_prompt = draft_prompt.replace("{confirmed_claims}", "\n".join(formatted_claims))
    draft_prompt = draft_prompt.replace("{contradictions}", _format_fact_pool({"consolidated_facts": [], "contradictions": fact_pool.get("contradictions", [])}))
    draft_prompt = draft_prompt.replace("{data_tables}", data_tables or "(no structured data available)")
    draft_prompt = draft_prompt.replace("{living_brief}", _compress_brief(read_living_brief(project_dir)))
    draft_prompt = draft_prompt.replace("{completed_sections}", "\n".join(f"- {k}: {v}" for k, v in completed_section_oneliners.items()) or "(none)")
    draft_prompt = draft_prompt.replace("{strategic_focus}", case_brief.get("strategic_focus", ""))
    return llm.call_flash(draft_prompt, call_label=f"{angle['id']}_draft")


def research_angle(
    llm: LLMClient,
    angle: dict,
    case_brief: dict,
    project_dir: Path,
    completed_section_oneliners: dict[str, str],
    buffer_calls_remaining: int,
) -> tuple[str, int, bool]:
    """Run the High-Depth modular research pipeline. 15-20 calls."""
    angle_id = angle["id"]
    angle_title = angle["title"]

    ui.print_angle_start(angle_id, angle_title)
    update_session(project_dir, current_angle=angle_id, current_call=1)

    with ui.ResearchDashboard(case_brief.get("topic", ""), angle_title, angle_id=angle_id) as dashboard:
        existing_sources = load_sources(project_dir)
        living_brief = read_living_brief(project_dir)
        buffer_used = 0

        # ── Phase 1: Query & Search ───────────────────────────────────────────
        dashboard.update(progress=1, step="Generating broad search queries")
        queries = _generate_research_queries(llm, angle, case_brief, living_brief, completed_section_oneliners)

        dashboard.update(progress=2, step="Broad search & source fetching")
        sources = search_and_fetch(queries, angle_id, project_dir, DOMAIN_TIERS, existing_sources)
        
        if not sources:
            ui.print_warn(f"Warning: Targeted search for {angle_id} returned no results. Retrying with broad queries...")
            broad_queries = [f"{case_brief.get('topic', '')} {angle_title}"]
            sources = search_and_fetch(broad_queries, f"{angle_id}_broad", project_dir, DOMAIN_TIERS, existing_sources)
            
        register_sources(project_dir, sources)

        if not sources:
            ui.print_warn(f"Warning: No sources found for {angle_id}. Research may be thin.")

        # ── Phase 2: Extraction & Consolidation ───────────────────────────────
        all_atoms = _extract_all_atoms(llm, angle, sources, project_dir, dashboard=dashboard)

        dashboard.update(progress=11, step="Consolidating fact pool")
        fact_pool = _consolidate_facts(llm, all_atoms, f"{angle_id}_consolidate")

        dashboard.update(progress=12, step="Identifying research gaps & adversarial queries")
        gaps_result = _gap_analysis(llm, fact_pool, case_brief, f"{angle_id}_gaps")

        # ── NEW: Data Forge Phase ─────────────────────────────────────────────
        dashboard.update(progress=12, step="Forging data tables & matrixes")
        data_forge_prompt = _load_prompt("data_forge.txt").replace("{fact_pool}", _format_fact_pool(fact_pool))
        data_forge_prompt = data_forge_prompt.replace("{angle_title}", angle_title)
        data_forge_prompt = data_forge_prompt.replace("{topic}", case_brief.get("topic", ""))
        try:
            data_tables = llm.call_flash(data_forge_prompt, call_label=f"{angle_id}_data_forge")
        except Exception:
            data_tables = ""

        # ── Phase 3: Recursive Search ─────────────────────────────────────────
        recursive_queries = gaps_result.get("adversarial_queries", []) + [q for g in gaps_result.get("gaps", []) for q in g.get("queries", [])]
        recursive_sources = []
        if recursive_queries and buffer_calls_remaining > 5:
            dashboard.update(progress=13, step="Recursive search for gaps")
            recursive_sources = search_and_fetch(recursive_queries[:3], f"{angle_id}_recursive", project_dir, DOMAIN_TIERS, existing_sources)
            if recursive_sources:
                dashboard.update(progress=14, step="Extracting recursive atoms")
                # Use the same Triplet Batching for recursive sources
                rec_atoms = _extract_all_atoms(llm, angle, recursive_sources, project_dir, dashboard, start_call_idx=14)
                fact_pool["consolidated_facts"].extend(rec_atoms)
                register_sources(project_dir, recursive_sources)

            dashboard.update(progress=15, step="Final fact pool synthesis")
            fact_pool = _consolidate_facts(llm, fact_pool.get("consolidated_facts", []), f"{angle_id}_consolidate_final")

        # ── Phase 4: Drafting & Review ────────────────────────────────────────
        top_facts_count = len([f for f in fact_pool.get("consolidated_facts", []) if f["importance"] >= 7])
        evidence_quality = "strong" if top_facts_count >= 10 else "adequate" if top_facts_count >= 5 else "thin"
        (project_dir / "cache" / f"{angle_id}_evidence_quality.txt").write_text(evidence_quality)

        dashboard.update(progress=16, step="Writing expert-level draft")
        # Inject forged tables into the draft prompt context
        draft = _draft_section(llm, angle, case_brief, fact_pool, project_dir, completed_section_oneliners, data_tables=data_tables)

        dashboard.update(progress=17, step="Peer Review: Skeptical Investor")
        rev_skeptic = _persona_review(llm, draft, fact_pool, case_brief, "skeptic", f"{angle_id}_rev_skeptic")
        
        dashboard.update(progress=18, step="Peer Review: Technical Expert")
        rev_expert = _persona_review(llm, draft, fact_pool, case_brief, "expert", f"{angle_id}_rev_expert")
        
        dashboard.update(progress=19, step="Peer Review: Strategic Partner")
        rev_partner = _persona_review(llm, draft, fact_pool, case_brief, "partner", f"{angle_id}_rev_partner")

        dashboard.update(progress=20, step="Final Lead Partner synthesis")
        synthesis_prompt = _load_prompt("final_synthesis.txt").replace("{draft}", draft)
        synthesis_prompt = synthesis_prompt.replace("{review_skeptic}", rev_skeptic)
        synthesis_prompt = synthesis_prompt.replace("{review_expert}", rev_expert)
        synthesis_prompt = synthesis_prompt.replace("{review_partner}", rev_partner)
        synthesis_prompt = synthesis_prompt.replace("{fact_pool}", _format_fact_pool(fact_pool))
        final_section = llm.call_flash(synthesis_prompt, call_label=f"{angle_id}_synthesis")

        # ── Active Self-Correction Loop (Active Truth Engine) ─────────────────
        dashboard.update(progress=20, step="Auditing section facts (Truth Engine)")
        
        # Gather raw text chunks for audit validation
        cache_raw_dir = project_dir / "cache" / f"{angle_id}_raw"
        source_texts_combined = ""
        if cache_raw_dir.exists():
            txt_files = sorted(cache_raw_dir.glob("*.txt"))[:3]
            for tf in txt_files:
                try:
                    source_texts_combined += f"\n--- Source ---\n{tf.read_text()[:2500]}\n"
                except Exception:
                    continue
        
        if source_texts_combined.strip():
            audit_prompt = _load_prompt("citation_validator.txt") \
                .replace("{angle_title}", angle_title) \
                .replace("{section_draft}", final_section[:4000]) \
                .replace("{source_texts}", source_texts_combined[:8000])
            
            try:
                audit_raw = llm.call_flash(audit_prompt, call_label=f"{angle_id}_pre_audit")
                cleaned = _strip_code_fences(audit_raw)
                start = cleaned.find("{")
                if start >= 0:
                    audit_res = json.loads(cleaned[start:])
                    unverified_claims = [c for c in audit_res.get("claims", []) if c.get("status") == "UNVERIFIED_RISK"]
                    
                    if unverified_claims:
                        dashboard.update(progress=20, step="Factual violations found. Executing self-correction rewrite...")
                        
                        corrections_block = "\n".join(
                            f"- Hallucinated/Unverified Claim: {c.get('claim')}\n  Corrective Action/Safer Wording: {c.get('remediation')}"
                            for c in unverified_claims
                        )
                        
                        redraft_prompt = _load_prompt("section_redraft.txt") \
                            .replace("{draft}", final_section) \
                            .replace("{corrections}", corrections_block)
                        
                        corrected_section = llm.call_flash(redraft_prompt, call_label=f"{angle_id}_self_corrected")
                        final_section = corrected_section
                        ui.print_info(f"  [Truth Engine] Successfully removed/corrected {len(unverified_claims)} unverified claims for {angle_id}!")
            except Exception as e:
                logger.warning(f"Active self-correction pre-audit failed for {angle_id}: {e}")

    # ── Phase 5: Brief Update ─────────────────────────────────────────────
    update_session(project_dir, current_call=21)
    brief_update_prompt = _load_prompt("brief_update.txt").replace("{living_brief}", read_living_brief(project_dir))
    brief_update_prompt = brief_update_prompt.replace("{angle_id}", angle_id)
    brief_update_prompt = brief_update_prompt.replace("{angle_title}", angle_title)
    brief_update_prompt = brief_update_prompt.replace("{section_content}", final_section)
    
    pivot_requested = False
    try:
        bu_response = llm.call_flash(brief_update_prompt, call_label=f"{angle_id}_brief_update")
        delta = json.loads(_strip_code_fences(bu_response))
        pivot_requested = apply_brief_delta(project_dir, delta)
    except Exception:
        apply_brief_delta(project_dir, {"section_complete": {"id": angle_id, "title": angle_title, "one_liner": f"{angle_title} complete."}})

    total_sources = sources + recursive_sources
    src_count = len([s for s in total_sources if not s.is_paywalled])
    save_section(project_dir, angle_id, angle_title, final_section)
    ui.print_angle_complete(angle_id, angle_title, section_word_count(final_section), src_count)
    
    return final_section, buffer_used, pivot_requested


