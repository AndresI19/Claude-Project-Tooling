#!/usr/bin/env python3
"""
projects.py — Multi-project enumeration for /git-plan and /triage.

Provides:
- list_all_projects(owner)  → every projectsV2 with status_counts
- find_oldest_active(owner) → oldest project (by createdAt) that has open items

Single GraphQL query per call; status counts come from the returned items.
"""
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
import github_client


_LIST_QUERY = """
query($login: String!) {
  user(login: $login) {
    projectsV2(first: 50) {
      nodes {
        id number title url createdAt closed
        items(first: 100) {
          nodes {
            content { ... on Issue { state } }
            fieldValues(first: 5) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field { ... on ProjectV2SingleSelectField { name } }
                }
              }
            }
          }
        }
      }
    }
  }
}"""


def _status_counts(project_node):
    """Tally Status field values across all items in a project node."""
    counts = {}
    for item in project_node.get("items", {}).get("nodes", []):
        for fv in item.get("fieldValues", {}).get("nodes", []):
            if fv.get("field", {}).get("name") == "Status" and fv.get("name"):
                counts[fv["name"]] = counts.get(fv["name"], 0) + 1
                break
    return counts


def _has_open_items(project_node):
    return any(
        (item.get("content") or {}).get("state", "").upper() == "OPEN"
        for item in project_node.get("items", {}).get("nodes", [])
    )


def list_all_projects(owner):
    """Return every projectsV2 for the owner.

    Each entry: {id, number, title, url, createdAt, closed, status_counts,
                 has_open_items}.
    Closed projects are included; the caller decides whether to filter.
    """
    data = github_client.graphql(_LIST_QUERY, {"login": owner})
    nodes = data["data"]["user"]["projectsV2"]["nodes"]
    return [
        {
            "id":               p["id"],
            "number":           p["number"],
            "title":            p["title"],
            "url":              p["url"],
            "createdAt":        p["createdAt"],
            "closed":           p.get("closed", False),
            "status_counts":    _status_counts(p),
            "has_open_items":   _has_open_items(p),
        }
        for p in nodes
    ]


def find_oldest_active(owner):
    """Return the oldest (by createdAt) non-closed project with at least one open item.

    Returns None if no project qualifies.
    """
    candidates = [
        p for p in list_all_projects(owner)
        if not p["closed"] and p["has_open_items"]
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p["createdAt"])
    return candidates[0]
