#!/usr/bin/env python3
"""
push_sessions.py — Commit and push RS-Agent-Planning session logs to origin/main.

Only stages files under 'Claude Sessions/' — script and tooling changes in
Claude-Project-Tooling must go through a PR via the /pr skill instead.

If the current branch is not main, the script switches to main first (carrying
uncommitted session log edits with it), commits, pushes, then switches back.

Usage:
    python3 push_sessions.py --message "Update Claude Sessions and token usage"
"""

import argparse
import sys
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

SESSION_REPO_PATH = Path.home() / "git-workspace/claude-workspace/RS-Agent-Planning"
SESSION_DIR       = "Claude Sessions"


def stage_session_files(repo):
    """Stage all files under Claude Sessions/ in the index."""
    session_path = SESSION_REPO_PATH / SESSION_DIR
    files = [
        str(f.relative_to(SESSION_REPO_PATH))
        for f in session_path.rglob("*") if f.is_file()
    ]
    if files:
        repo.index.add(files)


def has_staged(repo):
    """Return True if the index differs from HEAD."""
    try:
        return len(repo.index.diff(repo.head.commit)) > 0
    except ValueError:
        return bool(repo.index.entries)


def main():
    parser = argparse.ArgumentParser(description="Push session logs to origin/main")
    parser.add_argument("--message", required=True, help="Commit message")
    args = parser.parse_args()

    repo = Repo(SESSION_REPO_PATH)
    name = SESSION_REPO_PATH.name

    # ── Detect current branch ─────────────────────────────────────────────────
    current_branch = repo.active_branch.name

    # ── Switch to main if needed ──────────────────────────────────────────────
    # git checkout main carries uncommitted changes to tracked files that don't
    # conflict with the branch difference (session log edits qualify).
    switched = False
    if current_branch != "main":
        try:
            repo.git.checkout("main")
        except GitCommandError as e:
            print(f"ERROR: could not switch {name} to main.")
            print("  Stash or commit your branch changes first, then re-run /record.")
            print(f"  {e}")
            sys.exit(1)
        try:
            repo.git.pull("origin", "main", "--ff-only")
        except GitCommandError as e:
            print(f"ERROR: could not fast-forward pull origin/main in {name}.")
            print("  The remote has diverged. Resolve manually, then re-run /record.")
            print(f"  {e}")
            repo.git.checkout(current_branch)
            sys.exit(1)
        switched = True

    # ── Stage only session log files ──────────────────────────────────────────
    stage_session_files(repo)

    if not has_staged(repo):
        print(f"  {name}: nothing to commit — skipped")
        if switched:
            repo.git.checkout(current_branch)
        return

    # ── Commit and push ───────────────────────────────────────────────────────
    repo.index.commit(args.message)
    push_info = repo.remotes.origin.push("main")
    for info in push_info:
        if info.flags & info.ERROR:
            print(f"ERROR: push to origin/main failed: {info.summary.strip()}")
            if switched:
                repo.git.checkout(current_branch)
            sys.exit(1)
    print(f"  {name}: pushed")

    # ── Restore original branch ───────────────────────────────────────────────
    if switched:
        repo.git.checkout(current_branch)
        print(f"  {name}: restored to branch '{current_branch}'")


if __name__ == "__main__":
    main()
