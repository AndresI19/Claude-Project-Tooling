#!/usr/bin/env python3
"""
Lists open PRs across all workspace repos, grouped by repo with colored label badges.

Usage:
    python3 list_prs.py           # ANSI colored table (inline)
    python3 list_prs.py --window  # Open table in a new Ptyxis terminal window
    python3 list_prs.py --json    # JSON output for programmatic use
"""

import argparse
import json
import subprocess
import textwrap
from pathlib import Path

WORKSPACE = Path.home() / "git-workspace/claude-workspace"

LABEL_COLORS = {
    "trivial":       {"bg": (46, 204, 113),  "fg": (0, 0, 0)},
    "non-trivial":   {"bg": (241, 196, 15),  "fg": (0, 0, 0)},
    "complex":       {"bg": (231, 76, 60),   "fg": (255, 255, 255)},
    "integrated":    {"bg": (123, 36, 28),   "fg": (255, 255, 255)},
    "system":        {"bg": (96, 125, 139),  "fg": (255, 255, 255)},
    "documentation": {"bg": (0, 117, 202),   "fg": (255, 255, 255)},
    "fix":           {"bg": (142, 68, 173),  "fg": (255, 255, 255)},
    "enhancement":   {"bg": (162, 238, 239), "fg": (0, 0, 0)},
    "duplicate":     {"bg": (207, 211, 215), "fg": (0, 0, 0)},
    "as designed":   {"bg": (220, 220, 220), "fg": (0, 0, 0)},
}

RESET = "\033[0m"


def ansi_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"


def ansi_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def color_label(name):
    key = name.lower()
    style = LABEL_COLORS.get(key)
    if not style:
        return f" {name} "
    bg = ansi_bg(*style["bg"])
    fg = ansi_fg(*style["fg"])
    return f"{bg}{fg} {name} {RESET}"


def fetch_prs(repo):
    result = subprocess.run(
        ["gh", "pr", "list", "--repo", repo, "--state", "open",
         "--json", "number,title,labels,updatedAt"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return json.loads(result.stdout)


def find_repos():
    return sorted([
        d for d in WORKSPACE.iterdir()
        if d.is_dir() and (d / ".git").exists()
    ], key=lambda d: d.name)


def collect_all(repos):
    results = []
    for repo_path in repos:
        gh_repo_result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, cwd=repo_path
        )
        if gh_repo_result.returncode != 0:
            continue
        gh_repo = gh_repo_result.stdout.strip()
        prs = fetch_prs(gh_repo)
        if not prs:
            continue
        prs.sort(key=lambda p: p["updatedAt"], reverse=True)
        results.append({
            "repo": repo_path.name,
            "gh_repo": gh_repo,
            "prs": [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "labels": [l["name"] for l in pr["labels"]],
                    "updated": pr["updatedAt"][:10],
                }
                for pr in prs
            ],
        })
    return results


ID_GRAYS = [
    {"bg": (90, 90, 90),  "fg": (230, 230, 230)},
    {"bg": (55, 55, 55),  "fg": (210, 210, 210)},
]

REPO_BG  = (35, 38, 46)
REPO_FG  = (160, 190, 230)
UNDERLINE = "\033[4m"
NO_UNDER  = "\033[24m"

TITLE_WIDTH = 42
LABEL_WIDTH = 28
DATE_WIDTH  = 10
ID_VISIBLE  = 5   # " 12  " — leading space + 4-char number

# Chars before title column: "  " + id(5) + "  " + date(10) + "  "
TITLE_INDENT = 2 + ID_VISIBLE + 2 + DATE_WIDTH + 2   # 21
# Chars before label column
LABEL_INDENT = TITLE_INDENT + TITLE_WIDTH + 2         # 65


def wrap_labels(label_names):
    """Group label names into lines that fit within LABEL_WIDTH (by visible chars)."""
    lines, current, w = [], [], 0
    for name in label_names:
        badge_w = len(name) + 2   # " Name " visible width
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
        repo_header = f"{ansi_bg(*REPO_BG)}{ansi_fg(*REPO_FG)}\033[1m  {entry['repo']}  {RESET}"
        print(f"\n{repo_header}")
        print("─" * 72)
        for pr in entry["prs"]:
            gray = ID_GRAYS[row % 2]
            id_badge = f"{ansi_bg(*gray['bg'])}{ansi_fg(*gray['fg'])} {str(pr['number']).ljust(4)}{RESET}"
            date = f"{UNDERLINE}{pr['updated']}{NO_UNDER}"

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json",   action="store_true", help="Output JSON instead of colored table")
    parser.add_argument("--window", action="store_true", help="Open table in a new Ptyxis terminal window")
    args = parser.parse_args()

    if args.window:
        script = Path(__file__).resolve()
        cmd = f"python3 {script}; echo; read -p 'Press Enter to close'"
        subprocess.Popen(["ptyxis", "-T", "Open PRs", "--", "bash", "-c", cmd])
        return

    repos = find_repos()
    data = collect_all(repos)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_table(data)


if __name__ == "__main__":
    main()
