#!/usr/bin/env python3
"""
project.py — GitHub Projects V2 domain logic.

Covers: querying project state, status mutations, project creation,
active-project detection, and advance-ready promotion.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github_client


# ── Query helpers ──────────────────────────────────────────────────────────────

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
    """Return list of item dicts, optionally filtered by status name."""
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


# ── Status mutation helpers ────────────────────────────────────────────────────

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


def set_item_status_by_name(project_data, item_id, target_status):
    """Set a project item's Status by name, resolving field/option IDs from project_data."""
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


# ── Project creation helpers ───────────────────────────────────────────────────

def _get_owner_node_id(owner):
    q = """query($login: String!) { user(login: $login) { id } }"""
    return github_client.graphql(q, {"login": owner})["data"]["user"]["id"]


def create_or_find_project(owner, title, repo):
    """Create a GitHub Project V2 linked to repo. Returns (number, url, node_id).

    Checks for an existing project with the same title first to make re-runs safe.
    """
    list_q = """
query($login: String!, $first: Int!) {
  user(login: $login) {
    projectsV2(first: $first) {
      nodes { id number title url }
    }
  }
}"""
    data = github_client.graphql(list_q, {"login": owner, "first": 50})
    for p in data["data"]["user"]["projectsV2"]["nodes"]:
        if p["title"] == title:
            print(f"  (project already exists — reusing #{p['number']})")
            return p["number"], p["url"], p["id"]

    owner_id = _get_owner_node_id(owner)
    create_m = """
mutation($ownerId: ID!, $title: String!) {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 { id number url }
  }
}"""
    project = github_client.graphql(create_m, {"ownerId": owner_id, "title": title})
    project = project["data"]["createProjectV2"]["projectV2"]

    repo_data = github_client.rest("GET", f"/repos/{repo}")
    link_m = """
mutation($projectId: ID!, $repositoryId: ID!) {
  linkProjectV2ToRepository(input: {projectId: $projectId, repositoryId: $repositoryId}) {
    repository { id }
  }
}"""
    github_client.graphql(link_m, {
        "projectId":    project["id"],
        "repositoryId": repo_data["node_id"],
    })
    return project["number"], project["url"], project["id"]


EXTRA_STATUSES = [
    {"name": "Backlog", "color": "GRAY",   "description": "Work that can be done but carries the least priority"},
    {"name": "Verify",  "color": "ORANGE", "description": "Code is delivered but requires validation to close"},
    {"name": "Ready",   "color": "BLUE",   "description": "Work that is not pending other tasks to be started"},
]


def configure_project_statuses(project_number, owner):
    """Add Backlog, Verify, and Ready to the project's Status field.

    Returns (field_id, {name: option_id}) or (None, {}) if Status field is missing.
    """
    query = """
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) {
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id name
            options { id name color description }
          }
        }
      }
    }
  }
}"""
    data  = github_client.graphql(query, {"login": owner, "number": project_number})
    nodes = data["data"]["user"]["projectV2"]["fields"]["nodes"]
    status = next((n for n in nodes if n.get("name") == "Status"), None)
    if not status:
        print("  WARNING: Status field not found — skipping")
        return None, {}

    field_id       = status["id"]
    existing_names = {o["name"] for o in status["options"]}
    to_add         = [s for s in EXTRA_STATUSES if s["name"] not in existing_names]

    if not to_add:
        print("  (status options already configured)")
        return field_id, {o["name"]: o["id"] for o in status["options"]}

    all_options = [
        {"name": o["name"], "color": o["color"], "description": o.get("description", "")}
        for o in status["options"]
    ] + to_add

    mutation = """
mutation($fieldId: ID!, $options: [ProjectV2SingleSelectFieldOptionInput!]!) {
  updateProjectV2Field(input: {
    fieldId: $fieldId
    singleSelectOptions: $options
  }) {
    projectV2Field {
      ... on ProjectV2SingleSelectField {
        id
        options { id name }
      }
    }
  }
}"""
    mut_data = github_client.graphql(mutation, {"fieldId": field_id, "options": all_options})
    print(f"  Added: {', '.join(s['name'] for s in to_add)}")
    updated_opts = mut_data["data"]["updateProjectV2Field"]["projectV2Field"]["options"]
    return field_id, {o["name"]: o["id"] for o in updated_opts}


def add_item_to_project(project_id, content_node_id):
    """Add an issue to a project V2. Idempotent — returns item ID."""
    mutation = """
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}"""
    data = github_client.graphql(mutation, {
        "projectId": project_id,
        "contentId": content_node_id,
    })
    return data["data"]["addProjectV2ItemById"]["item"]["id"]


# ── Active-project detection + advance-ready ──────────────────────────────────

def find_active_project(owner):
    """Return the first project with open issues, or None if all are clear."""
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
    Returns list of (number, title) tuples for promoted items.
    """
    candidates = [
        item for item in items_by_status(project_data, None)
        if item["status"] in ("Todo", "Backlog")
        and item["state"] == "OPEN"
        and "Epic" not in item["labels"]
    ]
    promoted = []
    for item in candidates:
        issue = github_client.rest("GET", f"/repos/{repo}/issues/{item['number']}")
        body  = issue.get("body") or ""
        if "## Blocked By" in body:
            section      = body.split("## Blocked By", 1)[1]
            section      = re.split(r"\n##", section)[0]
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
