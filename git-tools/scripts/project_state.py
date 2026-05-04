#!/usr/bin/env python3
"""
project_state.py — Project loop state helper for work-flow.

Usage:
    python3 project_state.py --loop-state
"""
import argparse
import json
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
from github_client import load_config
from project import query_project, items_by_status

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


def main():
    parser = argparse.ArgumentParser(description="Project loop state helper")
    parser.add_argument("--owner",          default=_OWNER)
    parser.add_argument("--project-number", type=int, default=_PROJECT_NUMBER)
    parser.add_argument("--repo",           default=_REPO)
    parser.add_argument("--loop-state",     action="store_true", required=True,
                        help="Print JSON loop state summary")
    args = parser.parse_args()

    state = loop_state(args.owner, args.project_number, args.repo)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
