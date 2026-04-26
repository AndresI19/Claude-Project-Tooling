#!/usr/bin/env python3
"""Close an issue and advance newly unblocked items to Ready.
Usage: close_and_promote.py NUMBER
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: close_and_promote.py NUMBER", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_state import close_and_promote

close_and_promote(issue_number=int(sys.argv[1]))
