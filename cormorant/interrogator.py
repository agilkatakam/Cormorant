"""Phase 1 — Conversational scoping powered by Gemini 2.5 Flash Lite (with Gemma fallback)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from cormorant import ui
from cormorant.frameworks import FRAMEWORKS
from cormorant.llm import LLMClient, _strip_code_fences
from cormorant.memory import _atomic_write

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "interrogator_system.txt"

MAX_TURNS = 10
FRAMEWORK_LIST = "\n".join(f"  - {k}: {v['name']}" for k, v in FRAMEWORKS.items())


def _build_system_prompt(framework_id: str) -> str:
    from cormorant.framework_focus import get_strategic_focus
    base = SYSTEM_PROMPT_PATH.read_text()
    f_info = FRAMEWORKS.get(framework_id, list(FRAMEWORKS.values())[0])
    focus = get_strategic_focus(framework_id)
    framework_context = (
        f"SELECTED FRAMEWORK: {f_info['name']}\n"
        f"DESCRIPTION: {f_info['description']}\n"
        f"STRATEGIC FOCUS MANDATE: {focus}\n\n"
        "You must tailor your questions strictly to gather inputs supporting this specific framework and strategic focus mandate."
    )
    return base + "\n\n" + framework_context


def run_interrogation(llm: LLMClient, project_dir: Path) -> dict:
    """Run the conversational interrogation and return the case_brief dict."""
    
    # Phase 1a: Framework Selection
    selected_framework_id = ui.select_framework()
    
    ui.print_info("Starting research scoping. I'll ask a few questions.")
    ui.print_info("Type /skip to use what's been gathered, or /cancel to abort.\n")

    system_prompt = _build_system_prompt(selected_framework_id)
    history: list[dict[str, str]] = [
        {"role": "user", "content": system_prompt},
    ]

    # First question from the model
    f_name = FRAMEWORKS.get(selected_framework_id, {}).get("name", "Research")
    first_q = f"We are using the '{f_name}' framework. What are you researching, and what specific decision does this research need to support?"
    ui.console.print(f"\n[#22d3ee]Cormorant:[/#22d3ee] {first_q}")
    history.append({"role": "model", "content": first_q})

    turn = 0
    case_brief: dict | None = None

    while turn < MAX_TURNS:
        try:
            user_input = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            cmd = user_input.split()[0].lower()
            if cmd == "/skip":
                ui.print_info("Forcing summary with gathered information...")
                user_input = "Please summarize what you have gathered so far and produce the case_brief JSON now. Use your best judgment to fill in missing details."

            elif cmd == "/cancel":
                raise KeyboardInterrupt("User cancelled")
            elif cmd == "/topic":
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    ui.print_info(f"Topic refined to: {parts[1]}")
                    user_input = f"I want to change the research topic to: {parts[1]}"
                else:
                    ui.print_warn("Please provide a topic, e.g., /topic AI in Healthcare")
                    continue
            elif cmd == "/brief":
                ui.print_info("Requesting a draft brief from the model...")
                user_input = "Please show me the current draft of the research brief based on our conversation so far. Do not finalize yet."
            elif cmd == "/reset":
                ui.print_info("Resetting interrogation history...")
                history = [{"role": "user", "content": system_prompt}]
                history.append({"role": "model", "content": first_q})
                ui.console.print(f"\n[#22d3ee]Cormorant:[/#22d3ee] {first_q}")
                turn = 0
                continue
            elif cmd == "/help":
                ui.console.print("\n[bold #22d3ee]Available Commands:[/bold #22d3ee]")
                ui.console.print("  [bold]/skip[/bold]      - Force the model to summarize and start research now")
                ui.console.print("  [bold]/brief[/bold]     - See a draft of the brief gathered so far")
                ui.console.print("  [bold]/topic[/bold]     - Manually set or refine the research topic")
                ui.console.print("  [bold]/reset[/bold]     - Restart the conversation from the beginning")
                ui.console.print("  [bold]/cancel[/bold]    - Abort the research project")
                ui.console.print("  [bold]/help[/bold]      - Show this menu\n")
                continue

        history.append({"role": "user", "content": user_input})

        try:
            with ui.spinner("Diving deeper (Gemini 2.5 Flash Lite)..."):
                response = llm.call_lite_chat(history, call_label=f"interrogation_t{turn}")
        except Exception as e:
            # Fall back to Gemma if Gemini 2.5 Flash Lite is unavailable
            logger.warning(f"Gemini 2.5 Flash Lite failed, falling back to Gemma: {e}")
            try:
                with ui.spinner("Diving deeper (Gemma fallback)..."):
                    response = llm.call_gemma_chat(history, call_label=f"interrogation_t{turn}_fallback")
            except Exception as e2:
                ui.print_error(f"LLM call failed: {e2}")
                break

        history.append({"role": "model", "content": response})

        # Check if the model produced the final JSON
        is_json = False
        if '"confirmed"' in response and '"case_brief"' in response:
            try:
                cleaned = _strip_code_fences(response)
                # Find the JSON object
                start = cleaned.find("{")
                if start >= 0:
                    parsed = json.loads(cleaned[start:])
                    if parsed.get("confirmed") and parsed.get("case_brief"):
                        from cormorant.framework_focus import get_strategic_focus
                        case_brief = parsed["case_brief"]
                        case_brief["strategic_focus"] = get_strategic_focus(selected_framework_id)
                        # Add timestamp
                        case_brief["created_at"] = datetime.now().isoformat(timespec="seconds")
                        is_json = True
                        break
            except json.JSONDecodeError:
                pass

        if not is_json:
            ui.console.print("")
            ui.stream_print(response, prefix="**Cormorant:**")
            ui.console.print("")
        
        turn += 1

        # Force wrap-up at MAX_TURNS - 1
        if turn == MAX_TURNS - 1:
            ui.print_warn("Reaching question limit — producing summary now.")
            history.append({
                "role": "user",
                "content": "Please finalize the research plan now. Output the case_brief JSON immediately.",
            })

    if case_brief is None:
        # Build a minimal case_brief from conversation context
        case_brief = _build_fallback_brief(history)

    # Validate and persist
    _atomic_write(project_dir / "case_brief.json", json.dumps(case_brief, indent=2))
    ui.print_success(f"\nResearch brief locked in: {case_brief['topic']}")
    return case_brief


def _build_fallback_brief(history: list[dict]) -> dict:
    """Build a minimal case_brief from conversation if structured output failed."""
    # Extract any text from conversation to infer topic
    all_text = " ".join(m["content"] for m in history if m["role"] == "user")
    topic = all_text[:80].strip() or "Research Topic"
    return {
        "topic": topic,
        "decision": "General research and understanding",
        "audience": "general",
        "framework": "industry_landscape",
        "thesis_hypothesis": f"Research into {topic} to understand the landscape and key dynamics.",
        "narrative_arc": [
            "Landscape is mature and well-understood",
            "Significant disruption underway",
            "Early-stage with high uncertainty",
        ],
        "scope": {
            "geography": "global",
            "time_horizon": "current",
            "depth": "full",
        },
        "emphasis": [],
        "exclude": [],
        "strategic_focus": "Focus on mapping market players, structural entry barriers, and profit pools.",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def confirm_plan_with_user(plan: dict, llm: LLMClient, case_brief: dict) -> dict:
    """Show the plan to the user and handle natural-language edits."""
    ui.print_plan(plan)

    ui.console.print("[#22d3ee]Does this research plan match what you need?[/#22d3ee] [Y/n] (or describe changes)")
    try:
        ans = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return plan

    if not ans or ans.lower() in ("y", "yes"):
        return plan

    if ans.lower() in ("n", "no"):
        ui.print_info("Type your changes (e.g., 'add something about Chinese competition', 'swap S05 and S06'):")
        try:
            ans = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            return plan

    if not ans:
        return plan

    # Use Flash Lite to apply the edit
    edit_template = """You are adjusting a research plan based on user feedback.

CURRENT PLAN:
{plan_json}

USER FEEDBACK:
{user_feedback}

Apply the feedback to the plan. Keep exactly 8 angles. Maintain the same JSON structure.
Output ONLY the updated plan JSON. No prose. No code fences."""

    edit_prompt = edit_template.replace("{plan_json}", json.dumps(plan, indent=2)).replace("{user_feedback}", ans)

    try:
        response = llm.call_flash(edit_prompt, call_label="plan_edit")
        cleaned = _strip_code_fences(response)
        updated = json.loads(cleaned)
        ui.print_success("Plan updated.")
        ui.print_plan(updated)
        return updated
    except Exception as e:
        ui.print_warn(f"Could not apply edit ({e}). Using original plan.")
        return plan
