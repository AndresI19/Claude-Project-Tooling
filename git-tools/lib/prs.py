#!/usr/bin/env python3
"""
prs.py — Pull request data fetching via GitHub REST API.

Replaces the subprocess gh-cli calls previously used in scripts/list_prs.py.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github_client

WORKSPACE = Path.home() / "git-workspace/claude-workspace"


def find_workspace_repos():
    """Return sorted list of git repo paths under WORKSPACE."""
    return sorted(
        [d for d in WORKSPACE.iterdir() if d.is_dir() and (d / ".git").exists()],
        key=lambda d: d.name,
    )


def get_repo_full_name(repo_path):
    """Return 'owner/repo' parsed from the origin remote URL, or None."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True, cwd=repo_path,
    )
    if result.returncode != 0:
        return None
    url = result.stdout.strip()
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def fetch_prs_for_repo(gh_repo):
    """Fetch open PRs for OWNER/REPO via REST. Returns list of normalized dicts."""
    prs = github_client.rest("GET", f"/repos/{gh_repo}/pulls",
                              params={"state": "open", "per_page": 100})
    return [
        {
            "number":  pr["number"],
            "title":   pr["title"],
            "labels":  [l["name"] for l in pr.get("labels", [])],
            "updated": pr["updated_at"][:10],
        }
        for pr in prs
    ]


def collect_all_prs():
    """Fetch open PRs across all workspace repos. Returns list of {repo, gh_repo, prs} dicts."""
    results = []
    for repo_path in find_workspace_repos():
        gh_repo = get_repo_full_name(repo_path)
        if not gh_repo:
            continue
        prs = fetch_prs_for_repo(gh_repo)
        if not prs:
            continue
        prs.sort(key=lambda p: p["updated"], reverse=True)
        results.append({"repo": repo_path.name, "gh_repo": gh_repo, "prs": prs})
    return results
