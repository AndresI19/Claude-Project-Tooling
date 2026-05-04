#!/usr/bin/env python3
"""List every GitHub Project for the configured owner.

Usage:
    python3 list_projects.py             # formatted selector menu
    python3 list_projects.py --json      # machine-readable JSON
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from projects import list_all_projects, find_oldest_active
from github_client import load_config
from status_emojis import STATUS_EMOJI, legend as status_legend

# ANSI helpers (kept inline — display.py covers richer rendering but this
# script is intentionally lightweight so /git-plan and /triage can both use it).
RESET   = "\033[0m"
DIM     = "\033[2m"
BOLD    = "\033[1m"
DEFAULT = "\033[44m"   # blue background → /work-flow default row


def _format_counts(counts):
    """Render a status-counts dict like {'Ready': 5, 'In Progress': 2} as
    '5 ⚪ · 2 🔵' in the same lifecycle order as STATUS_EMOJI."""
    parts = []
    for name, emoji in STATUS_EMOJI.items():
        if counts.get(name):
            parts.append(f"{counts[name]} {emoji}")
    return " · ".join(parts) if parts else "(empty)"


def render_menu(projects, oldest_number, include_create_new=True):
    """Return a multi-line string of the selector menu."""
    if not projects:
        if include_create_new:
            return "No projects yet. Pick `0` to create one.\n\n  0.  + Create new project\n"
        return "No projects yet.\n"

    width = max(len(p["title"]) for p in projects)
    lines = ["Pick a project:\n"]
    for i, p in enumerate(projects, start=1):
        title  = p["title"].ljust(width)
        counts = _format_counts(p["status_counts"])
        date   = p["createdAt"][:10]   # YYYY-MM-DD
        suffix = "  ← /work-flow default" if p["number"] == oldest_number else ""
        prefix = DEFAULT if p["number"] == oldest_number else ""
        body   = f"  {i:>2}. ⚪ {title}   {counts}   created {date}{suffix}"
        lines.append(f"{prefix}{body}{RESET}" if prefix else body)
    if include_create_new:
        lines.append("")
        lines.append(f"   0. {BOLD}+ Create new project{RESET}")
    lines.append("")
    lines.append(f"Legend: {status_legend()}")
    lines.append("")
    lines.append("Pick? (number, or 0 to cancel)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="List GitHub Projects for the configured owner")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a formatted menu")
    parser.add_argument("--no-create-new", action="store_true",
                        help="omit the '0. Create new project' row (used by /triage)")
    parser.add_argument("--include-closed", action="store_true",
                        help="include closed/archived projects in the output (hidden by default)")
    args = parser.parse_args()

    cfg = load_config()
    owner = cfg["owner"]

    projects = list_all_projects(owner)
    if not args.include_closed:
        projects = [p for p in projects if not p["closed"]]
    # Default sort: oldest first (matches the "oldest is /work-flow default" surface).
    projects.sort(key=lambda p: p["createdAt"])

    oldest = find_oldest_active(owner)
    oldest_number = oldest["number"] if oldest else None

    if args.json:
        print(json.dumps({
            "projects":      projects,
            "oldest_active": oldest_number,
        }, indent=2))
        return

    print(render_menu(projects, oldest_number, include_create_new=not args.no_create_new))


if __name__ == "__main__":
    main()
