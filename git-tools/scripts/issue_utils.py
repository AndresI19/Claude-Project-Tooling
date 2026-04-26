#!/usr/bin/env python3
"""
issue_utils.py — Shared GitHub issue and project board helpers.

Used as a library by git-plan.py and project_items.py, and as a CLI by the /todo skill.

CLI usage:
    python3 issue_utils.py --repo OWNER/REPO --title "..." --body "..." --label Code --label Inquiry

Library usage:
    from issue_utils import (
        get_or_create_issue, append_blocked_by,
        get_project_node_id, set_item_status,
        query_project, items_by_status, set_item_status_by_name,
    )
"""

import argparse
import os
import sys

# Allow importing github_client from the same directory regardless of cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github_client  # noqa: E402


# ── Standard label vocabulary ─────────────────────────────────────────────────
# Authoritative list shared across git-plan, /todo, and init_labels.

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


# ── Issue helpers ─────────────────────────────────────────────────────────────

def get_or_create_issue(repo, title, body, labels, existing=None):
    """Return (number, url, node_id, created).

    If existing dict is provided, skips creation when title is already present
    and updates the dict on creation. Pass existing=None to always create.
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


# ── Project board helpers ─────────────────────────────────────────────────────

def get_project_node_id(owner, project_number):
    """Resolve a project number to its GraphQL node ID (PVT_...)."""
    query = """
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) { id }
  }
}"""
    data = github_client.graphql(query, {"login": owner, "number": project_number})
    return data["data"]["user"]["projectV2"]["id"]


def set_item_status(project_id, item_id, field_id, option_id):
    """Set a project item's Status field given pre-resolved GraphQL IDs."""
    mutation = """
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: { singleSelectOptionId: $optionId }
  }) {
    projectV2Item { id }
  }
}"""
    github_client.graphql(mutation, {
        "projectId": project_id,
        "itemId":    item_id,
        "fieldId":   field_id,
        "optionId":  option_id,
    })


def query_project(owner, project_number):
    """Return raw project data: id, status field options, and all items with issue details."""
    query = """
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) {
      id
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id name
            options { id name }
          }
        }
      }
      items(first: 100) {
        nodes {
          id
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2SingleSelectField { name } }
              }
            }
          }
          content {
            ... on Issue {
              number title state url
              labels(first: 10) { nodes { name } }
            }
          }
        }
      }
    }
  }
}"""
    data = github_client.graphql(query, {"login": owner, "number": project_number})
    return data["data"]["user"]["projectV2"]


def items_by_status(project_data, status_filter=None):
    """Return list of item dicts from project_data, optionally filtered by status name."""
    results = []
    for item in project_data["items"]["nodes"]:
        content = item.get("content") or {}
        if not content:
            continue
        current_status = next(
            (fv["name"] for fv in item["fieldValues"]["nodes"]
             if fv.get("field", {}).get("name") == "Status"),
            None
        )
        if status_filter and current_status != status_filter:
            continue
        results.append({
            "item_id": item["id"],
            "number":  content.get("number"),
            "title":   content.get("title", ""),
            "state":   content.get("state", ""),
            "url":     content.get("url", ""),
            "labels":  [l["name"] for l in content.get("labels", {}).get("nodes", [])],
            "status":  current_status,
        })
    return results


def set_item_status_by_name(project_data, item_id, target_status):
    """Set a project item's Status field by status name, resolving IDs from project_data."""
    status_field = next(
        (n for n in project_data["fields"]["nodes"] if n.get("name") == "Status"), None
    )
    if not status_field:
        print("ERROR: Status field not found.")
        sys.exit(1)
    option = next((o for o in status_field["options"] if o["name"] == target_status), None)
    if not option:
        valid = [o["name"] for o in status_field["options"]]
        print(f"ERROR: unknown status '{target_status}'. Valid: {', '.join(valid)}")
        sys.exit(1)
    set_item_status(project_data["id"], item_id, status_field["id"], option["id"])


# ── Active-project helpers ────────────────────────────────────────────────────

def find_active_project(owner):
    """Return the first project that has open issues, or None if all are clear."""
    query = """
query($login: String!, $first: Int!) {
  user(login: $login) {
    projectsV2(first: $first) {
      nodes {
        number title url
        items(first: 100) {
          nodes {
            content { ... on Issue { state } }
          }
        }
      }
    }
  }
}"""
    data = github_client.graphql(query, {"login": owner, "first": 20})
    for project in data["data"]["user"]["projectsV2"]["nodes"]:
        has_open = any(
            (item.get("content") or {}).get("state", "").upper() == "OPEN"
            for item in project["items"]["nodes"]
        )
        if has_open:
            return project
    return None


def advance_ready(project_data, repo):
    """Promote Todo/Backlog items to Ready when all their listed blockers are closed.

    Reads '## Blocked By' sections from issue bodies. Skips Epics.
    Returns a list of (number, title) tuples for items that were promoted.
    """
    import re
    candidates = [
        item for item in items_by_status(project_data, None)
        if item["status"] in ("Todo", "Backlog")
        and item["state"] == "OPEN"
        and "Epic" not in item["labels"]
    ]
    promoted = []
    for item in candidates:
        issue = github_client.rest("GET", f"/repos/{repo}/issues/{item['number']}")
        body = issue.get("body") or ""
        if "## Blocked By" in body:
            section = body.split("## Blocked By", 1)[1]
            section = re.split(r"\n##", section)[0]
            blocker_nums = [int(m) for m in re.findall(r"#(\d+)", section)]
        else:
            blocker_nums = []
        if blocker_nums:
            states = [
                github_client.rest("GET", f"/repos/{repo}/issues/{n}").get("state", "").lower()
                for n in blocker_nums
            ]
            if not all(s == "closed" for s in states):
                continue
        set_item_status_by_name(project_data, item["item_id"], "Ready")
        promoted.append((item["number"], item["title"]))
    return promoted


# ── CLI entry point (used by /todo) ──────────────────────────────────────────

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
