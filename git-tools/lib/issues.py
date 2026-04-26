#!/usr/bin/env python3
"""
issues.py — GitHub issue CRUD helpers and label vocabulary.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github_client


ISSUE_LABELS = [
    {"name": "Epic",         "description": "Tracks a broader goal composed of multiple tasks"},
    {"name": "Code",         "description": "Coding required to build a new feature"},
    {"name": "Defect",       "description": "A discovered error or broken behavior"},
    {"name": "Discovery",    "description": "Investigation or research needed"},
    {"name": "Inquiry",      "description": "Open question requiring a design decision"},
    {"name": "DevOps",       "description": "Infrastructure, deployment, or automation work"},
    {"name": "Service: MCP", "description": "Changes to the MCP server service"},
]

ISSUE_LABEL_NAMES = [l["name"] for l in ISSUE_LABELS]


def get_or_create_issue(repo, title, body, labels, existing=None):
    """Return (number, url, node_id, created).

    Pass existing={} to skip re-creation when the title is already present.
    """
    if existing is not None and title in existing:
        entry = existing[title]
        return entry["number"], entry["url"], entry["node_id"], False

    data = github_client.rest("POST", f"/repos/{repo}/issues", json={
        "title":  title,
        "body":   body,
        "labels": labels,
    })
    number  = data["number"]
    url     = data["html_url"]
    node_id = data["node_id"]
    if existing is not None:
        existing[title] = {"number": number, "url": url, "node_id": node_id}
    return number, url, node_id, True


def append_blocked_by(repo, issue_number, current_body, blocker_numbers_titles):
    """Append a '## Blocked By' section to an issue body."""
    lines = "\n".join(f"- #{n} {t}" for n, t in blocker_numbers_titles)
    new_body = (
        current_body.rstrip() + f"\n\n## Blocked By\n{lines}"
        if current_body.strip()
        else f"## Blocked By\n{lines}"
    )
    github_client.rest("PATCH", f"/repos/{repo}/issues/{issue_number}", json={"body": new_body})


def load_existing_issues(repo):
    """Fetch all issues (open + closed) and return title → {number, url, node_id} dict."""
    result = {}
    page   = 1
    while True:
        issues = github_client.rest("GET", f"/repos/{repo}/issues",
                                    params={"state": "all", "per_page": 100, "page": page})
        if not issues:
            break
        for issue in issues:
            if "pull_request" in issue:
                continue
            result[issue["title"]] = {
                "number":  issue["number"],
                "url":     issue["html_url"],
                "node_id": issue["node_id"],
            }
        if len(issues) < 100:
            break
        page += 1
    return result
