#!/usr/bin/env python3
"""
project_advance.py — Promote Todo/Backlog items to Ready when all blockers are closed.

Usage:
    python3 project_advance.py
    python3 project_advance.py --repo AndresI19/RS-Agent-Planning
"""
import argparse
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
from github_client import load_config
from project import query_project, advance_ready

GREEN = "\033[32m"
RESET = "\033[0m"

_cfg           = load_config()
_OWNER         = _cfg["owner"]
_PROJECT_NUMBER = _cfg["project_number"]
_REPO          = _cfg["repo"]


def run(owner=_OWNER, project_number=_PROJECT_NUMBER, repo=_REPO):
    """Advance all unblocked Todo/Backlog items to Ready. Prints each promotion."""
    project_data = query_project(owner, project_number)
    promoted = advance_ready(project_data, repo)
    if promoted:
        for number, title in promoted:
            print(f"{GREEN}✓{RESET} #{number} {title} → Ready")
        print(f"\n{len(promoted)} item(s) promoted to Ready.")
    else:
        print("No items ready to advance (blockers still open or no Todo/Backlog items).")
    return promoted


def main():
    parser = argparse.ArgumentParser(description="Advance blocked items to Ready")
    parser.add_argument("--owner",          default=_OWNER)
    parser.add_argument("--project-number", type=int, default=_PROJECT_NUMBER)
    parser.add_argument("--repo",           default=_REPO)
    args = parser.parse_args()
    run(owner=args.owner, project_number=args.project_number, repo=args.repo)


if __name__ == "__main__":
    main()
