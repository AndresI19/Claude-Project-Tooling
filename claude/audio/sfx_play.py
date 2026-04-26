#!/usr/bin/env python3
"""
sfx_play.py — Play a named SFX file from the shared sfx directory.

Usage:
    python3 sfx_play.py user-select
    python3 sfx_play.py task-complete
    python3 sfx_play.py error-soft

The .wav extension is optional. Plays immediately in the background via
a detached subprocess (setsid) so the caller is not blocked.
"""

import os
import subprocess
import sys
from pathlib import Path

SFX_DIR = Path(__file__).parent.parent.parent / "resources/audio/sfx"


def main():
    if len(sys.argv) < 2:
        print("Usage: sfx_play.py <sound-name>", file=sys.stderr)
        sys.exit(1)

    name = sys.argv[1]
    if not name.endswith(".wav"):
        name += ".wav"

    sfx = SFX_DIR / name
    if not sfx.exists():
        available = [p.stem for p in SFX_DIR.glob("*.wav")]
        print(f"Sound '{name}' not found. Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    subprocess.Popen(
        ["aplay", "-q", str(sfx)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )


if __name__ == "__main__":
    main()
