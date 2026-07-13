#!/usr/bin/env python3
"""
push_wiki.py — Publish a directory of Markdown pages to a GitHub repo's wiki.

A GitHub wiki is a separate `<repo>.wiki.git` repository whose only branch is
`master`. The branch-check.sh PreToolUse hook blocks `git push` to master from the
Bash tool; this script performs the push through GitPython (not a Bash `git push`),
which is the sanctioned bypass for legitimate master pushes — the same pattern
push_sessions.py uses for origin/main. Invoked by the /git-wiki skill.

The wiki must already be initialized: GitHub does not create the `.wiki.git` repo
until at least one page exists (create it once via the repo's Wiki tab in the web
UI). If the clone fails with "Repository not found", that bootstrap step is missing.

Pages are copied into a fresh clone, so existing wiki pages with the same filename
are overwritten and new ones are added; untouched pages are left in place.

Usage:
    python3 push_wiki.py --repo OWNER/REPO --pages-dir /path/to/pages \
        --message "Migrate docs into the wiki"
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

CO_AUTHOR = "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
# Keep the transient clone inside the workspace rather than the system /tmp.
WORKSPACE = Path.home() / "git-workspace/claude-workspace"


def main():
    parser = argparse.ArgumentParser(description="Publish Markdown pages to a GitHub repo wiki")
    parser.add_argument("--repo", required=True, help="Target repo as OWNER/REPO")
    parser.add_argument("--pages-dir", required=True, help="Local directory of .md pages to publish")
    parser.add_argument("--message", required=True, help="Commit message")
    args = parser.parse_args()

    pages_dir = Path(args.pages_dir).resolve()
    if not pages_dir.is_dir():
        print(f"ERROR: --pages-dir not found: {pages_dir}")
        sys.exit(1)
    md_files = sorted(pages_dir.glob("*.md"))
    if not md_files:
        print(f"ERROR: no .md pages in {pages_dir}")
        sys.exit(1)

    wiki_url = f"https://github.com/{args.repo}.wiki.git"

    with tempfile.TemporaryDirectory(dir=WORKSPACE, prefix=".git-wiki-") as tmp:
        clone_path = Path(tmp) / "wiki"
        try:
            repo = Repo.clone_from(wiki_url, clone_path)
        except GitCommandError as e:
            print(f"ERROR: could not clone {wiki_url}")
            print("  If this says 'Repository not found', the wiki has no pages yet.")
            print("  Create the first page once via the repo's Wiki tab in the GitHub UI, then re-run.")
            print(f"  {e}")
            sys.exit(1)

        for f in md_files:
            shutil.copy2(f, clone_path / f.name)

        repo.git.add(A=True)
        try:
            staged = repo.index.diff(repo.head.commit)
        except ValueError:  # no commits yet (shouldn't happen on an initialized wiki)
            staged = repo.index.entries
        if not staged:
            print("  wiki: nothing to publish — pages already up to date")
            return

        repo.index.commit(f"{args.message}\n\n{CO_AUTHOR}")
        for info in repo.remotes.origin.push("master"):
            if info.flags & info.ERROR:
                print(f"ERROR: push to wiki master failed: {info.summary.strip()}")
                sys.exit(1)
        print(f"  wiki: published {len(md_files)} page(s) to https://github.com/{args.repo}/wiki")


if __name__ == "__main__":
    main()
