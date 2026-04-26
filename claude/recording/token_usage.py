#!/usr/bin/env python3
"""
Calculates token usage across all Claude session files and prints a markdown table.

Usage:
    python3 token_usage.py

Output: markdown table rows + a TOTALS line for the record skill to insert into
        RS-Agent-Planning/Claude Sessions/Usage/token-usage.md
"""

import glob
import json
import os
from datetime import datetime

JSONL_GLOBS = [
    os.path.expanduser("~/.claude/projects/-home-ClaudeSpace/*.jsonl"),
    os.path.expanduser("~/.claude/sessions/*.jsonl"),
]


def main():
    total_input = total_output = total_cache_read = total_cache_write = 0
    sessions = []

    for pattern in JSONL_GLOBS:
        for f in glob.glob(pattern):
            sess_input = sess_output = sess_cache_read = sess_cache_write = 0
            date = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d")

            with open(f) as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        usage = rec.get("usage") or rec.get("message", {}).get("usage", {})
                        if usage:
                            sess_input       += usage.get("input_tokens", 0)
                            sess_output      += usage.get("output_tokens", 0)
                            sess_cache_read  += usage.get("cache_read_input_tokens", 0)
                            sess_cache_write += usage.get("cache_creation_input_tokens", 0)
                    except Exception:
                        pass

            if sess_input or sess_output:
                sessions.append((date, os.path.basename(f)[:8], sess_input, sess_output, sess_cache_read, sess_cache_write))
                total_input       += sess_input
                total_output      += sess_output
                total_cache_read  += sess_cache_read
                total_cache_write += sess_cache_write

    sessions.sort()

    for s in sessions:
        print(f"| {s[0]} | {s[1]} | {s[2]:,} | {s[3]:,} | {s[4]:,} | {s[5]:,} |")

    print(f"TOTALS {total_input:,} {total_output:,} {total_cache_read:,} {total_cache_write:,}")


if __name__ == "__main__":
    main()
