#!/usr/bin/env python3
"""
project_items.py — List and update GitHub Project V2 items by status.

Usage:
    python3 project_items.py                         # list Ready items, colored table
    python3 project_items.py --status Todo           # filter by status
    python3 project_items.py --json                  # JSON output
    python3 project_items.py --set-status ID STATUS  # move an item
"""
import argparse
import json
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, LIB)
from github_client import load_config
from project import query_project, items_by_status, set_item_status_by_name
from display import ansi_bg, ansi_fg, ljust_visible, color_label

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

_cfg = load_config()
_OWNER          = _cfg["owner"]
_PROJECT_NUMBER = _cfg["project_number"]


def print_table(items, status_label):
    if not items:
        print(f"No items with status '{status_label}'.")
        return
    print(f"\n{BOLD}{BLUE}  {status_label} ({len(items)}){RESET}\n")
    for i, item in enumerate(items, 1):
        labels_str = " ".join(color_label(l, LABEL_COLORS) for l in item["labels"]) if item["labels"] else ""
        num_badge  = f"{DIM}#{item['number']}{RESET}"
        print(f"  {BOLD}{i}){RESET}  {item['title']:<50}  {ljust_visible(labels_str, 30)}  {num_badge}")
    print(f"  {BOLD}0){RESET}  Cancel\n")


def list_items(status="Ready", json_output=False,
               owner=_OWNER, project_number=_PROJECT_NUMBER):
    """List project items for a given status. Prints table or JSON."""
    project_data = query_project(owner, project_number)
    items = items_by_status(project_data, status)
    if json_output:
        print(json.dumps(items, indent=2))
    else:
        print_table(items, status)


def update_status(item_id, target,
                  owner=_OWNER, project_number=_PROJECT_NUMBER):
    """Move a project item to a new status by name."""
    project_data = query_project(owner, project_number)
    set_item_status_by_name(project_data, item_id, target)
    print(f"{GREEN}✓{RESET} Status → {target}")


def main():
    parser = argparse.ArgumentParser(description="Query and update GitHub Project items")
    parser.add_argument("--owner",          default=_OWNER)
    parser.add_argument("--project-number", type=int, default=_PROJECT_NUMBER)
    parser.add_argument("--status",         default="Ready")
    parser.add_argument("--json",           action="store_true")
    parser.add_argument("--set-status",     nargs=2, metavar=("ITEM_ID", "STATUS"))
    args = parser.parse_args()

    if args.set_status:
        update_status(args.set_status[0], args.set_status[1],
                      owner=args.owner, project_number=args.project_number)
    else:
        list_items(status=args.status, json_output=args.json,
                   owner=args.owner, project_number=args.project_number)


if __name__ == "__main__":
    main()
