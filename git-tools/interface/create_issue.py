#!/usr/bin/env python3
"""Create a GitHub issue — stable interface path for the /todo skill.
Usage: create_issue.py --repo OWNER/REPO --title "..." --body "..." --label Code
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from create_issue import create

parser = argparse.ArgumentParser()
parser.add_argument("--repo",  required=True)
parser.add_argument("--title", required=True)
parser.add_argument("--body",  default="")
parser.add_argument("--label", action="append", default=[], dest="labels")
args = parser.parse_args()

create(repo=args.repo, title=args.title, body=args.body, labels=args.labels)
