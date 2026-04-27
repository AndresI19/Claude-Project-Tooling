"""Shared test configuration — adds lib/ and scripts/ to sys.path."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
# lib/ must precede scripts/ so lib/github_client.py wins over the thin CLI wrapper in scripts/
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lib"))


# ── Shared project-data fixtures ──────────────────────────────────────────────

def make_item(number, title, status, state="OPEN", labels=None):
    """Build a minimal project item dict matching the GitHub GraphQL shape."""
    return {
        "id": f"PVTI_{number}",
        "fieldValues": {
            "nodes": [{"name": status, "field": {"name": "Status"}}]
        },
        "content": {
            "number": number,
            "title":  title,
            "state":  state,
            "url":    f"https://github.com/test/repo/issues/{number}",
            "labels": {"nodes": [{"name": l} for l in (labels or [])]},
        },
    }


def make_project_data(items, status_options=None):
    """Build a minimal project_data dict for testing."""
    if status_options is None:
        status_options = [
            {"id": "opt_todo",    "name": "Todo"},
            {"id": "opt_ready",   "name": "Ready"},
            {"id": "opt_backlog", "name": "Backlog"},
            {"id": "opt_inprog",  "name": "In Progress"},
            {"id": "opt_verify",  "name": "Verify"},
        ]
    return {
        "id": "PVT_test",
        "fields": {
            "nodes": [
                {"id": "field_status", "name": "Status", "options": status_options}
            ]
        },
        "items": {"nodes": items},
    }
