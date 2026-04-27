#!/usr/bin/env python3
"""
create_issue.py — Create a GitHub issue with validated standard labels.

Usage:
    python3 create_issue.py --repo OWNER/REPO --title "..." --body "..." --label Code
    python3 create_issue.py --repo OWNER/REPO --title "..." --auto-project
"""
import argparse
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
from issues import ISSUE_LABEL_NAMES, get_or_create_issue
from project import find_active_project, get_project_node_id, add_item_to_project


def create(repo, title, body, labels, project=False):
    """Create a GitHub issue and print its URL. Returns the URL string."""
    invalid = [l for l in labels if l not in ISSUE_LABEL_NAMES]
    if invalid:
        print(f"ERROR: unknown label(s): {', '.join(invalid)}")
        print(f"  Valid labels: {', '.join(ISSUE_LABEL_NAMES)}")
        sys.exit(1)

    _, url, node_id, _ = get_or_create_issue(repo, title, body, labels)

    if project:
        owner = repo.split("/")[0]
        active = find_active_project(owner)
        if active:
            project_id = get_project_node_id(owner, active["number"])
            add_item_to_project(project_id, node_id)
            print(f"Linked to project: {active['title']}")
        else:
            print("Warning: no active project found — issue not linked to a project")

    print(url)
    return url


def main():
    parser = argparse.ArgumentParser(description="Create a GitHub issue with standard labels")
    parser.add_argument("--repo",  required=True, help="OWNER/REPO")
    parser.add_argument("--title", required=True, help="Issue title")
    parser.add_argument("--body",  default="",    help="Issue body")
    parser.add_argument("--label", action="append", default=[], dest="labels",
                        metavar="LABEL", help="Label name (repeatable)")
    parser.add_argument("--project", action="store_true", default=False,
                        help="Auto-detect the active GitHub Project and link this issue to it")
    args = parser.parse_args()

    create(
        repo=args.repo,
        title=args.title,
        body=args.body,
        labels=args.labels,
        project=args.project,
    )


if __name__ == "__main__":
    main()
