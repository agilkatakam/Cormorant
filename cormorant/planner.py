"""Phase 2 — Planning: single Flash Lite call to generate the research plan."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema

from cormorant.frameworks import get_framework, fill_search_seeds
from cormorant.llm import LLMClient, _strip_code_fences
from cormorant.sessions import save_plan

logger = logging.getLogger(__name__)

PLANNING_PROMPT_PATH = Path(__file__).parent / "prompts" / "planning.txt"
PLAN_SCHEMA_PATH = Path(__file__).parent / "schemas" / "plan.json"


def _topological_sort(angles: list[dict]) -> list[str]:
    """Kahn's algorithm for dependency-based ordering."""
    in_degree = {a["id"]: 0 for a in angles}
    adj: dict[str, list[str]] = {a["id"]: [] for a in angles}

    for angle in angles:
        for dep in angle.get("depends_on", []):
            if dep in adj:
                adj[dep].append(angle["id"])
                in_degree[angle["id"]] += 1

    queue = [aid for aid, deg in in_degree.items() if deg == 0]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Include any missed angles at the end
    for a in angles:
        if a["id"] not in order:
            order.append(a["id"])

    return order


def generate_plan(llm: LLMClient, case_brief: dict, project_dir: Path, living_brief: str = "") -> dict:
    """Call Flash Lite to generate the research plan from the case brief."""
    framework_id = case_brief.get("framework", "industry_landscape")
    framework = get_framework(framework_id)
    topic = case_brief.get("topic", "")

    # Fill in template search seeds with topic
    framework_copy = dict(framework)
    angles_copy = []
    for angle in framework["angles"]:
        a = dict(angle)
        a["search_seeds"] = fill_search_seeds(a["search_seeds"], topic)
        angles_copy.append(a)
    framework_copy["angles"] = angles_copy

    prompt_template = PLANNING_PROMPT_PATH.read_text()
    schema = json.loads(PLAN_SCHEMA_PATH.read_text())

    prompt = prompt_template.replace("{case_brief}", json.dumps(case_brief, indent=2))
    prompt = prompt.replace("{framework_template}", json.dumps(framework_copy, indent=2))
    prompt = prompt.replace("{living_brief}", living_brief or "(no research completed yet)")
    prompt = prompt.replace("{strategic_focus}", case_brief.get("strategic_focus", ""))

    from cormorant.ui import print_info
    print_info("Generating research plan...")

    plan = None
    for attempt in range(3):
        try:
            response = llm.call_flash(
                prompt,
                call_label="planning",
                schema=schema,
            )
            cleaned = _strip_code_fences(response)
            plan = json.loads(cleaned)
            jsonschema.validate(plan, schema)
            break
        except (json.JSONDecodeError, jsonschema.ValidationError) as e:
            logger.warning(f"Plan validation failed attempt {attempt+1}: {e}")
            if attempt == 2:
                # Build a fallback plan from framework template
                plan = _build_fallback_plan(framework, topic)

    if plan is None:
        plan = _build_fallback_plan(framework, topic)

    # ID Reservation & Sort Stability: Ensure completed sections stay at the front
    from cormorant.sessions import load_session
    session = load_session(project_dir)
    if session:
        completed = session.get("completed_angles", [])
        # Put completed ones first, then others in topological order
        all_ids = plan["execution_order"]
        new_order = [aid for aid in all_ids if aid in completed]
        new_order += [aid for aid in all_ids if aid not in completed]
        plan["execution_order"] = new_order

    save_plan(project_dir, plan)
    return plan


def _build_fallback_plan(framework: dict, topic: str) -> dict:
    """Build a plan directly from the framework template if LLM fails."""
    angles = []
    for i, template_angle in enumerate(framework["angles"]):
        angle = {
            "id": template_angle["id"],
            "title": template_angle["title"],
            "key_questions": template_angle["key_questions"],
            "search_seeds": fill_search_seeds(template_angle["search_seeds"], topic),
            "priority": 10 - i,
            "depends_on": template_angle.get("depends_on", []),
        }
        angles.append(angle)

    plan = {
        "angles": angles,
        "execution_order": [a["id"] for a in angles],
    }
    plan["execution_order"] = _topological_sort(angles)
    return plan
