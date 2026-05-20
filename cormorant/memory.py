"""Living Brief management and source registry."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import tiktoken

BRIEF_MAX_TOKENS = 10000
GRANULAR_MAX_ITEMS = 10
FOUNDATIONAL_MAX_ITEMS = 20

_TOKENIZER = None


def _tok() -> tiktoken.Encoding:
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = tiktoken.get_encoding("cl100k_base")
    return _TOKENIZER


def count_tokens(text: str) -> int:
    return len(_tok().encode(text))


# ── Living Brief ─────────────────────────────────────────────────────────────

BRIEF_TEMPLATE = """\
# LIVING BRIEF — {topic}

## THESIS
{thesis}

## FOUNDATIONAL
{foundational}

## GRANULAR
{granular}

## CONTRADICTIONS LIVE
{contradictions}

## SECTIONS COMPLETE
{sections_complete}

## OPEN ANGLES
{open_angles}
"""


def init_living_brief(project_dir: Path, topic: str, thesis: str) -> None:
    brief = BRIEF_TEMPLATE.format(
        topic=topic,
        thesis=thesis,
        foundational="(none yet)",
        granular="(none yet)",
        contradictions="(none yet)",
        sections_complete="(none yet)",
        open_angles="(none yet)",
    )
    _atomic_write(project_dir / "living_brief.md", brief)


def read_living_brief(project_dir: Path) -> str:
    path = project_dir / "living_brief.md"
    if path.exists():
        return path.read_text()
    return ""


def apply_brief_delta(project_dir: Path, delta: dict) -> bool:
    """Apply a delta dict from Call 8 to the Living Brief atomically. Returns pivot_recommended."""
    path = project_dir / "living_brief.md"
    current = _parse_brief(path.read_text() if path.exists() else "")

    # confirmed_add - now handles list of {"fact": "...", "type": "foundational"|"granular"}
    for item in delta.get("confirmed_add", []):
        if isinstance(item, dict):
            fact = item.get("fact", "")
            ftype = item.get("type", "granular")
        else:
            fact = str(item)
            ftype = "granular"

        if fact:
            if ftype == "foundational" and fact not in current["foundational"]:
                current["foundational"].append(fact)
            elif ftype == "granular" and fact not in current["granular"]:
                current["granular"].append(fact)

    # confirmed_drop
    for drop in delta.get("confirmed_drop", []):
        current["foundational"] = [f for f in current["foundational"] if f != drop]
        current["granular"] = [f for f in current["granular"] if f != drop]

    # enforce max per section
    if len(current["foundational"]) > FOUNDATIONAL_MAX_ITEMS:
        current["foundational"] = current["foundational"][-FOUNDATIONAL_MAX_ITEMS:]
    if len(current["granular"]) > GRANULAR_MAX_ITEMS:
        current["granular"] = current["granular"][-GRANULAR_MAX_ITEMS:]

    # thesis_nuance
    if delta.get("thesis_nuance"):
        current["thesis"] = current["thesis"].rstrip() + " " + delta["thesis_nuance"].strip()

    # contradictions_add
    for c in delta.get("contradictions_add", []):
        if c and c not in current["contradictions"]:
            current["contradictions"].append(c)
    # contradictions_resolved
    for r in delta.get("contradictions_resolved", []):
        current["contradictions"] = [c for c in current["contradictions"] if r.lower() not in c.lower()]

    # section_complete
    sc = delta.get("section_complete")
    if sc and isinstance(sc, dict):
        entry = f"- {sc.get('id', '')} {sc.get('title', '')}: {sc.get('one_liner', '')}"
        existing_ids = [s.split()[1] for s in current["sections_complete"] if s.startswith("- ")]
        if sc.get("id") not in existing_ids:
            current["sections_complete"].append(entry)

    # new_angles_discovered
    for angle in delta.get("new_angles_discovered", []):
        if angle and angle not in current["open_angles"]:
            current["open_angles"].append(angle)

    brief_text = _render_brief(current)

    # Enforce global token cap — trim GRANULAR first, then FOUNDATIONAL
    while count_tokens(brief_text) > BRIEF_MAX_TOKENS:
        if current["granular"]:
            current["granular"].pop(0)
        elif current["foundational"]:
            current["foundational"].pop(0)
        else:
            break
        brief_text = _render_brief(current)

    _atomic_write(path, brief_text)
    return delta.get("plan_pivot_recommended", False)


def _parse_brief(text: str) -> dict:
    """Parse the Living Brief markdown into a dict of lists/strings."""
    result: dict[str, Any] = {
        "topic": "",
        "thesis": "",
        "foundational": [],
        "granular": [],
        "contradictions": [],
        "sections_complete": [],
        "open_angles": [],
    }
    if not text:
        return result

    lines = text.splitlines()
    section = None
    buffer: list[str] = []

    def flush(sec: str | None, buf: list[str]) -> None:
        content = "\n".join(buf).strip()
        if sec == "thesis":
            result["thesis"] = content
        elif sec in ("foundational", "granular", "contradictions", "sections_complete", "open_angles"):
            items = [line.lstrip("- ").strip() for line in buf if line.strip() and line.strip() != "(none yet)"]
            result[sec] = [i for i in items if i]

    for line in lines:
        if line.startswith("# LIVING BRIEF"):
            result["topic"] = line.replace("# LIVING BRIEF —", "").strip()
        elif line.startswith("## THESIS"):
            flush(section, buffer)
            section = "thesis"
            buffer = []
        elif line.startswith("## FOUNDATIONAL"):
            flush(section, buffer)
            section = "foundational"
            buffer = []
        elif line.startswith("## GRANULAR"):
            flush(section, buffer)
            section = "granular"
            buffer = []
        elif line.startswith("## CONTRADICTIONS LIVE"):
            flush(section, buffer)
            section = "contradictions"
            buffer = []
        elif line.startswith("## SECTIONS COMPLETE"):
            flush(section, buffer)
            section = "sections_complete"
            buffer = []
        elif line.startswith("## OPEN ANGLES"):
            flush(section, buffer)
            section = "open_angles"
            buffer = []
        else:
            buffer.append(line)

    flush(section, buffer)
    return result


def _render_brief(d: dict) -> str:
    def _list(items: list[str], empty: str = "(none yet)") -> str:
        if not items:
            return empty
        return "\n".join(f"- {i}" if not i.startswith("-") else i for i in items)

    return BRIEF_TEMPLATE.format(
        topic=d.get("topic", ""),
        thesis=d.get("thesis", ""),
        foundational=_list(d.get("foundational", [])),
        granular=_list(d.get("granular", [])),
        contradictions=_list(d.get("contradictions", [])),
        sections_complete=_list(d.get("sections_complete", [])),
        open_angles=_list(d.get("open_angles", [])),
    )



# ── Source Registry ───────────────────────────────────────────────────────────

def load_sources(project_dir: Path) -> dict[str, dict]:
    path = project_dir / "sources.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def register_sources(project_dir: Path, sources: list) -> None:
    """Merge new sources into sources.json atomically."""
    existing = load_sources(project_dir)
    for src in sources:
        if src.url not in existing:
            existing[src.url] = {
                "url": src.url,
                "domain": src.domain,
                "title": src.title,
                "tier": src.tier,
                "date_fetched": src.date_fetched,
                "is_paywalled": src.is_paywalled,
                "angle_id": src.angle_id,
                "use_count": 1,
            }
        else:
            existing[src.url]["use_count"] = existing[src.url].get("use_count", 1) + 1

    _atomic_write(project_dir / "sources.json", json.dumps(existing, indent=2))


def get_sources_summary(project_dir: Path) -> str:
    sources = load_sources(project_dir)
    if not sources:
        return "No sources registered yet."
    by_tier: dict[int, list] = {}
    for s in sources.values():
        t = s.get("tier", 3)
        by_tier.setdefault(t, []).append(s)
    lines = []
    for tier in sorted(by_tier):
        for s in by_tier[tier]:
            lines.append(
                f"[Tier {tier}] {s['domain']} — \"{s['title'][:60]}\" — {s['date_fetched']} — {s['url']}"
            )
    return "\n".join(lines)


# ── Atomic write ──────────────────────────────────────────────────────────────

def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise
