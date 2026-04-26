#!/usr/bin/env python3
"""
Detects the current session log state for the record skill.

Usage:
    python3 session_detect.py          # normal mode
    python3 session_detect.py auto     # auto mode (Stop hook) — always returns action=new

Outputs JSON:
    {"action": "append"|"new"|"ask", "file": "/path/to/latest.md", "latest_date": "YYYY-MM-DD", "today": "YYYY-MM-DD"}

Actions:
    new    — create a fresh log (auto mode, or no existing logs)
    append — add to today's existing log
    ask    — latest log is from a prior day; Claude should prompt the user to choose
"""

import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = (
    Path.home() / "git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions"
)


def main():
    auto = len(sys.argv) > 1 and sys.argv[1] == "auto"
    today = datetime.now().strftime("%Y-%m-%d")

    logs = sorted(
        [f for f in glob.glob(str(SESSIONS_DIR / "*.md")) if "Usage" not in f],
        key=os.path.getmtime,
        reverse=True,
    )

    if not logs:
        print(json.dumps({"action": "new", "file": None, "latest_date": None, "today": today}))
        return

    latest = logs[0]
    latest_date = Path(latest).name[:10]  # YYYY-MM-DD prefix

    if auto:
        action = "new"
    elif latest_date == today:
        action = "append"
    else:
        action = "ask"

    print(json.dumps({
        "action": action,
        "file": latest,
        "latest_date": latest_date,
        "today": today,
    }))


if __name__ == "__main__":
    main()
