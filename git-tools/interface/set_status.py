#!/usr/bin/env python3
"""Move a project item to a new status.
Usage: set_status.py ITEM_ID STATUS
"""
import sys
from pathlib import Path

if len(sys.argv) < 3:
    print("Usage: set_status.py ITEM_ID STATUS", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_items import update_status

update_status(item_id=sys.argv[1], target=sys.argv[2])
