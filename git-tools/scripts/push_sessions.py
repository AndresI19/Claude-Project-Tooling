#!/usr/bin/env python3
"""
push_sessions.py — Commit and push RS-Agent-Planning session logs to origin/main.

Stages files under 'Claude Sessions/' by default. With --include-planning, also
stages files under 'Planning/' so /work-flow Inquiry/Discovery doc edits ride
along with the next /record push (the documented behavior of /work-flow). Script
and tooling changes in Claude-Project-Tooling must still go through a PR via the
/pr skill instead.

If the current branch is not main, the script switches to main first (carrying
uncommitted edits with it), commits, pushes, then switches back.

Usage:
    python3 push_sessions.py --message "Update Claude Sessions and token usage"
    python3 push_sessions.py --message "Record session + planning decision" --include-planning
"""

import argparse
import sys
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

SESSION_REPO_PATH = Path.home() / "git-workspace/claude-workspace/RS-Agent-Planning"
SESSION_DIR       = "Claude Sessions"
PLANNING_DIR      = "Planning"


def _stage_dir(repo, subdir):
    """Stage every file under <repo>/<subdir>/ in the index. No-op if missing."""
    path = SESSION_REPO_PATH / subdir
    if not path.exists():
        return
    files = [
        str(f.relative_to(SESSION_REPO_PATH))
        for f in path.rglob("*") if f.is_file()
    ]
    if files:
        repo.index.add(files)


def stage_session_files(repo):
    """Stage all files under Claude Sessions/ in the index."""
    _stage_dir(repo, SESSION_DIR)


def stage_planning_files(repo):
    """Stage all files under Planning/ in the index."""
    _stage_dir(repo, PLANNING_DIR)


def has_staged(repo):
    """Return True if the index differs from HEAD."""
    try:
        return len(repo.index.diff(repo.head.commit)) > 0
    except ValueError:
        return bool(repo.index.entries)


def main():
    parser = argparse.ArgumentParser(description="Push session logs to origin/main")
    parser.add_argument("--message", required=True, help="Commit message")
    parser.add_argument(
        "--include-planning",
        action="store_true",
        help="Also stage Planning/ edits in addition to Claude Sessions/.",
    )
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

    # ── Stage selected paths ──────────────────────────────────────────────────
    stage_session_files(repo)
    if args.include_planning:
        stage_planning_files(repo)

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
