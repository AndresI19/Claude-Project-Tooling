#!/usr/bin/env python3
"""
Loads a PR by number from any workspace repo.

Searches all repos under ~/git-workspace/claude-workspace/ for the given PR
number, resolves OWNER/REPO, then fetches gh pr view + gh pr diff in parallel.

Usage:
    python3 load_pr.py NUMBER
    python3 load_pr.py REPO_FOLDER/NUMBER   # disambiguate when PR# exists in multiple repos
"""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WORKSPACE = Path.home() / "git-workspace/claude-workspace"

BOLD  = "\033[1m"
RESET = "\033[0m"
RED   = "\033[31m"


def run(args, cwd=None):
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    return result.stdout.strip(), result.returncode == 0


def find_repos():
    return sorted(
        [d for d in WORKSPACE.iterdir() if d.is_dir() and (d / ".git").exists()],
        key=lambda d: d.name,
    )


def resolve_gh_repo(repo_path):
    out, ok = run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        cwd=repo_path,
    )
    return out if ok else None


def pr_exists(gh_repo, number):
    _, ok = run(["gh", "pr", "view", str(number), "--repo", gh_repo])
    return ok


def fetch_view(gh_repo, number):
    out, _ = run(["gh", "pr", "view", str(number), "--repo", gh_repo])
    return out


def fetch_diff(gh_repo, number):
    out, _ = run(["gh", "pr", "diff", str(number), "--repo", gh_repo])
    return out


def main():
    if len(sys.argv) != 2:
        print(f"Usage: load_pr.py NUMBER  |  load_pr.py REPO/NUMBER")
        sys.exit(1)

    arg = sys.argv[1]
    repo_hint = None

    if "/" in arg:
        parts = arg.rsplit("/", 1)
        repo_hint, number_str = parts[0], parts[1]
    else:
        number_str = arg

    try:
        number = int(number_str)
    except ValueError:
        print(f"{RED}ERROR: '{number_str}' is not a valid PR number{RESET}")
        sys.exit(1)

    repos = find_repos()
    if repo_hint:
        repos = [r for r in repos if r.name == repo_hint]
        if not repos:
            print(f"{RED}ERROR: No repo folder named '{repo_hint}' in workspace{RESET}")
            sys.exit(1)

    # Find which repos have this PR number
    matches = []
    for repo_path in repos:
        gh_repo = resolve_gh_repo(repo_path)
        if gh_repo and pr_exists(gh_repo, number):
            matches.append((repo_path, gh_repo))

    if not matches:
        print(f"{RED}ERROR: PR #{number} not found in any workspace repo{RESET}")
        sys.exit(1)

    if len(matches) > 1:
        names = [f"  {r.name}/{number}" for r, _ in matches]
        print(f"{RED}ERROR: PR #{number} exists in multiple repos — specify one:{RESET}")
        print("\n".join(names))
        sys.exit(1)

    repo_path, gh_repo = matches[0]

    print(f"\n{BOLD}Repo:{RESET}  {gh_repo}  (PR #{number})\n")

    with ThreadPoolExecutor(max_workers=2) as ex:
        view_f = ex.submit(fetch_view, gh_repo, number)
        diff_f = ex.submit(fetch_diff, gh_repo, number)
        view = view_f.result()
        diff = diff_f.result()

    print(f"{BOLD}{'─' * 72}{RESET}")
    print(f"{BOLD}PR VIEW{RESET}")
    print(f"{BOLD}{'─' * 72}{RESET}")
    print(view)

    print(f"\n{BOLD}{'─' * 72}{RESET}")
    print(f"{BOLD}DIFF{RESET}")
    print(f"{BOLD}{'─' * 72}{RESET}")
    print(diff)


if __name__ == "__main__":
    main()
