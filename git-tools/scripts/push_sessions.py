#!/usr/bin/env python3
"""
Pushes changes in RS-Agent-Planning and Claude-Project-Tooling to origin/main.

Usage:
    python3 push_sessions.py --message "Update Claude Sessions and token usage"
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPOS = [
    Path.home() / "git-workspace/claude-workspace/RS-Agent-Planning",
    Path.home() / "git-workspace/claude-workspace/Claude-Project-Tooling",
]


def run(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\nERROR: command failed (exit {result.returncode})")
        print(f"  CMD:    {' '.join(args)}")
        if result.stdout.strip():
            print(f"  STDOUT: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"  STDERR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def has_changes(repo):
    result = subprocess.run(
        ["git", "status", "--short"], cwd=repo, capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="Push session logs to origin/main")
    parser.add_argument("--message", required=True, help="Commit message")
    args = parser.parse_args()

    for repo in REPOS:
        name = repo.name
        if not has_changes(repo):
            print(f"  {name}: nothing to commit — skipped")
            continue

        run(["git", "add", "-A"], cwd=repo)
        run(["git", "commit", "-m", args.message], cwd=repo)
        run(["git", "push", "origin", "main"], cwd=repo)
        print(f"  {name}: pushed")


if __name__ == "__main__":
    main()
