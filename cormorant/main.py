"""CLI entry point — REPL, slash commands, top-level commands."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from cormorant import ui
from cormorant.agent import Orchestrator, dig_section
from cormorant.llm import LLMClient, QuotaExceededError
from cormorant.sessions import (
    find_latest_project,
    find_project_by_slug,
    list_projects,
    load_session,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)


# ── Config management ─────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".cormorant"
CONFIG_PATH = CONFIG_DIR / "config.toml"


def _load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            import tomli
            return tomli.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import tomli_w
    CONFIG_PATH.write_text(tomli_w.dumps(config))


def _get_api_key() -> str:
    import os

    # Priority 1: config file
    config = _load_config()
    if config.get("api_key"):
        return config["api_key"]

    # Priority 2: environment variable
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key:
        return env_key

    # Priority 3: prompt user and save
    ui.console.print("\n[#22d3ee]No API key found.[/#22d3ee]")
    ui.console.print("Get your free Gemini API key at: [link]https://aistudio.google.com[/link]")
    try:
        key = input("Paste your Gemini API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        ui.print_error("No API key provided.")
        sys.exit(1)

    if not key:
        ui.print_error("API key cannot be empty.")
        sys.exit(1)

    config["api_key"] = key
    _save_config(config)
    ui.print_success("API key saved to ~/.cormorant/config.toml")
    return key


def _make_llm() -> LLMClient:
    api_key = _get_api_key()
    return LLMClient(api_key=api_key)


# ── CLI commands ──────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Cormorant — deep research. consulting grade. runs while you sleep."""
    if ctx.invoked_subcommand is None:
        # Default: launch REPL (new or resume)
        _cmd_default()


@cli.command("new")
def cmd_new() -> None:
    """Start a new research project."""
    ui.print_banner()
    llm = _make_llm()
    orch = Orchestrator(llm)
    try:
        report_path = orch.new_project()
        if report_path.name != "report_final.md":
            ui.print_warn(f"\n[bold]Partial Draft Saved:[/bold] {report_path}")
    except KeyboardInterrupt:
        ui.print_info("Cancelled.")
    except QuotaExceededError as e:
        ui.print_error(str(e))
    except Exception as e:
        ui.print_error(f"Unexpected error: {e}")
        raise


@cli.command("resume")
@click.argument("slug", required=False)
def cmd_resume(slug: str | None = None) -> None:
    """Resume the most recent or a specific project."""
    ui.print_banner()
    if slug:
        project_dir = find_project_by_slug(slug)
        if not project_dir:
            ui.print_error(f"No project found matching '{slug}'")
            sys.exit(1)
    else:
        project_dir = find_latest_project()
        if not project_dir:
            ui.print_error("No projects found. Start one with: cormorant new")
            sys.exit(1)

    llm = _make_llm()
    orch = Orchestrator(llm)
    try:
        report_path = orch.resume_project(project_dir)
        if report_path.name != "report_final.md":
            ui.print_warn(f"\n[bold]Partial Draft Saved:[/bold] {report_path}")
    except KeyboardInterrupt:
        ui.print_info("Paused.")
    except QuotaExceededError as e:
        ui.print_error(str(e))
    except Exception as e:
        ui.print_error(f"Error: {e}")
        raise


@cli.command("status")
@click.argument("slug", required=False)
def cmd_status(slug: str | None = None) -> None:
    """Show progress of the current or specified project."""
    if slug:
        project_dir = find_project_by_slug(slug)
    else:
        project_dir = find_latest_project()

    if not project_dir:
        ui.print_error("No projects found.")
        sys.exit(1)

    session = load_session(project_dir)
    ui.print_status(session or {}, project_dir=project_dir)


@cli.command("sessions")
def cmd_sessions() -> None:
    """List all research projects."""
    projects = list_projects()
    ui.print_sessions(projects)


@cli.command("dig")
@click.argument("section_id")
@click.argument("slug", required=False)
def cmd_dig(section_id: str, slug: str | None = None) -> None:
    """Spend buffer calls deepening research on a section (e.g. S02)."""
    section_id = section_id.upper()

    if slug:
        project_dir = find_project_by_slug(slug)
    else:
        project_dir = find_latest_project()

    if not project_dir:
        ui.print_error("No project found.")
        sys.exit(1)

    llm = _make_llm()
    try:
        dig_section(llm, project_dir, section_id)
        ui.print_success(f"Section {section_id} deepened.")
        ui.print_info("Deepening complete. Section updated on disk.")
    except RuntimeError as e:
        ui.print_error(str(e))
    except QuotaExceededError as e:
        ui.print_error(str(e))


@cli.command("custom")
def cmd_custom() -> None:
    """Synthesise and save a bespoke research framework using Gemini Flash."""
    from pathlib import Path as _Path
    import json as _json
    import re as _re

    from cormorant.llm import _strip_code_fences
    from cormorant.frameworks import (
        validate_custom_framework,
        register_custom_framework,
        FRAMEWORKS,
    )

    ui.print_banner()
    ui.console.print("\n[bold #22d3ee]Custom Framework Builder[/bold #22d3ee]")
    ui.console.print("[#6b7280]Design a bespoke research framework tailored to your niche.[/#6b7280]\n")

    try:
        fw_name = input("  Framework name (e.g. 'Climate Risk Supply Chain Analysis'): ").strip()
        if not fw_name:
            ui.print_error("Framework name cannot be empty.")
            sys.exit(1)

        fw_desc = input("  Short description (1 sentence): ").strip()
        if not fw_desc:
            ui.print_error("Description cannot be empty.")
            sys.exit(1)

        fw_brief = input("  Research focus brief (2-4 sentences on the analytical lens): ").strip()
        if not fw_brief:
            ui.print_error("Brief cannot be empty.")
            sys.exit(1)
    except (EOFError, KeyboardInterrupt):
        ui.print_info("Cancelled.")
        return

    # Build a stable, slugified framework ID
    fw_id = "custom_" + _re.sub(r"[^a-z0-9]+", "_", fw_name.lower()).strip("_")[:40]
    if fw_id in FRAMEWORKS:
        ui.print_warn(f"A framework with ID '{fw_id}' already exists. Overwriting.")

    llm = _make_llm()

    # Load and fill the synthesis prompt
    prompt_path = _Path(__file__).parent / "prompts" / "custom_framework_synth.txt"
    prompt = prompt_path.read_text()
    prompt = prompt.replace("{framework_name}", fw_name)
    prompt = prompt.replace("{framework_description}", fw_desc)
    prompt = prompt.replace("{user_brief}", fw_brief)

    ui.console.print("\n[#22d3ee]Synthesising your bespoke framework via Gemini Flash...[/#22d3ee]")
    try:
        with ui.spinner("Generating 8-angle DAG..."):
            raw = llm.call_flash(prompt, call_label="custom_fw_synth")
    except Exception as e:
        ui.print_error(f"LLM synthesis failed: {e}")
        return

    # Parse the synthesised framework
    try:
        cleaned = _strip_code_fences(raw)
        # Find first { to handle any preamble
        start = cleaned.find("{")
        if start < 0:
            raise ValueError("No JSON object found in LLM response.")
        fw_data = _json.loads(cleaned[start:])
    except Exception as e:
        ui.print_error(f"Could not parse synthesised framework JSON: {e}")
        ui.console.print(f"[#6b7280]Raw LLM output:\n{raw[:500]}[/#6b7280]")
        return

    # Ensure name/description are set
    fw_data.setdefault("name", fw_name)
    fw_data.setdefault("description", fw_desc)

    # Validate the structure
    errors = validate_custom_framework(fw_data)
    if errors:
        ui.print_error("Framework validation failed:")
        for err in errors:
            ui.console.print(f"  [#ef4444]✗ {err}[/#ef4444]")
        return

    # Preview the framework to the user
    ui.console.print(f"\n[bold #22c55e]✓ Framework synthesised:[/bold #22c55e] {fw_data['name']}")
    ui.console.print(f"[#6b7280]{fw_data.get('description', '')}[/#6b7280]")
    ui.console.print(f"\n[bold]Strategic Mandate:[/bold] {fw_data.get('strategic_focus', '')}\n")
    ui.console.print("[bold #22d3ee]Research Angles:[/bold #22d3ee]")
    for angle in fw_data.get("angles", []):
        deps = ", ".join(angle.get("depends_on", [])) or "none"
        ui.console.print(f"  [#22d3ee]{angle['id']}[/#22d3ee] {angle['title']}  [#6b7280](deps: {deps})[/#6b7280]")

    try:
        confirm = input("\n  Save this framework? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ui.print_info("Cancelled.")
        return

    if confirm in ("n", "no"):
        ui.print_info("Framework discarded.")
        return

    register_custom_framework(fw_id, fw_data)
    ui.print_success(f"\nFramework '{fw_data['name']}' saved as '{fw_id}'.")
    ui.print_info("It will now appear under 'Custom Frameworks' when you run: cormorant new\n")

    try:
        launch = input("  Launch a research session with this framework now? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if launch in ("y", "yes"):
        orch = Orchestrator(llm)
        # Patch the interrogator to pre-select the new custom framework
        import cormorant.interrogator as _interrog
        _orig_select = _interrog.ui.select_framework

        def _patched_select() -> str:
            ui.print_success(f"Auto-selecting custom framework: {fw_data['name']}")
            return fw_id

        _interrog.ui.select_framework = _patched_select  # type: ignore[method-assign]
        try:
            report_path = orch.new_project()
            ui.print_success(f"\nReport: {report_path}")
        except KeyboardInterrupt:
            ui.print_info("Cancelled.")
        except QuotaExceededError as e:
            ui.print_error(str(e))
        except Exception as e:
            ui.print_error(f"Unexpected error: {e}")
            raise
        finally:
            _interrog.ui.select_framework = _orig_select  # type: ignore[method-assign]




@cli.command("quota")
@click.argument("slug", required=False)
def cmd_quota(slug: str | None = None) -> None:
    """Show today's API usage for the current project."""
    if slug:
        project_dir = find_project_by_slug(slug)
    else:
        project_dir = find_latest_project()

    llm = _make_llm()
    flash_used = llm.flash_calls_used()
    lite_used = llm.lite_calls_used()
    gemma_used = llm.gemma_calls_used()

    ui.console.print(f"\n[bold]Flash 3.1 calls today:[/bold]      {flash_used}")
    ui.console.print(f"[bold]Flash Lite 2.5 calls today:[/bold] {lite_used}")
    ui.console.print(f"[bold]Gemma calls today:[/bold]           {gemma_used}\n")

    if project_dir:
        log_path = project_dir / "quota.log"
        if log_path.exists():
            lines = log_path.read_text().splitlines()
            ui.console.print("[#6b7280]Recent calls (last 10):[/#6b7280]")
            for line in lines[-10:]:
                ui.console.print(f"  [#6b7280]{line}[/#6b7280]")


@cli.command("config")
def cmd_config() -> None:
    """View or update configuration (API key, etc.)."""
    config = _load_config()
    ui.console.print("\n[bold]Current config:[/bold]")
    if config.get("api_key"):
        ui.console.print(f"  api_key: {config['api_key'][:8]}...")
    else:
        ui.console.print("  api_key: (not set)")
    ui.console.print(f"  config file: {CONFIG_PATH}\n")

    ans = ui.confirm("Update API key?", default=False)
    if ans:
        try:
            key = input("New API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if key:
            config["api_key"] = key
            _save_config(config)
            ui.print_success("API key updated.")


@cli.command("export")
@click.argument("slug", required=False)
@click.option("--format", "fmt", default="md", type=click.Choice(["md"]), help="Export format")
def cmd_export(slug: str | None, fmt: str) -> None:
    """Export the final report."""
    if slug:
        project_dir = find_project_by_slug(slug)
    else:
        project_dir = find_latest_project()

    if not project_dir:
        ui.print_error("No project found.")
        sys.exit(1)

    report = project_dir / "report_final.md"
    draft = project_dir / "report_draft.md"

    if report.exists():
        ui.print_success(f"Report ready: {report}")
    elif draft.exists():
        ui.print_warn(f"Only draft available: {draft}")
    else:
        ui.print_error("No report found. Run the research first.")


# ── Default REPL ──────────────────────────────────────────────────────────────

def _cmd_default() -> None:
    ui.print_banner()

    projects = list_projects()
    running = [p for p in projects if p.get("status") in ("running", "paused")]

    if running:
        latest = running[0]
        ui.console.print(f"[#22d3ee]Found in-progress project:[/#22d3ee] {latest.get('topic', '')}")
        ui.console.print(f"[#6b7280]Status: {latest.get('status', '')} | Calls used: {latest.get('calls_used', 0)}[/#6b7280]")
        choice = ui.confirm("Resume this project?", default=True)
        if choice:
            project_dir = Path(latest["project_dir"])
            llm = _make_llm()
            orch = Orchestrator(llm)
            try:
                report_path = orch.resume_project(project_dir)
                ui.print_success(f"\nReport: {report_path}")
            except KeyboardInterrupt:
                ui.print_info("Paused.")
            return

    # Start new project
    llm = _make_llm()
    orch = Orchestrator(llm)
    try:
        report_path = orch.new_project()
        ui.print_success(f"\nReport: {report_path}")
    except KeyboardInterrupt:
        ui.print_info("Cancelled.")
    except QuotaExceededError as e:
        ui.print_error(str(e))
    except Exception as e:
        ui.print_error(f"Unexpected error: {e}")
        logging.exception(e)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
