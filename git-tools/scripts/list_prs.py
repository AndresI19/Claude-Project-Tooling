#!/usr/bin/env python3
"""
Lists open PRs across all workspace repos, grouped by repo with colored label badges.

Usage:
    python3 list_prs.py           # ANSI colored table
    python3 list_prs.py --json    # JSON output for programmatic use
"""

import argparse
import json
import subprocess
from datetime import datetime
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


def print_table(data):
    if not data:
        print("No open PRs across workspace repos.")
        return
    for entry in data:
        print(f"\n\033[1m{entry['repo']}\033[0m")
        print("─" * 72)
        for pr in entry["prs"]:
            title = pr["title"][:48].ljust(48)
            labels_str = " ".join(color_label(l) for l in pr["labels"]) if pr["labels"] else "—"
            print(f"  {title}  {labels_str}  {pr['updated']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON instead of colored table")
    args = parser.parse_args()

    repos = find_repos()
    data = collect_all(repos)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_table(data)


if __name__ == "__main__":
    main()
