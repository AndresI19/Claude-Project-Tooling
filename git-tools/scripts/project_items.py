#!/usr/bin/env python3
"""
project_items.py — Query and update GitHub Project V2 items by status.

Usage:
    python3 project_items.py                          # list Ready items, colored table
    python3 project_items.py --status Todo            # filter by status name
    python3 project_items.py --json                   # JSON output for skill consumption
    python3 project_items.py --set-status ITEM_ID "In Progress"  # move an item

Defaults to AndresI19's project #5. Override with --owner / --project-number.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from issue_utils import query_project, items_by_status, set_item_status_by_name

RESET = "\033[0m"
BOLD  = "\033[1m"
BLUE  = "\033[34m"
GREEN = "\033[32m"
DIM   = "\033[2m"

LABEL_COLORS = {
    "epic":         {"bg": (0,   0,   0),   "fg": (255, 255, 255)},
    "code":         {"bg": (22,  101, 52),  "fg": (255, 255, 255)},
    "defect":       {"bg": (211, 47,  47),  "fg": (255, 255, 255)},
    "discovery":    {"bg": (254, 249, 195), "fg": (0,   0,   0)},
    "inquiry":      {"bg": (254, 249, 195), "fg": (0,   0,   0)},
    "devops":       {"bg": (224, 64,  251), "fg": (255, 255, 255)},
    "service: mcp": {"bg": (224, 64,  251), "fg": (255, 255, 255)},
}


def ansi_bg(r, g, b): return f"\033[48;2;{r};{g};{b}m"
def ansi_fg(r, g, b): return f"\033[38;2;{r};{g};{b}m"


def color_label(name):
    style = LABEL_COLORS.get(name.lower())
    if not style:
        return f" {name} "
    return f"{ansi_bg(*style['bg'])}{ansi_fg(*style['fg'])} {name} {RESET}"


def print_table(items, status_label):
    if not items:
        print(f"No items with status '{status_label}'.")
        return
    print(f"\n{BOLD}{BLUE}  {status_label} ({len(items)}){RESET}\n")
    for i, item in enumerate(items, 1):
        labels_str = " ".join(color_label(l) for l in item["labels"]) if item["labels"] else ""
        num_badge  = f"{DIM}#{item['number']}{RESET}"
        # Column order: index · title · labels · issue number
        print(f"  {BOLD}{i}){RESET}  {item['title']:<50}  {labels_str:<30}  {num_badge}")
    print(f"  {BOLD}0){RESET}  Cancel\n")


def main():
    parser = argparse.ArgumentParser(description="Query and update GitHub Project items")
    parser.add_argument("--owner",          default="AndresI19")
    parser.add_argument("--project-number", type=int, default=5)
    parser.add_argument("--status",         default="Ready",
                        help="Filter items by status name (default: Ready)")
    parser.add_argument("--json",           action="store_true",
                        help="Output JSON instead of colored table")
    parser.add_argument("--set-status",     nargs=2, metavar=("ITEM_ID", "STATUS"),
                        help="Move ITEM_ID to STATUS and exit")
    args = parser.parse_args()

    project_data = query_project(args.owner, args.project_number)

    if args.set_status:
        item_id, target = args.set_status
        set_item_status_by_name(project_data, item_id, target)
        print(f"{GREEN}✓{RESET} Status → {target}")
        return

    items = items_by_status(project_data, args.status)

    if args.json:
        print(json.dumps(items, indent=2))
    else:
        print_table(items, args.status)


if __name__ == "__main__":
    main()
