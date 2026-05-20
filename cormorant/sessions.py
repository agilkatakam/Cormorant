"""Project persistence, session management, and resume capability."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"


def _slug(topic: str) -> str:
    s = topic.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s[:40]


def create_project(topic: str) -> Path:
    date_str = datetime.now().strftime("%Y%m%d")
    project_id = f"{_slug(topic)}_{date_str}"
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "sections").mkdir(exist_ok=True)
    (project_dir / "cache").mkdir(exist_ok=True)
    return project_dir


def save_session(project_dir: Path, state: dict) -> None:
    from cormorant.memory import _atomic_write
    path = project_dir / "session.json"
    _atomic_write(path, json.dumps(state, indent=2))


def load_session(project_dir: Path) -> dict | None:
    path = project_dir / "session.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def get_project_id(project_dir: Path) -> str:
    return project_dir.name


def init_session(
    project_dir: Path,
    topic: str,
    case_brief: dict,
    plan: dict,
) -> dict:
    state = {
        "project_id": get_project_id(project_dir),
        "topic": topic,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "current_phase": "planning",
        "current_angle": None,
        "current_call": 0,
        "calls_used": 0,
        "calls_remaining": 250,
        "completed_angles": [],
        "status": "running",
    }
    save_session(project_dir, state)
    return state


def update_session(project_dir: Path, **kwargs: Any) -> dict:
    state = load_session(project_dir) or {}
    state.update(kwargs)
    save_session(project_dir, state)
    return state


def list_projects() -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []
    projects = []
    for p in sorted(PROJECTS_DIR.iterdir(), reverse=True):
        if not p.is_dir():
            continue
        session = load_session(p)
        if session:
            projects.append(session | {"project_dir": str(p)})
    return projects


def find_latest_project() -> Path | None:
    if not PROJECTS_DIR.exists():
        return None
    dirs = sorted(
        [d for d in PROJECTS_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return dirs[0] if dirs else None


def find_project_by_slug(slug: str) -> Path | None:
    if not PROJECTS_DIR.exists():
        return None
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir() and slug in d.name:
            return d
    return None


def save_case_brief(project_dir: Path, brief: dict) -> None:
    from cormorant.memory import _atomic_write
    _atomic_write(project_dir / "case_brief.json", json.dumps(brief, indent=2))


def load_case_brief(project_dir: Path) -> dict | None:
    path = project_dir / "case_brief.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_plan(project_dir: Path, plan: dict) -> None:
    from cormorant.memory import _atomic_write
    _atomic_write(project_dir / "plan.json", json.dumps(plan, indent=2))


def load_plan(project_dir: Path) -> dict | None:
    path = project_dir / "plan.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_section(project_dir: Path, angle_id: str, title: str, content: str) -> None:
    from cormorant.memory import _atomic_write
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:30]
    filename = f"{angle_id}_{slug}.md"
    _atomic_write(project_dir / "sections" / filename, content)


def load_section(project_dir: Path, angle_id: str) -> str | None:
    sections_dir = project_dir / "sections"
    if not sections_dir.exists():
        return None
    for f in sections_dir.iterdir():
        if f.name.startswith(angle_id):
            return f.read_text()
    return None


def load_all_sections(project_dir: Path) -> dict[str, str]:
    sections_dir = project_dir / "sections"
    result = {}
    if not sections_dir.exists():
        return result
    for f in sorted(sections_dir.iterdir()):
        angle_id = f.name.split("_")[0]
        result[angle_id] = f.read_text()
    return result


def section_word_count(content: str) -> int:
    return len(content.split())


def section_source_count(content: str) -> int:
    import re
    return len(re.findall(r"\[[\w.]+,\s*\d{4}", content))
