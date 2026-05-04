"""Tests for projects.py — multi-project enumeration."""
from unittest.mock import patch

from projects import list_all_projects, find_oldest_active


def _project_node(number, title, created_at, *, closed=False, item_states=None, statuses=None):
    """Build a minimal projectsV2 node for tests.

    item_states: list of issue states ("OPEN" | "CLOSED") — one per item.
    statuses: list of Status field values, one per item (parallel to item_states).
    """
    item_states = item_states or []
    statuses = statuses or [None] * len(item_states)
    items = []
    for state, status in zip(item_states, statuses):
        items.append({
            "content": {"state": state} if state else None,
            "fieldValues": {
                "nodes": [{"name": status, "field": {"name": "Status"}}] if status else []
            },
        })
    return {
        "id":        f"PVT_{number}",
        "number":    number,
        "title":     title,
        "url":       f"https://github.com/users/test/projects/{number}",
        "createdAt": created_at,
        "closed":    closed,
        "items":     {"nodes": items},
    }


def _graphql_response(nodes):
    return {"data": {"user": {"projectsV2": {"nodes": nodes}}}}


# ── list_all_projects ──────────────────────────────────────────────────────────

class TestListAllProjects:
    @patch("projects.github_client.graphql")
    def test_returns_each_project_with_status_counts(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([
            _project_node(
                1, "Alpha", "2026-01-01T00:00:00Z",
                item_states=["OPEN", "OPEN", "CLOSED"],
                statuses=["Ready", "Ready", "Done"],
            ),
            _project_node(2, "Beta", "2026-02-01T00:00:00Z", item_states=[], statuses=[]),
        ])
        result = list_all_projects("test-owner")
        assert len(result) == 2
        assert result[0]["title"] == "Alpha"
        assert result[0]["status_counts"] == {"Ready": 2, "Done": 1}
        assert result[0]["has_open_items"] is True
        assert result[1]["status_counts"] == {}
        assert result[1]["has_open_items"] is False

    @patch("projects.github_client.graphql")
    def test_empty_owner_yields_empty_list(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([])
        assert list_all_projects("test-owner") == []

    @patch("projects.github_client.graphql")
    def test_closed_projects_included_but_flagged(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([
            _project_node(1, "Old", "2025-01-01T00:00:00Z", closed=True,
                          item_states=["OPEN"], statuses=["Ready"]),
        ])
        result = list_all_projects("test-owner")
        assert result[0]["closed"] is True


# ── find_oldest_active ─────────────────────────────────────────────────────────

class TestFindOldestActive:
    @patch("projects.github_client.graphql")
    def test_picks_oldest_with_open_items(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([
            _project_node(2, "Younger", "2026-03-01T00:00:00Z",
                          item_states=["OPEN"], statuses=["Ready"]),
            _project_node(1, "Older",   "2026-01-01T00:00:00Z",
                          item_states=["OPEN"], statuses=["Todo"]),
            _project_node(3, "Newest",  "2026-04-01T00:00:00Z",
                          item_states=["OPEN"], statuses=["Backlog"]),
        ])
        result = find_oldest_active("test-owner")
        assert result["number"] == 1
        assert result["title"]  == "Older"

    @patch("projects.github_client.graphql")
    def test_skips_projects_without_open_items(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([
            _project_node(1, "Done-Only", "2026-01-01T00:00:00Z",
                          item_states=["CLOSED"], statuses=["Done"]),
            _project_node(2, "Has-Open",  "2026-02-01T00:00:00Z",
                          item_states=["OPEN"], statuses=["Ready"]),
        ])
        # Project 1 is older but has no open items — project 2 wins.
        result = find_oldest_active("test-owner")
        assert result["number"] == 2

    @patch("projects.github_client.graphql")
    def test_skips_closed_projects(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([
            _project_node(1, "Archived", "2026-01-01T00:00:00Z",
                          closed=True, item_states=["OPEN"], statuses=["Ready"]),
            _project_node(2, "Active",   "2026-02-01T00:00:00Z",
                          item_states=["OPEN"], statuses=["Ready"]),
        ])
        result = find_oldest_active("test-owner")
        assert result["number"] == 2

    @patch("projects.github_client.graphql")
    def test_returns_none_when_no_qualifying_projects(self, mock_graphql):
        mock_graphql.return_value = _graphql_response([
            _project_node(1, "Closed",  "2026-01-01T00:00:00Z",
                          closed=True, item_states=["OPEN"], statuses=["Ready"]),
            _project_node(2, "Empty",   "2026-02-01T00:00:00Z",
                          item_states=[], statuses=[]),
        ])
        assert find_oldest_active("test-owner") is None
