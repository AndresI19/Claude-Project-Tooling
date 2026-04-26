#!/usr/bin/env python3
"""
sfx_task_start.py — Play the task-start sound once per task.

Usage:
    python3 sfx_task_start.py short   # < 5 expected tool calls
    python3 sfx_task_start.py long    # >= 5 expected tool calls

Uses a timestamp file in /tmp to prevent re-triggering within the same task.
If called again within COOLDOWN seconds, the sound is skipped silently.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

SFX_DIR   = Path(__file__).parent.parent.parent / "resources/audio/sfx"
FLAG_FILE = Path("/tmp/claude_sfx_task_start")
COOLDOWN  = 8  # seconds — enough to span rapid parallel tool calls, short enough to catch new tasks


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else "short"
    if kind not in ("short", "long"):
        print(f"Usage: sfx_task_start.py short|long", file=sys.stderr)
        sys.exit(1)

    now = time.time()
    try:
        last = float(FLAG_FILE.read_text())
        if now - last < COOLDOWN:
            return  # still within the same task — skip
    except (FileNotFoundError, ValueError):
        pass

    FLAG_FILE.write_text(str(now))
    sfx = "task-start-long.wav" if kind == "long" else "task-start-short.wav"
    subprocess.Popen(
        ["aplay", "-q", str(SFX_DIR / sfx)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )


if __name__ == "__main__":
    main()
