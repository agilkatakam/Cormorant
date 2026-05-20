"""Top-level orchestrator — stitches all phases together."""

from __future__ import annotations

import logging
from pathlib import Path

from cormorant import ui
from cormorant.compiler import compile_report
from cormorant.interrogator import confirm_plan_with_user, run_interrogation
from cormorant.llm import LLMClient, QuotaExceededError
from cormorant.memory import init_living_brief, read_living_brief
from cormorant.planner import generate_plan
from cormorant.researcher import research_angle
from cormorant.sessions import (
    create_project,
    init_session,
    load_case_brief,
    load_plan,
    load_section,
    load_session,
    save_case_brief,
    save_plan,
    update_session,
)

logger = logging.getLogger(__name__)

# No hard call budget enforced
BUFFER_BASE = 100


class Orchestrator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def new_project(self) -> Path:
        """Start a brand-new research project end to end."""
        # ── Phase 1: Interrogation ────────────────────────────────────────
        project_dir = create_project("_tmp")  # temporary slug
        try:
            case_brief = run_interrogation(self.llm, project_dir)
        except KeyboardInterrupt:
            ui.print_info("Research cancelled.")
            raise

        # Rename project dir to proper slug
        from cormorant.sessions import _slug, PROJECTS_DIR
        from datetime import datetime
        topic_slug = _slug(case_brief.get("topic", "research"))
        date_str = datetime.now().strftime("%Y%m%d")
        new_name = f"{topic_slug}_{date_str}"
        new_dir = PROJECTS_DIR / new_name
        if not new_dir.exists():
            project_dir.rename(new_dir)
            project_dir = new_dir
        else:
            # Already exists (same day, same topic) — use the new one
            project_dir = new_dir

        save_case_brief(project_dir, case_brief)

        # ── Phase 2: Planning ─────────────────────────────────────────────
        ui.print_info("\nGenerating research plan...")
        plan = generate_plan(self.llm, case_brief, project_dir)

        # Show plan and allow user edits
        plan = confirm_plan_with_user(plan, self.llm, case_brief)
        save_plan(project_dir, plan)

        # Initialize living brief
        init_living_brief(
            project_dir,
            topic=case_brief.get("topic", ""),
            thesis=case_brief.get("thesis_hypothesis", ""),
        )

        # Initialize session state
        session = init_session(project_dir, case_brief.get("topic", ""), case_brief, plan)
        update_session(project_dir, current_phase="research_loop", calls_used=self.llm.flash_calls_used())

        ui.print_research_start(case_brief.get("topic", ""))

        return self._run_research_loop(project_dir, case_brief, plan, session)

    def resume_project(self, project_dir: Path) -> Path:
        """Resume a paused or in-progress project."""
        session = load_session(project_dir)
        if not session:
            raise RuntimeError(f"No session found at {project_dir}")

        case_brief = load_case_brief(project_dir)
        plan = load_plan(project_dir)

        if not case_brief or not plan:
            raise RuntimeError("Missing case_brief.json or plan.json")

        status = session.get("status", "")
        if status == "complete":
            ui.print_info("Project already complete.")
            root_path = Path(__file__).resolve().parent.parent / "report_final.md"
            ui.print_success(f"📄 [bold green]MAIN REPORT FILE:[/bold green] {root_path}")
            ui.print_info(f"📁 [#22d3ee]Supporting Project Directory:[/#22d3ee] {project_dir}")
            return root_path

        ui.print_success(f"Resuming: {session.get('topic', '')}")
        ui.print_info(f"Completed angles: {session.get('completed_angles', [])}")

        update_session(project_dir, status="running")
        return self._run_research_loop(project_dir, case_brief, plan, session)

    def _run_research_loop(self, project_dir: Path, case_brief: dict, plan: dict, session: dict) -> Path:
        execution_order = plan.get("execution_order", [a["id"] for a in plan["angles"]])
        completed_angles: list[str] = session.get("completed_angles", [])
        angles_map = {a["id"]: a for a in plan["angles"]}

        buffer_calls_remaining = BUFFER_BASE
        completed_oneliners: dict[str, str] = {}

        # Load existing oneliners from living brief
        try:
            from cormorant.compiler import _get_section_oneliners
            completed_oneliners = _get_section_oneliners(project_dir)
        except Exception:
            pass

        # ── Phase 3: Research Loop ────────────────────────────────────────
        try:
            for angle_id in execution_order:
                if angle_id in completed_angles:
                    ui.print_info(f"{angle_id} already complete, skipping.")
                    continue

                angle = angles_map.get(angle_id)
                if not angle:
                    logger.warning(f"Angle {angle_id} not found in plan")
                    continue

                section_content, buffer_used, pivot_requested = research_angle(
                    llm=self.llm,
                    angle=angle,
                    case_brief=case_brief,
                    project_dir=project_dir,
                    completed_section_oneliners=completed_oneliners,
                    buffer_calls_remaining=buffer_calls_remaining,
                )

                buffer_calls_remaining -= buffer_used
                completed_angles.append(angle_id)
                calls_used = self.llm.flash_calls_used()

                # ── Handle Strategic Pivot ────────────────────────────────
                if pivot_requested and buffer_calls_remaining > 5:
                    ui.print_warn("Strategic pivot recommended. Re-planning research...")
                    try:
                        new_plan = generate_plan(self.llm, case_brief, project_dir, living_brief=read_living_brief(project_dir))
                        # Merge new plan: keep completed angles, update remaining
                        new_angles = new_plan.get("angles", [])
                        current_angles = plan.get("angles", [])
                        
                        # Only keep new angles that haven't been done
                        completed_ids = set(completed_angles)
                        merged_angles = [a for a in current_angles if a["id"] in completed_ids]
                        for na in new_angles:
                            if na["id"] not in completed_ids:
                                merged_angles.append(na)
                        
                        plan["angles"] = merged_angles
                        plan["execution_order"] = [a["id"] for a in merged_angles]
                        angles_map = {a["id"]: a for a in merged_angles}
                        execution_order = plan["execution_order"]
                        save_plan(project_dir, plan)
                        buffer_calls_remaining -= 1
                        ui.print_success("Research plan pivoted.")
                    except Exception as e:
                        logger.error(f"Pivot failed: {e}")

                update_session(
                    project_dir,
                    completed_angles=completed_angles,
                    calls_used=calls_used,
                    current_phase="research_loop",
                )

        except QuotaExceededError as e:
            ui.print_error(str(e))
            ui.print_warn("Project paused. Resume tomorrow with: cormorant resume")
            update_session(project_dir, status="paused")
            # Write partial report from completed sections
            if completed_angles:
                self._write_partial_report(project_dir, plan, case_brief)
            return project_dir / "report_draft.md"

        except KeyboardInterrupt:
            ui.print_warn("\nPaused. Resume with: cormorant resume")
            update_session(project_dir, status="paused")
            return project_dir / "report_draft.md"

        # ── Phase 4: Compilation ──────────────────────────────────────────
        update_session(project_dir, current_phase="compilation")
        try:
            report_path = compile_report(self.llm, project_dir)
            update_session(
                project_dir,
                status="complete",
                calls_used=self.llm.flash_calls_used(),
            )
            return report_path
        except QuotaExceededError as e:
            ui.print_error(str(e))
            ui.print_warn("Quota exhausted during compilation. Run cormorant resume tomorrow.")
            update_session(project_dir, status="paused")
            return project_dir / "report_draft.md"

    def _write_partial_report(self, project_dir: Path, plan: dict, case_brief: dict) -> None:
        from cormorant.sessions import load_all_sections
        from cormorant.memory import _atomic_write
        sections = load_all_sections(project_dir)
        parts = [f"# {case_brief.get('topic', 'Report')} — PARTIAL\n\n*Research paused — resume with: cormorant resume*\n"]
        for angle in plan["angles"]:
            aid = angle["id"]
            if aid in sections:
                parts.append(f"\n{sections[aid]}\n")
        _atomic_write(project_dir / "report_draft.md", "\n".join(parts))


def dig_section(
    llm: LLMClient,
    project_dir: Path,
    section_id: str,
    buffer_calls: int = 10,
) -> str:
    """Spend buffer calls deepening research on a specific section."""
    session = load_session(project_dir)
    if not session:
        raise RuntimeError("No session found.")

    calls_remaining = session.get("calls_remaining", 0)
    if calls_remaining < 5:
        raise RuntimeError(
            f"Buffer exhausted ({calls_remaining} calls remaining). "
            "Try again tomorrow or start a new project."
        )

    case_brief = load_case_brief(project_dir)
    plan = load_plan(project_dir)
    if not case_brief or not plan:
        raise RuntimeError("Missing project files.")

    angle = next((a for a in plan["angles"] if a["id"] == section_id), None)
    if not angle:
        raise RuntimeError(f"Section {section_id} not found in plan.")

    existing = load_section(project_dir, section_id)
    if not existing:
        raise RuntimeError(f"Section {section_id} not yet researched.")

    ui.print_info(f"Deepening research on {section_id}: {angle['title']}")

    from cormorant.compiler import _get_section_oneliners
    oneliners = _get_section_oneliners(project_dir)
    oneliners.pop(section_id, None)

    new_content, _, _ = research_angle(
        llm=llm,
        angle=angle,
        case_brief=case_brief,
        project_dir=project_dir,
        completed_section_oneliners=oneliners,
        buffer_calls_remaining=buffer_calls,
    )

    update_session(project_dir, calls_used=llm.flash_calls_used())
    return new_content
