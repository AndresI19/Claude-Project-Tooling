---
name: record
description: Record the current Claude session to RS-Agent-Planning/Claude Sessions. Must only run when explicitly invoked by the user. Never invoke proactively or as a follow-on step. The "auto" argument is reserved for Stop hook automation only.
---

Record the current Claude session to `~/git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions/`.

## Pre-flight — Confirm explicit user request

**Before doing anything**, verify one of the following is true:

1. The user explicitly invoked this skill in their last message (e.g. typed `record`, `/record`, or a clear equivalent).
2. The skill was called with the `auto` argument — this is the Stop hook path and is always permitted.

If Claude is running this as a proactive follow-on step or inferred end-of-session cleanup — **stop immediately and do not proceed**. The user must ask for it explicitly.

---

## Pre-flight — Check for Claude-Project-Tooling changes

Before writing the session log, run:
```bash
git -C ~/git-workspace/claude-workspace/Claude-Project-Tooling status --short
```

If there are **any uncommitted or unstaged changes** in that repo, stop and tell the user:

> Claude-Project-Tooling has uncommitted changes. Run `/pr` to open a pull request for those changes before recording — otherwise they won't be pushed (push_sessions.py only pushes RS-Agent-Planning session logs).

Do **not** proceed with the session log until the user confirms how to handle it (either they run `/pr` or they confirm the changes can be discarded).

---

## Step 1 — Determine action

```bash
python3 /home/ClaudeSpace/git-workspace/claude-workspace/Claude-Project-Tooling/claude/recording/session_detect.py [auto]
```

Pass `auto` as the argument if the skill was invoked with `auto`. The script outputs JSON:
`{"action": "append"|"new"|"ask", "file": "/path/to/latest.md", "latest_date": "YYYY-MM-DD", "today": "YYYY-MM-DD"}`

**Branch logic:**
- `new` → go to **CREATE NEW LOG**
- `append` → go to **APPEND**
- `ask` → prompt the user:
  ```
  The last session log is from [latest_date]. Create a new log for today?
  1) Yes — create new log
  2) No — append to existing
  ```
  → 1 → **CREATE NEW LOG**, 2 → **APPEND**

---

## CREATE NEW LOG

1. Run `date +"%Y-%m-%d %H:%M"` for the timestamp.
2. Write a new file at:
   `~/git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions/YYYY-MM-DD-HH:MM.md`
   with these sections:
   - `# Claude Session — YYYY-MM-DD HH:MM`
   - `## Summary` — first entry using the format described below
   - `## Terminal Commands — YYYY-MM-DD HH:MM` — all bash commands in a single fenced code block with inline comments
   - `## Files Created — YYYY-MM-DD HH:MM` — markdown table of files created or modified (path + description)
   - `## Notes` — important reminders or follow-up items
3. Only if apps were installed or updated this session: update `~/git-workspace/claude-workspace/Claude-Project-Tooling/dev-workspace-versions.md` (run version commands to get accurate versions; add/update rows, never remove existing entries).
4. Go to **TOKEN USAGE**, then **PUSH**.

---

## APPEND

1. Read the file path returned by session_detect.py.
2. Insert a new summary entry into the existing `## Summary` section (after the last `### ` entry already there).
3. Append a new `## Terminal Commands — YYYY-MM-DD HH:MM` section and a new `## Files Created — YYYY-MM-DD HH:MM` section at the bottom of the file covering everything done since the last record.
4. Only if apps were installed or updated this session: update `~/git-workspace/claude-workspace/Claude-Project-Tooling/dev-workspace-versions.md` same as above.
5. Go to **TOKEN USAGE**, then **PUSH**.

---

## Summary format

The `## Summary` section contains one `### YYYY-MM-DD HH:MM` subsection per record invocation. Each subsection uses bold topic labels followed by a concise description on the same line. Group related work under the same label. Example:

```markdown
## Summary

### 2026-04-25 15:38
**Skills** — created init skill, merged sess-add/append/push-session into record, deleted legacy skills
**Config** — added claude alias to .bashrc, set bypassPermissions in settings.json, removed Stop hook

### 2026-04-25 17:45
**PR skill** — reduced from 8 to 5 steps, chained commands, removed redundant fetch+merge
**Permissions** — fixed dangerouslySkipPermissions schema, added explicit allow rules for git/gh/for/python3/rm
**Record skill** — combined Step 1 commands, conditional dev-workspace-versions update, chained PUSH
```

---

## TOKEN USAGE

Run:
```bash
python3 /home/ClaudeSpace/git-workspace/claude-workspace/Claude-Project-Tooling/claude/recording/token_usage.py
```

Replace the session table rows and totals in
`~/git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions/Usage/token-usage.md`
and update the "Last updated" date. The script outputs one `| row |` per session file followed by a `TOTALS` line.

---

## PUSH

```bash
python3 /home/ClaudeSpace/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/scripts/push_sessions.py --message "MESSAGE"
```

Use a short descriptive commit message (e.g. "Update Claude Sessions and token usage"). The script only stages and pushes files under `Claude Sessions/` in RS-Agent-Planning. Claude-Project-Tooling is never touched — script changes there must go through `/pr`.
