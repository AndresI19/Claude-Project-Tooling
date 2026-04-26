#!/usr/bin/env python3
"""
create_issue.py — Create a GitHub issue with validated standard labels.

Usage:
    python3 create_issue.py --repo OWNER/REPO --title "..." --body "..." --label Code
"""
import argparse
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
from issues import ISSUE_LABEL_NAMES, get_or_create_issue


def create(repo, title, body, labels):
    """Create a GitHub issue and print its URL. Returns the URL string."""
    invalid = [l for l in labels if l not in ISSUE_LABEL_NAMES]
    if invalid:
        print(f"ERROR: unknown label(s): {', '.join(invalid)}")
        print(f"  Valid labels: {', '.join(ISSUE_LABEL_NAMES)}")
        sys.exit(1)
    _, url, _, _ = get_or_create_issue(repo, title, body, labels)
    print(url)
    return url


def main():
    parser = argparse.ArgumentParser(description="Create a GitHub issue with standard labels")
    parser.add_argument("--repo",  required=True, help="OWNER/REPO")
    parser.add_argument("--title", required=True, help="Issue title")
    parser.add_argument("--body",  default="",    help="Issue body")
    parser.add_argument("--label", action="append", default=[], dest="labels",
                        metavar="LABEL", help="Label name (repeatable)")
    args = parser.parse_args()

    invalid = [l for l in args.labels if l not in ISSUE_LABEL_NAMES]
    if invalid:
        print(f"ERROR: unknown label(s): {', '.join(invalid)}")
        print(f"  Valid labels: {', '.join(ISSUE_LABEL_NAMES)}")
        sys.exit(1)

    _, url, _, _ = get_or_create_issue(args.repo, args.title, args.body, args.labels)
    print(url)


if __name__ == "__main__":
    main()
