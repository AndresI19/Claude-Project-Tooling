#!/usr/bin/env python3
"""List project items for a given status as JSON.
Usage: status_items.py STATUS
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: status_items.py STATUS", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_items import list_items

list_items(status=sys.argv[1], json_output=True)
