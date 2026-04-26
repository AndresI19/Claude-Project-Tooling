#!/usr/bin/env python3
"""
project_state.py — Project loop state and issue lifecycle helpers for work-flow.

Usage:
    python3 project_state.py --loop-state
    python3 project_state.py --close-and-promote NUMBER
    python3 project_state.py --close-and-promote NUMBER --repo AndresI19/RS-Agent-Planning
"""
import argparse
import json
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
import github_client
from github_client import load_config
from project import query_project, items_by_status, advance_ready

GREEN = "\033[32m"
RESET = "\033[0m"

_cfg           = load_config()
_OWNER         = _cfg["owner"]
_PROJECT_NUMBER = _cfg["project_number"]
_REPO          = _cfg["repo"]


def loop_state(owner=_OWNER, project_number=_PROJECT_NUMBER, repo=_REPO):
    """Return a dict with per-status item counts and the recommended next_action."""
    project_data = query_project(owner, project_number)
    counts = {
        s.lower().replace(" ", "_"): len(items_by_status(project_data, s))
        for s in ("Ready", "In Progress", "Todo", "Backlog", "Verify")
    }
    if counts["ready"] > 0 or counts["in_progress"] > 0:
        next_action = "continue"
    elif counts["todo"] > 0 or counts["backlog"] > 0:
        next_action = "blocked"
    else:
        next_action = "plan"
    return {**counts, "next_action": next_action}


def close_and_promote(issue_number, repo=_REPO, owner=_OWNER, project_number=_PROJECT_NUMBER):
    """Close an issue and promote newly unblocked items to Ready."""
    github_client.rest("PATCH", f"/repos/{repo}/issues/{issue_number}",
                       json={"state": "closed"})
    print(f"{GREEN}✓{RESET} #{issue_number} closed")

    project_data = query_project(owner, project_number)
    promoted = advance_ready(project_data, repo)
    if promoted:
        for number, title in promoted:
            print(f"{GREEN}✓{RESET} #{number} {title} → Ready")
        print(f"\n{len(promoted)} item(s) promoted to Ready.")
    else:
        print("No items ready to advance.")
    return promoted


def main():
    parser = argparse.ArgumentParser(description="Project loop state and lifecycle helpers")
    parser.add_argument("--owner",          default=_OWNER)
    parser.add_argument("--project-number", type=int, default=_PROJECT_NUMBER)
    parser.add_argument("--repo",           default=_REPO)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--loop-state",        action="store_true",
                       help="Print JSON loop state summary")
    group.add_argument("--close-and-promote", type=int, metavar="NUMBER",
                       help="Close issue NUMBER and advance newly unblocked items to Ready")
    args = parser.parse_args()

    if args.loop_state:
        state = loop_state(args.owner, args.project_number, args.repo)
        print(json.dumps(state, indent=2))
    else:
        close_and_promote(args.close_and_promote, args.repo, args.owner, args.project_number)


if __name__ == "__main__":
    main()
