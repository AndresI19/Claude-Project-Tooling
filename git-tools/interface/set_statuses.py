#!/usr/bin/env python3
"""Apply a batch of project Status mutations in one shot.

Reads a JSON array of moves on stdin:

    [
      {"item_id": "PVTI_...", "status": "Done"},
      {"item_id": "PVTI_...", "status": "Backlog"}
    ]

Used by /triage to commit an approved batch after the user authorizes.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from project import query_project, set_item_statuses
from github_client import load_config


def main():
    cfg = load_config()
    owner = cfg["owner"]
    project_number = int(os.environ.get("PROJECT_NUMBER", cfg["project_number"]))

    payload = json.load(sys.stdin)
    if not isinstance(payload, list):
        print("ERROR: stdin must be a JSON array of {item_id, status} objects.", file=sys.stderr)
        sys.exit(1)

    moves = [(m["item_id"], m["status"]) for m in payload]
    if not moves:
        print("No moves to apply.")
        return

    project_data = query_project(owner, project_number)
    applied = set_item_statuses(project_data, moves)
    print(f"\033[32m✓\033[0m {applied} status mutation(s) applied.")


if __name__ == "__main__":
    main()
