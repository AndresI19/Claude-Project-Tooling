#!/usr/bin/env python3
"""
issue_utils.py — Shared GitHub issue and project board helpers.

Used as a library by git-plan.py and project_items.py, and as a CLI by the /todo skill.

CLI usage:
    python3 issue_utils.py --repo OWNER/REPO --title "..." --body "..." --label Code --label Inquiry

Library usage:
    from issue_utils import run, run_silent, get_or_create_issue, issue_number_from_url,
                            append_blocked_by, get_project_node_id, set_item_status,
                            query_project, items_by_status, set_item_status_by_name
"""

import argparse
import json
import re
import subprocess
import sys


# ── Standard label vocabulary ─────────────────────────────────────────────────
# Authoritative list shared across git-plan, /todo, and init_labels.
# PR complexity labels are omitted here — those are applied by reviewers, not at issue creation.

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


# ── Shell helpers ─────────────────────────────────────────────────────────────

def run(args, description=None):
    if isinstance(args, str):
        args = ["bash", "-c", args]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        label = description or (" ".join(args) if isinstance(args, list) else args)
        print(f"\nERROR: {label} failed (exit {result.returncode})")
        if result.stdout.strip():
            print(f"  STDOUT: {result.stdout.strip()}")
        if result.stderr.strip():
            print(f"  STDERR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def run_silent(args):
    if isinstance(args, str):
        args = ["bash", "-c", args]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode == 0


# ── Issue helpers ─────────────────────────────────────────────────────────────

def issue_number_from_url(url):
    match = re.search(r"/issues/(\d+)$", url)
    if not match:
        print(f"ERROR: could not parse issue number from: {url}")
        sys.exit(1)
    return int(match.group(1))


def get_or_create_issue(repo, title, body, labels, existing=None):
    """Return (number, url, created).

    If existing dict is provided, skips creation when title is already present
    and updates the dict on creation. Pass existing=None to always create.
    """
    if existing is not None and title in existing:
        entry = existing[title]
        return entry["number"], entry["url"], False

    label_flags = [flag for label in labels for flag in ("--label", label)]
    url = run(["gh", "issue", "create",
               "--repo",  repo,
               "--title", title,
               "--body",  body,
               *label_flags],
              description=f"create issue: {title}")
    number = issue_number_from_url(url)
    if existing is not None:
        existing[title] = {"number": number, "url": url}
    return number, url, True


def append_blocked_by(repo, issue_number, current_body, blocker_numbers_titles):
    """Append a '## Blocked By' section to an issue body."""
    lines = "\n".join(f"- #{n} {t}" for n, t in blocker_numbers_titles)
    new_body = (
        current_body.rstrip() + f"\n\n## Blocked By\n{lines}"
        if current_body.strip()
        else f"## Blocked By\n{lines}"
    )
    run(["gh", "issue", "edit", str(issue_number),
         "--repo", repo, "--body", new_body],
        description=f"add blocked-by to #{issue_number}")


# ── Project board helpers ─────────────────────────────────────────────────────

def get_project_node_id(owner, project_number):
    """Resolve a project number to its GraphQL node ID (PVT_...)."""
    query = """
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) { id }
  }
}"""
    out = run(["gh", "api", "graphql",
               "-f", f"query={query}",
               "-f", f"login={owner}",
               "-F", f"number={project_number}"],
              description="query project node id")
    return json.loads(out)["data"]["user"]["projectV2"]["id"]


def set_item_status(project_id, item_id, field_id, option_id):
    """Set a project item's Status field given pre-resolved GraphQL IDs."""
    mutation = f"""
mutation {{
  updateProjectV2ItemFieldValue(input: {{
    projectId: "{project_id}"
    itemId: "{item_id}"
    fieldId: "{field_id}"
    value: {{ singleSelectOptionId: "{option_id}" }}
  }}) {{
    projectV2Item {{ id }}
  }}
}}"""
    run(["gh", "api", "graphql", "-f", f"query={mutation}"],
        description=f"set status on item {item_id}")


def query_project(owner, project_number):
    """Return raw project data: id, status field options, and all items with issue details."""
    query = f"""
query {{
  user(login: "{owner}") {{
    projectV2(number: {project_number}) {{
      id
      fields(first: 20) {{
        nodes {{
          ... on ProjectV2SingleSelectField {{
            id name
            options {{ id name }}
          }}
        }}
      }}
      items(first: 100) {{
        nodes {{
          id
          fieldValues(first: 20) {{
            nodes {{
              ... on ProjectV2ItemFieldSingleSelectValue {{
                name
                field {{ ... on ProjectV2SingleSelectField {{ name }} }}
              }}
            }}
          }}
          content {{
            ... on Issue {{
              number title state url
              labels(first: 10) {{ nodes {{ name }} }}
            }}
          }}
        }}
      }}
    }}
  }}
}}"""
    out = run(["gh", "api", "graphql", "-f", f"query={query}"],
              description="query project items")
    return json.loads(out)["data"]["user"]["projectV2"]


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


# ── CLI entry point (used by /todo) ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Create a GitHub issue with standard labels"
    )
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

    _, url, _ = get_or_create_issue(args.repo, args.title, args.body, args.labels)
    print(url)


if __name__ == "__main__":
    main()
