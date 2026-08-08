#!/usr/bin/env python3
"""Find plain (unquoted) YAML scalars containing ': ' — illegal, and the single most frequent
cause of a card file failing to parse.

A plain scalar cannot contain ": " ANYWHERE, including the continuation lines of a wrapped
string, so `text: Derive it: 1,200 posts/sec` reparses as a mapping. The parser's error points
at the structural confusion rather than the offending line, which is why hunting by eye is slow.

Usage:  python3 scan-colons.py cards/p-system-design-patterns.yaml [more.yaml ...]
        python3 scan-colons.py cards/[a-z]-*.yaml        # sweep everything

Exit status is 1 when anything is found, so it can gate a commit.
"""
import re
import sys

KEY = re.compile(r"^(\s*)(-\s+)?([a-z_]+):\s*(.*)$")


def scan(path: str) -> int:
    lines = open(path).read().split("\n")
    hits = []
    i = 0
    while i < len(lines):
        m = KEY.match(lines[i])
        if not m:
            i += 1
            continue
        indent, dash, key, val = m.groups()
        # Skip quoted, block (| >), and empty values — only PLAIN scalars are at risk.
        if not val or val[0] in "\"'|>&*[{#":
            i += 1
            continue
        start, block = i, [val]
        base = len(indent) + (len(dash) if dash else 0)
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                break
            ind = len(nxt) - len(nxt.lstrip())
            if ind <= base or KEY.match(nxt) or nxt.lstrip().startswith("- "):
                break
            block.append(nxt.strip())
            j += 1
        if ": " in " ".join(block):
            hits.append((start + 1, key, " ".join(block)[:80]))
        i = j if j > i else i + 1

    for ln, key, txt in hits:
        print(f"  {path}:{ln}  {key}: {txt}")
    print(f"{path}: {len(hits)} offending scalar(s)")
    return len(hits)


total = sum(scan(p) for p in sys.argv[1:])
sys.exit(1 if total else 0)
