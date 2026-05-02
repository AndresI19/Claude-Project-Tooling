#!/usr/bin/env python3
"""
Initializes the standard label set on a GitHub repository.
Creates missing labels, skips ones that already exist.
Removes GitHub default labels not in the standard set.

Usage:
    python3 init_labels.py --repo OWNER/REPO
"""

import argparse
import json
import subprocess
import sys

STANDARD_LABELS = [
    # PR review-effort vocabulary (used by /review and /ultrareview)
    {"name": "Trivial",       "color": "2ecc71", "description": "Can be evaluated quickly"},
    {"name": "Non-Trivial",   "color": "f1c40f", "description": "Needs a scan through, but is largely harmless"},
    {"name": "Complex",       "color": "e74c3c", "description": "Requires focused review, a step above Non-Trivial"},
    {"name": "Integrated",    "color": "7b241c", "description": "Core structural changes likely to break without human review"},
    {"name": "System",        "color": "607d8b", "description": "Changes to OS, containerization, or automation"},
    {"name": "Documentation", "color": "0075ca", "description": "Includes documentation updates"},
    {"name": "Fix",           "color": "8e44ad", "description": "Bug fix or correction"},
    {"name": "Enhancement",   "color": "a2eeef", "description": "New feature or request"},
    {"name": "Duplicate",     "color": "cfd3d7", "description": "This issue or pull request already exists"},
    {"name": "As Designed",   "color": "ffffff", "description": "Intended behavior, not a bug"},
    # Issue-routing vocabulary (used by /todo and /git-plan)
    {"name": "Code",          "color": "1d76db", "description": "Writing new feature code"},
    {"name": "Defect",        "color": "d73a4a", "description": "Fixing broken or incorrect behavior"},
    {"name": "Discovery",     "color": "5319e7", "description": "Investigation or research needed before work can start"},
    {"name": "Inquiry",       "color": "fbca04", "description": "Open design question that must be resolved first"},
    {"name": "DevOps",        "color": "006b75", "description": "Infrastructure, deployment, CI/CD, or automation work"},
    {"name": "Epic",          "color": "9e0142", "description": "Top-level work group (managed by /git-plan)"},
]

STANDARD_NAMES = {l["name"].lower() for l in STANDARD_LABELS}

REMOVE_DEFAULTS = {"bug", "documentation", "good first issue", "help wanted", "invalid", "question", "wontfix"}


def run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\nERROR: command failed (exit {result.returncode})")
        print(f"  CMD:    {' '.join(args)}")
        if result.stdout.strip():
            print(f"  STDOUT: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"  STDERR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Initialize standard labels on a GitHub repo")
    parser.add_argument("--repo", required=True, help="Owner/repo (e.g. AndresI19/Claude-Project-Tooling)")
    args = parser.parse_args()

    existing_raw = run(["gh", "label", "list", "--repo", args.repo, "--json", "name"])
    existing = {l["name"].lower() for l in json.loads(existing_raw)}

    # Remove unwanted defaults
    for name in REMOVE_DEFAULTS:
        if name in existing:
            run(["gh", "label", "delete", name, "--repo", args.repo, "--yes"])
            print(f"  Removed: {name}")

    # Create missing standard labels
    for label in STANDARD_LABELS:
        if label["name"].lower() not in existing:
            run(["gh", "label", "create", label["name"],
                 "--repo", args.repo,
                 "--color", label["color"],
                 "--description", label["description"]])
            print(f"  Created: {label['name']}")
        else:
            print(f"  Exists:  {label['name']} — skipped")

    print(f"\nDone. Labels initialized for {args.repo}.")


if __name__ == "__main__":
    main()
