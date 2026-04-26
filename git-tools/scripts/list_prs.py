#!/usr/bin/env python3
"""
list_prs.py — Display open PRs across all workspace repos.

Usage:
    python3 list_prs.py           # colored ANSI table
    python3 list_prs.py --json    # JSON output
    python3 list_prs.py --window  # open in a new Ptyxis terminal
"""
import argparse
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
from prs import collect_all_prs
from display import ansi_bg, ansi_fg

# PR-specific label color map (distinct from project issue label colors)
LABEL_COLORS = {
    "trivial":       {"bg": (46,  204, 113), "fg": (0, 0, 0)},
    "non-trivial":   {"bg": (241, 196, 15),  "fg": (0, 0, 0)},
    "complex":       {"bg": (231, 76,  60),  "fg": (255, 255, 255)},
    "integrated":    {"bg": (123, 36,  28),  "fg": (255, 255, 255)},
    "system":        {"bg": (96,  125, 139), "fg": (255, 255, 255)},
    "documentation": {"bg": (0,   117, 202), "fg": (255, 255, 255)},
    "fix":           {"bg": (142, 68,  173), "fg": (255, 255, 255)},
    "enhancement":   {"bg": (162, 238, 239), "fg": (0, 0, 0)},
    "duplicate":     {"bg": (207, 211, 215), "fg": (0, 0, 0)},
    "as designed":   {"bg": (220, 220, 220), "fg": (0, 0, 0)},
}

RESET     = "\033[0m"
BOLD      = "\033[1m"
UNDERLINE = "\033[4m"
NO_UNDER  = "\033[24m"

TITLE_WIDTH  = 42
LABEL_WIDTH  = 28
DATE_WIDTH   = 10
ID_VISIBLE   = 5
TITLE_INDENT = 2 + ID_VISIBLE + 2 + DATE_WIDTH + 2

ID_GRAYS = [
    {"bg": (90, 90, 90),  "fg": (230, 230, 230)},
    {"bg": (55, 55, 55),  "fg": (210, 210, 210)},
]

REPO_BG = (35, 38, 46)
REPO_FG = (160, 190, 230)


def color_label(name):
    style = LABEL_COLORS.get(name.lower())
    if not style:
        return f" {name} "
    return f"{ansi_bg(*style['bg'])}{ansi_fg(*style['fg'])} {name} {RESET}"


def wrap_labels(label_names):
    lines, current, w = [], [], 0
    for name in label_names:
        badge_w = len(name) + 2
        gap = 1 if current else 0
        if current and w + gap + badge_w > LABEL_WIDTH:
            lines.append(current)
            current, w = [name], badge_w
        else:
            current.append(name)
            w += gap + badge_w
    if current:
        lines.append(current)
    return lines or [[]]


def print_table(data):
    if not data:
        print("No open PRs across workspace repos.")
        return
    row = 0
    for entry in data:
        repo_header = f"{ansi_bg(*REPO_BG)}{ansi_fg(*REPO_FG)}{BOLD}  {entry['repo']}  {RESET}"
        print(f"\n{repo_header}")
        print("─" * 72)
        for pr in entry["prs"]:
            gray     = ID_GRAYS[row % 2]
            id_badge = f"{ansi_bg(*gray['bg'])}{ansi_fg(*gray['fg'])} {str(pr['number']).ljust(4)}{RESET}"
            date     = f"{UNDERLINE}{pr['updated']}{NO_UNDER}"

            title_lines  = textwrap.wrap(pr["title"], TITLE_WIDTH) or [pr["title"]]
            label_groups = wrap_labels(pr["labels"]) if pr["labels"] else [["—"]]
            colored_groups = [
                " ".join(color_label(l) for l in g) if g != ["—"] else "—"
                for g in label_groups
            ]

            n = max(len(title_lines), len(colored_groups))
            title_lines    += [""] * (n - len(title_lines))
            colored_groups += [""] * (n - len(colored_groups))

            for i, (t, lbl) in enumerate(zip(title_lines, colored_groups)):
                if i == 0:
                    print(f"  {id_badge}  {date}  {t.ljust(TITLE_WIDTH)}  {lbl}")
                else:
                    print(f"{' ' * TITLE_INDENT}{t.ljust(TITLE_WIDTH)}  {lbl}")
            row += 1


def show(json_output=False, window=False):
    """Display open PRs. Opens a Ptyxis window when window=True."""
    if window:
        script = Path(__file__).resolve()
        cmd = f"python3 {script}; echo; read -p 'Press Enter to close'"
        subprocess.Popen(["ptyxis", "-T", "Open PRs", "--", "bash", "-c", cmd])
        return
    data = collect_all_prs()
    if json_output:
        print(json.dumps(data, indent=2))
    else:
        print_table(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json",   action="store_true", help="Output JSON")
    parser.add_argument("--window", action="store_true", help="Open in a new Ptyxis terminal")
    args = parser.parse_args()
    show(json_output=args.json, window=args.window)


if __name__ == "__main__":
    main()
