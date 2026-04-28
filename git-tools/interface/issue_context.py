#!/usr/bin/env python3
"""Fetch issue title, body, labels, and comments for plan-mode context.

Usage:
    issue_context.py NUMBER --repo OWNER/REPO

Output: JSON with title, body, labels, url, state, number, comments.
Each comment has: author, created_at, body.
"""
import argparse
import json
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("number", type=int)
parser.add_argument("--repo", required=True, help="OWNER/REPO")
args = parser.parse_args()

result = subprocess.run(
    ["gh", "issue", "view", str(args.number), "--repo", args.repo,
     "--json", "title,body,labels,comments,url,state,number"],
    capture_output=True, text=True,
)
if result.returncode != 0:
    print(f"ERROR: {result.stderr.strip()}", file=sys.stderr)
    sys.exit(1)

data = json.loads(result.stdout)
data["labels"] = [l.get("name", "") for l in data.get("labels", [])]
data["comments"] = [
    {
        "author": c.get("author", {}).get("login", "unknown"),
        "created_at": c.get("createdAt", ""),
        "body": c.get("body", ""),
    }
    for c in data.get("comments", [])
]
print(json.dumps(data, indent=2))
