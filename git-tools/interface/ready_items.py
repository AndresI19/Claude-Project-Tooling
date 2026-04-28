#!/usr/bin/env python3
"""List project items as JSON — pre-set interface for skill consumption.

Default: Ready items only (backward compatible).
Pass --include-statuses to fetch multiple statuses in display priority order.
Examples:
    ready_items.py
    ready_items.py --include-statuses="Verify,In Progress,Ready"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_items import list_items

parser = argparse.ArgumentParser()
parser.add_argument("--include-statuses", default="Ready",
                    help="Comma-separated statuses in display priority order")
args = parser.parse_args()

statuses = [s.strip() for s in args.include_statuses.split(",")]
list_items(statuses=statuses, json_output=True)
