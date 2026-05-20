"""Terminal UI — banner, progress bars, status display using rich."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

BANNER = r"""
   ██████╗ ██████╗ ██████╗ ███╗   ███╗ ██████╗ ██████╗  █████╗ ███╗   ██╗████████╗
  ██╔════╝██╔═══██╗██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██╔══██╗████╗  ██║╚══██╔══╝
  ██║     ██║   ██║██████╔╝██╔████╔██║██║   ██║██████╔╝███████║██╔██╗ ██║   ██║
  ██║     ██║   ██║██╔══██╗██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║██║╚██╗██║   ██║
  ╚██████╗╚██████╔╝██║  ██║██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║██║ ╚████║   ██║
   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝
"""

TAGLINE = "deep research. consulting grade. runs while you sleep."


def print_banner() -> None:
    paths_to_check = [
        Path("cormorant_ascii.txt"),
        Path(__file__).parent / "cormorant_ascii.txt",
        Path(__file__).parent.parent / "cormorant_ascii.txt",
    ]
    
    bird_art = None
    for path in paths_to_check:
        if path.exists() and path.is_file():
            try:
                bird_art = path.read_text(encoding="utf-8")
                break
            except Exception:
                pass
                
    if bird_art:
        lines = bird_art.splitlines()
        total_lines = len(lines)
        color_start = "#22d3ee"  # Vibrant cyan
        color_end = "#4f46e5"    # Royal/indigo blue
        
        gradient_text = Text()
        for idx, line in enumerate(lines):
            factor = idx / max(1, total_lines - 1)
            c1 = color_start.lstrip("#")
            c2 = color_end.lstrip("#")
            r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
            r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
            
            r = int(r1 + factor * (r2 - r1))
            g = int(g1 + factor * (g2 - g1))
            b = int(b1 + factor * (b2 - b1))
            
            color_hex = f"#{r:02x}{g:02x}{b:02x}"
            gradient_text.append(line + "\n", style=color_hex)
            
        console.print(gradient_text, soft_wrap=True)
    else:
        console.print(Text(BANNER, style="cyan"))
        console.print(Text(f"   {TAGLINE}\n", style="#6b7280"))



def select_framework() -> str:
    from cormorant.frameworks import list_categories
    categories = list_categories()
    
    # 1. Select Category
    console.print("\n[bold #22d3ee]Select a Consulting Domain:[/bold #22d3ee]")
    cat_list = list(categories.keys())
    
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("No.", style="#22d3ee", justify="right")
    table.add_column("Domain", style="white bold")
    for i, cat in enumerate(cat_list, 1):
        table.add_row(f"{i}.", cat)
    console.print(table)
    
    cat_idx = -1
    while True:
        try:
            ans = input("  Domain #> ").strip()
            if ans.isdigit() and 1 <= int(ans) <= len(cat_list):
                cat_idx = int(ans) - 1
                break
            console.print("[#ef4444]Invalid selection. Enter a number.[/#ef4444]")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt("User cancelled")

    selected_cat = cat_list[cat_idx]
    frameworks = categories[selected_cat]

    # 2. Select Framework
    console.print(f"\n[bold #22d3ee]Select a Framework under '{selected_cat}':[/bold #22d3ee]")
    fw_table = Table(box=box.SIMPLE, show_header=True, header_style="#22d3ee")
    fw_table.add_column("No.", style="#22d3ee", justify="right")
    fw_table.add_column("Framework", style="white bold")
    fw_table.add_column("Description", style="#6b7280")
    
    for i, (f_id, f_name, f_desc) in enumerate(frameworks, 1):
        fw_table.add_row(f"{i}.", f_name, f_desc)
    console.print(fw_table)

    fw_idx = -1
    while True:
        try:
            ans = input("  Framework #> ").strip()
            if ans.isdigit() and 1 <= int(ans) <= len(frameworks):
                fw_idx = int(ans) - 1
                break
            console.print("[#ef4444]Invalid selection. Enter a number.[/#ef4444]")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt("User cancelled")
            
    f_id, f_name, _ = frameworks[fw_idx]
    console.print(f"\n[#22c55e]Selected Framework:[/#22c55e] {f_name}\n")
    return f_id



def print_status(session: dict, project_dir: Path | None = None) -> None:
    if not session:
        console.print("[#ef4444]No active project found.[/#ef4444]")
        return

    topic = session.get("topic", "Unknown")
    created_at = session.get("created_at", "")
    calls_used = session.get("calls_used", 0)
    completed_angles = session.get("completed_angles", [])
    current_angle = session.get("current_angle")
    current_call = session.get("current_call", 0)
    status = session.get("status", "unknown")

    # Time elapsed
    elapsed_str = ""
    if created_at:
        try:
            start = datetime.fromisoformat(created_at)
            elapsed = datetime.now() - start
            h, rem = divmod(int(elapsed.total_seconds()), 3600)
            m = rem // 60
            elapsed_str = f"({h}h {m}m ago)" if h else f"({m}m ago)"
        except Exception:
            pass

    console.print(f"\n[bold #22d3ee]Project:[/bold #22d3ee] {topic}")
    if created_at:
        console.print(f"[#6b7280]Started:[/#6b7280] {created_at[:16]} {elapsed_str}")
    console.print()

    # Angles progress
    total_angles = 8
    done = len(completed_angles)
    bar_filled = int((done / total_angles) * 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    console.print(f"  [[#22d3ee]{bar}[/#22d3ee]] {done}/{total_angles} angles complete\n")

    # Per-angle status — load from sessions if project_dir provided
    if project_dir:
        from cormorant.sessions import load_all_sections, section_word_count, section_source_count, load_plan
        plan = load_plan(project_dir)
        sections = load_all_sections(project_dir)
        angles = plan.get("angles", []) if plan else []
        order = plan.get("execution_order", [f"S0{i}" for i in range(1, 9)]) if plan else []

        for angle_id in order:
            angle = next((a for a in angles if a["id"] == angle_id), None)
            title = angle["title"] if angle else angle_id
            if angle_id in completed_angles and angle_id in sections:
                words = section_word_count(sections[angle_id])
                srcs = section_source_count(sections[angle_id])
                console.print(f"    [#22c55e]✓[/#22c55e] {angle_id} {title:<35} ({srcs} sources, {words} words)")
            elif angle_id == current_angle:
                console.print(f"    [#22d3ee]⟳[/#22d3ee] {angle_id} {title:<35} [#6b7280]in progress... (Call {current_call} of 10)[/#6b7280]")
            else:
                console.print(f"    [#6b7280]  {angle_id} {title:<35} pending[/#6b7280]")

    console.print()
    console.print(f"  [bold]Flash calls today:[/bold]  {calls_used} / 150")
    console.print(f"  [bold]Status:[/bold]                  {status}")

    if project_dir:
        report_path = project_dir / "report_final.md"
        if report_path.exists():
            console.print(f"\n  [#22c55e]Report ready:[/#22c55e] {report_path}")
        else:
            draft = project_dir / "report_draft.md"
            if draft.exists():
                console.print(f"\n  [#6b7280]Draft in progress:[/#6b7280] {draft}")

    console.print()


def print_research_start(topic: str) -> None:
    console.print(f"\n[#22d3ee]Starting research:[/#22d3ee] {topic}")
    console.print("[#6b7280]State persists to disk. You can close this terminal at any time.[/#6b7280]")
    console.print("[#6b7280]This is a high-depth, long process making a high volume of structured LLM calls[/#6b7280]")
    console.print("[#6b7280]to perform exhaustive extraction, adversarial cross-checking, and peer review.[/#6b7280]\n")


def print_angle_start(angle_id: str, title: str) -> None:
    console.print(f"\n[bold #22d3ee]{angle_id}[/bold #22d3ee] [white]{title}[/white]")


def print_angle_complete(angle_id: str, title: str, word_count: int, source_count: int) -> None:
    console.print(
        f"[#22c55e]✓[/#22c55e] {angle_id} complete. "
        f"{source_count} sources, {word_count} words."
    )


def print_call_progress(call_num: int, total: int, label: str) -> None:
    console.print(f"  [#6b7280]Call {call_num}/{total}:[/#6b7280] {label}", end="\r")


def print_rate_limit_sleep(seconds: float) -> None:
    console.print(f"  [#ff8a3d]Rate limit — sleeping {seconds:.0f}s...[/#ff8a3d]")


def print_quota_warning(used: int, total: int) -> None:
    console.print(f"  [#ff8a3d]Warning: {used}/{total} Flash calls used today.[/#ff8a3d]")


def print_error(msg: str) -> None:
    console.print(f"[#ef4444]Error:[/#ef4444] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[#6b7280]{msg}[/#6b7280]")


def print_success(msg: str) -> None:
    console.print(f"[#22c55e]{msg}[/#22c55e]")


def print_warn(msg: str) -> None:
    console.print(f"[#ff8a3d]{msg}[/#ff8a3d]")


def prompt_user(prompt_text: str) -> str:
    console.print(f"\n[#22d3ee]Cormorant:[/#22d3ee] {prompt_text}")
    try:
        return input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def confirm(prompt_text: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    console.print(f"\n[#22d3ee]{prompt_text}[/#22d3ee] {hint}")
    try:
        ans = input("  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not ans:
        return default
    return ans.startswith("y")


def print_plan(plan: dict) -> None:
    console.print("\n[bold #22d3ee]Research Plan[/bold #22d3ee]\n")
    for angle in plan.get("angles", []):
        console.print(f"  [#22d3ee]{angle['id']}[/#22d3ee]  {angle['title']}")
        for q in angle.get("key_questions", [])[:2]:
            console.print(f"       [#6b7280]• {q}[/#6b7280]")
    console.print()


def print_sessions(projects: list[dict]) -> None:
    if not projects:
        console.print("[#6b7280]No projects found.[/#6b7280]")
        return
    table = Table(box=box.SIMPLE, show_header=True, header_style="#22d3ee")
    table.add_column("ID")
    table.add_column("Topic")
    table.add_column("Status")
    table.add_column("Calls")
    table.add_column("Started")
    for p in projects:
        table.add_row(
            p.get("project_id", ""),
            p.get("topic", "")[:40],
            p.get("status", ""),
            str(p.get("calls_used", 0)),
            p.get("created_at", "")[:16],
        )
    console.print(table)


def stream_print(text: str, prefix: str = "") -> None:
    """Print text word-by-word with live Markdown rendering."""
    import time
    import random
    from rich.live import Live
    from rich.markdown import Markdown
    
    words = text.split(" ")
    accumulated = ""
    
    with Live(Markdown(""), refresh_per_second=20, console=console, transient=False) as live:
        for i, word in enumerate(words):
            accumulated += word + (" " if i < len(words) - 1 else "")
            display_text = f"{prefix} {accumulated}" if prefix else accumulated
            live.update(Markdown(display_text))
            # Natural typing rhythm
            time.sleep(random.uniform(0.01, 0.04))


class ResearchDashboard:
    """A live-updating dashboard for the research phase."""
    
    def __init__(self, topic: str, angle_title: str, angle_id: str = "S01"):
        self.topic = topic
        self.angle_title = angle_title
        self.angle_id = angle_id
        self.current_step = ""
        self.current_source = ""
        self.recent_atoms: list[str] = []
        self.progress = 0
        self._live = None

    def _make_renderable(self):
        from rich.panel import Panel
        from rich.table import Table
        import re
        
        # Calculate overall project progress (0-100%)
        try:
            angle_idx = int(re.sub(r"\D", "", self.angle_id))
        except Exception:
            angle_idx = 1
            
        completed_steps = (angle_idx - 1) * 20 + self.progress
        total_steps = 8 * 20
        overall_percent = int((completed_steps / total_steps) * 100)
        overall_percent = min(100, max(0, overall_percent))
        
        # Stats Table
        stats_table = Table.grid(expand=True)
        stats_table.add_column(style="bold #4f46e5", width=14)
        stats_table.add_column(style="white")
        stats_table.add_row("Topic:", self.topic[:45] + ("..." if len(self.topic) > 45 else ""))
        stats_table.add_row("Angle:", f"[{self.angle_id}] {self.angle_title}")
        stats_table.add_row("Current Step:", f"[white]{self.current_step}[/white]" if self.current_step else "[dim]initializing[/dim]")
        stats_table.add_row("Source:", f"[#818cf8]{self.current_source[:45]}...[/#818cf8]" if self.current_source else "[dim]none[/dim]")
        
        # Atom / Facts Feed (No emojis, highly clean)
        feed_table = Table.grid(padding=(0, 1))
        feed_table.add_column(style="#22d3ee", width=2)
        feed_table.add_column(style="#9ca3af", no_wrap=False)  # dim gray for text
        
        display_atoms = self.recent_atoms[-4:]
        for a in display_atoms:
            clean_atom = a.replace("\n", " ").strip()
            if len(clean_atom) > 75:
                clean_atom = clean_atom[:72] + "..."
            feed_table.add_row("-", clean_atom)
            
        if not display_atoms:
            feed_table.add_row("-", "waiting for facts")
            
        # Body Grid
        body_table = Table.grid(expand=True, padding=(0, 1))
        body_table.add_column(ratio=1)
        body_table.add_column(ratio=2)
        body_table.add_row(
            Panel(stats_table, title="[bold #22d3ee]Research Status[/bold #22d3ee]", border_style="#4f46e5", padding=(1, 2)),
            Panel(feed_table, title=f"[bold #22d3ee]Facts Extracted ({len(self.recent_atoms)})[/bold #22d3ee]", border_style="#374151", padding=(1, 2))
        )
        
        # Long, beautiful minimalist progress bar with high-fidelity blue fade gradient dynamically scaling to full screen length
        bar_width = max(30, console.width - 14)
        filled_chars = int((overall_percent / 100.0) * bar_width)
        
        # Cohesive Indigo to Cyan Gradient Transition
        colors = ["#312e81", "#4338ca", "#4f46e5", "#6366f1", "#818cf8", "#22d3ee"]
        bar_parts = []
        for idx in range(filled_chars):
            color_idx = min(len(colors) - 1, int((idx / max(1, filled_chars)) * len(colors)))
            bar_parts.append(f"[{colors[color_idx]}]█[/{colors[color_idx]}]")
            
        unfilled_bar = "[#1f2937]" + "░" * (bar_width - filled_chars) + "[/#1f2937]"
        progress_str = f" [bold #22d3ee]{overall_percent}%[/bold #22d3ee]"
        
        bar_table = Table.grid(expand=True)
        bar_table.add_row(f"  {''.join(bar_parts)}{unfilled_bar}{progress_str}")
        
        # Single unified panel structure
        main_table = Table.grid(expand=True, padding=(0, 1))
        main_table.add_row(body_table)
        main_table.add_row(
            Panel(
                bar_table, 
                title=f"[bold #22d3ee]Overall Progress - Phase {angle_idx} of 8 ({self.angle_title})[/bold #22d3ee]", 
                border_style="#374151", 
                padding=(0, 1)
            )
        )
        
        return main_table
    
    def update(self, step: str = "", source: str = "", atom: str = "", progress: int = -1):
        if step:
            self.current_step = step
        if source:
            self.current_source = source
        if atom:
            self.recent_atoms.append(atom)
        if progress >= 0:
            self.progress = progress
        if self._live:
            self._live.update(self._make_renderable(), refresh=True)
        else:
            # Clean static fallback for non-interactive or basic terminals
            if step or progress >= 0:
                import re
                try:
                    angle_idx = int(re.sub(r"\D", "", self.angle_id))
                except Exception:
                    angle_idx = 1
                completed_steps = (angle_idx - 1) * 20 + max(0, progress)
                overall_percent = int((completed_steps / 160) * 100)
                overall_percent = min(100, max(0, overall_percent))
                
                prog_str = f" [Overall Progress: {overall_percent}%]"
                step_str = f" - {step}" if step else ""
                src_str = f" ({source})" if source else ""
                console.print(f"[bold #4f46e5][Dashboard][/bold #4f46e5]{prog_str}{step_str}{src_str}")
            if atom:
                clean_atom = atom.replace("\n", " ").strip()
                if len(clean_atom) > 75:
                    clean_atom = clean_atom[:72] + "..."
                console.print(f"  [#22d3ee]-[/#22d3ee] [dim]{clean_atom}[/dim]")

    def __enter__(self):
        # Only start Live if we are in an interactive, cursor-controlled terminal
        if console.is_interactive:
            from rich.live import Live
            # Suppress auto_refresh thread to prevent rendering empty panels/colliding logs
            self._live = Live(
                self._make_renderable(),
                console=console,
                auto_refresh=False,
                transient=True
            )
            self._live.start()
        else:
            self._live = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._live:
            self._live.stop()


class CormorantSpinner:
    """A dynamic spinner with cormorant-themed phrases."""
    
    PHRASES = [
        "Flying...",
        "Gliding...",
        "Diving for data...",
        "Scanning the horizon...",
        "Perched and observing...",
        "Wingspan spreading...",
        "Skimming the surface...",
        "Adjusting plumage...",
        "Navigating the updrafts..."
    ]

    def __init__(self, label: str | None = None):
        self.label = label
        self._progress = Progress(
            SpinnerColumn(spinner_name="dots", style="#22d3ee"),
            TextColumn("[#6b7280]{task.description}[/#6b7280]"),
            transient=True,
            console=console,
        )
        self._task_id = None

    def __enter__(self):
        import random
        phrase = self.label or random.choice(self.PHRASES)
        self._progress.start()
        self._task_id = self._progress.add_task(description=phrase, total=None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._progress.stop()


def spinner(label: str | None = None):
    """Context manager for a spinner during long operations."""
    return CormorantSpinner(label)
