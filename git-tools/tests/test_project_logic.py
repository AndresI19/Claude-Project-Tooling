"""Tests for project domain logic: items_by_status, set_item_status_by_name,
loop_state (next_action branching), and wrap_labels layout."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from conftest import make_item, make_project_data
from project import items_by_status, set_item_status_by_name
from project_state import loop_state
from list_prs import wrap_labels


# ── items_by_status ────────────────────────────────────────────────────────────

class TestItemsByStatus:
    def test_filters_to_matching_status(self):
        data = make_project_data([
            make_item(1, "Task A", "Ready"),
            make_item(2, "Task B", "Todo"),
            make_item(3, "Task C", "Ready"),
        ])
        result = items_by_status(data, "Ready")
        assert len(result) == 2
        assert all(i["status"] == "Ready" for i in result)

    def test_none_filter_returns_all(self):
        data = make_project_data([
            make_item(1, "A", "Ready"),
            make_item(2, "B", "Todo"),
            make_item(3, "C", "In Progress"),
        ])
        assert len(items_by_status(data, None)) == 3

    def test_empty_project_returns_empty(self):
        assert items_by_status(make_project_data([]), "Ready") == []

    def test_nonexistent_status_returns_empty(self):
        data = make_project_data([make_item(1, "Task", "Ready")])
        assert items_by_status(data, "Nonexistent") == []

    def test_skips_items_without_content(self):
        no_content = {
            "id": "PVTI_x",
            "fieldValues": {"nodes": []},
            "content": None,
        }
        data = make_project_data([no_content, make_item(1, "Real", "Ready")])
        result = items_by_status(data, "Ready")
        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_extracts_labels(self):
        data = make_project_data([
            make_item(1, "Task", "Ready", labels=["Code", "Service: MCP"])
        ])
        result = items_by_status(data, "Ready")
        assert result[0]["labels"] == ["Code", "Service: MCP"]

    def test_result_fields_present(self):
        data = make_project_data([make_item(5, "My Task", "Todo")])
        result = items_by_status(data, "Todo")
        item = result[0]
        assert item["item_id"] == "PVTI_5"
        assert item["number"] == 5
        assert item["title"] == "My Task"
        assert item["status"] == "Todo"
        assert item["state"] == "OPEN"
        assert "url" in item

    def test_item_with_no_status_fieldvalue_has_none_status(self):
        item = {
            "id": "PVTI_99",
            "fieldValues": {"nodes": []},  # no Status field value
            "content": {
                "number": 99, "title": "Statusless", "state": "OPEN",
                "url": "", "labels": {"nodes": []},
            },
        }
        data = make_project_data([item])
        result = items_by_status(data, None)
        assert result[0]["status"] is None


# ── set_item_status_by_name ────────────────────────────────────────────────────

class TestSetItemStatusByName:
    def test_unknown_status_exits(self):
        data = make_project_data([])
        with pytest.raises(SystemExit):
            set_item_status_by_name(data, "PVTI_1", "InvalidStatus")

    def test_missing_status_field_exits(self):
        data = {
            "id": "PVT_test",
            "fields": {"nodes": []},  # no Status field at all
            "items": {"nodes": []},
        }
        with pytest.raises(SystemExit):
            set_item_status_by_name(data, "PVTI_1", "Ready")

    @patch("project.set_item_status")
    def test_valid_status_calls_set_item_status(self, mock_set):
        data = make_project_data([])
        set_item_status_by_name(data, "PVTI_1", "Ready")
        mock_set.assert_called_once_with("PVT_test", "PVTI_1", "field_status", "opt_ready")

    @patch("project.set_item_status")
    def test_correct_option_id_resolved(self, mock_set):
        data = make_project_data([])
        set_item_status_by_name(data, "PVTI_1", "Todo")
        _, _, _, option_id = mock_set.call_args[0]
        assert option_id == "opt_todo"


# ── loop_state / next_action ───────────────────────────────────────────────────

class TestLoopStateNextAction:
    """loop_state returns a dict with per-status counts and a next_action signal.
    query_project and items_by_status are mocked so we only test the branching logic.
    """

    def _mock_ibs(self, counts_by_status):
        """Return a side_effect that maps status name → list of N fake items."""
        def side_effect(data, status):
            return [None] * counts_by_status.get(status, 0)
        return side_effect

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_ready_items_gives_continue(self, mock_qp, mock_ibs):
        mock_qp.return_value = {}
        mock_ibs.side_effect = self._mock_ibs({"Ready": 2})
        assert loop_state()["next_action"] == "continue"

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_in_progress_items_gives_continue(self, mock_qp, mock_ibs):
        mock_qp.return_value = {}
        mock_ibs.side_effect = self._mock_ibs({"In Progress": 1})
        assert loop_state()["next_action"] == "continue"

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_only_todo_gives_blocked(self, mock_qp, mock_ibs):
        mock_qp.return_value = {}
        mock_ibs.side_effect = self._mock_ibs({"Todo": 3})
        assert loop_state()["next_action"] == "blocked"

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_only_backlog_gives_blocked(self, mock_qp, mock_ibs):
        mock_qp.return_value = {}
        mock_ibs.side_effect = self._mock_ibs({"Backlog": 1})
        assert loop_state()["next_action"] == "blocked"

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_all_empty_gives_plan(self, mock_qp, mock_ibs):
        mock_qp.return_value = {}
        mock_ibs.return_value = []
        assert loop_state()["next_action"] == "plan"

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_ready_takes_priority_over_todo(self, mock_qp, mock_ibs):
        # If both Ready and Todo exist, next_action is "continue" not "blocked"
        mock_qp.return_value = {}
        mock_ibs.side_effect = self._mock_ibs({"Ready": 1, "Todo": 5})
        assert loop_state()["next_action"] == "continue"

    @patch("project_state.items_by_status")
    @patch("project_state.query_project")
    def test_counts_are_accurate(self, mock_qp, mock_ibs):
        mock_qp.return_value = {}
        mock_ibs.side_effect = self._mock_ibs({"Ready": 2, "Todo": 3, "Backlog": 1})
        result = loop_state()
        assert result["ready"] == 2
        assert result["todo"] == 3
        assert result["backlog"] == 1
        assert result["in_progress"] == 0
        assert result["verify"] == 0


# ── wrap_labels ────────────────────────────────────────────────────────────────

class TestWrapLabels:
    """wrap_labels distributes label names into lines that fit within LABEL_WIDTH (28)."""

    def test_empty_list_returns_sentinel(self):
        assert wrap_labels([]) == [[]]

    def test_single_label(self):
        assert wrap_labels(["Code"]) == [["Code"]]

    def test_two_short_labels_fit_one_line(self):
        # "Hi"(4) + gap(1) + "Ok"(4) = 9 < 28
        assert wrap_labels(["Hi", "Ok"]) == [["Hi", "Ok"]]

    def test_labels_wrap_when_combined_exceeds_width(self):
        # "Enhancement"(13) + gap(1) + "Documentation"(15) = 29 > 28
        result = wrap_labels(["Enhancement", "Documentation"])
        assert result == [["Enhancement"], ["Documentation"]]

    def test_label_that_exactly_fills_width_does_not_wrap(self):
        # badge_w = 26+2 = 28, fits exactly
        label = "A" * 26
        assert wrap_labels([label]) == [[label]]

    def test_three_labels_split_across_lines(self):
        # "Enhancement"(13) + "Fix"(5) = 13+1+5=19, fits; then "Documentation"(15): 19+1+15=35 > 28
        result = wrap_labels(["Enhancement", "Fix", "Documentation"])
        assert result[0] == ["Enhancement", "Fix"]
        assert result[1] == ["Documentation"]

    def test_single_label_preserves_name(self):
        assert wrap_labels(["Service: MCP"]) == [["Service: MCP"]]
