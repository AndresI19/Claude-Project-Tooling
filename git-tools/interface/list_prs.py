#!/usr/bin/env python3
"""List open PRs across workspace repos — stable interface path for the /review skill.
Usage: list_prs.py [--json] [--window]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from list_prs import show

parser = argparse.ArgumentParser()
parser.add_argument("--json",   action="store_true")
parser.add_argument("--window", action="store_true")
args = parser.parse_args()

show(json_output=args.json, window=args.window)
