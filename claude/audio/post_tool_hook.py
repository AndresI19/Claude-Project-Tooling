#!/usr/bin/env python3
"""
post_tool_hook.py — PostToolUse hook: plays SFX based on tool outcome.

Triggered by Claude Code after every tool call. Reads the JSON payload from stdin.

Sounds:
  user-select.wav  — Bash call containing project_items.py --set-status (user picked from list)
  error-soft.wav   — Any tool returned a non-zero exit code (Claude can recover)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SFX_DIR = Path(__file__).parent.parent.parent / "resources/audio/sfx"


def play(name):
    subprocess.Popen(
        ["aplay", "-q", str(SFX_DIR / name)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    tool_name     = payload.get("tool_name", "")
    tool_input    = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response", "")
    response_str  = tool_response if isinstance(tool_response, str) else json.dumps(tool_response)

    # User selected from list via /new-task or similar skill
    if tool_name == "Bash":
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        if "project_items.py" in command and "--set-status" in command:
            play("user-select.wav")
            return

    # Recoverable tool error — non-zero exit code
    codes = re.findall(r"[Ee]xit code[:\s]+(\d+)", response_str)
    if any(int(c) != 0 for c in codes):
        play("error-soft.wav")


if __name__ == "__main__":
    main()
