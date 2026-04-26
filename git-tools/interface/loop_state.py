#!/usr/bin/env python3
"""Return project loop state JSON: per-status counts and next_action signal."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_state import loop_state

print(json.dumps(loop_state(), indent=2))
