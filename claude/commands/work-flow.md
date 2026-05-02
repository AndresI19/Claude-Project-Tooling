# /work-flow

Drive the project loop: work through Verify, In Progress, and Ready issues, then plan the next project.

## Pre-flight — Advance Ready items

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/advance_ready.py
```

Report any items just promoted. Then enter the loop.

---

## Loop — Work through the queue

Repeat steps 1–7 until the queue is empty. **Do not stop between iterations** — after moving an issue to Verify, immediately return to step 1 without waiting for user instruction.

**Each iteration MUST re-fetch fresh project state via `ready_items.py`.** Never render the next iteration's menu from the previous iteration's data — the user may have closed an issue, moved a card, or merged a PR (auto-closing its issue) between iterations. Stale menus that show items in the wrong column (e.g., still showing a closed issue as Verify) are the most common loop bug. Treat in-context memory of a prior iteration's queue as untrusted.

### Steps 1–6 — Delegate to /new-task

Run the full `/new-task` flow for each iteration. This handles, in order:
- Building the unified Verify/In Progress/Ready list (with link emojis and color-coded status chips) — **always from a fresh `ready_items.py` read, never from cached data**
- Selecting an item
- Inferring the target repo
- Resume detection (existing branch with `-I<N>` suffix)
- Pre-flight uncommitted-changes prompt (4 options)
- Branch creation off `origin/main`
- Moving the issue to In Progress
- Plan mode kickoff with full context (issue link, branch, recap, comments)
- Doing the work end to end

Continue until the issue is fully resolved. Surface blockers or open questions to the user as they arise.

### Step 7a — PR gate (must run before transitioning)

Check the issue labels:

- **Labels include `Code`, `Service: MCP`, or `DevOps`** → **STOP.** Ask the user:
  > "Want me to open a PR for this?"
  Wait for an explicit yes or no. If yes, invoke `/pr`. **Do not proceed to Step 7b until this is resolved.**
- **Labels are only `Inquiry`, `Discovery`, or documentation-only** → skip to Step 7b immediately.

### Step 7b — Move issue to Verify

Do **not** `gh issue close`. Instead, move the issue to Verify so the user reviews before it's closed:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/set_status.py ITEM_ID "Verify"
```

The user closes the issue manually after reviewing the work / merging the PR. Verify items appear at the top of the next iteration's task list (yellow chip), so they remain visible as a reminder until acted on.

After moving to Verify, run advance-ready to surface any newly unblocked items:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/advance_ready.py
```

### Step 7c — Workspace cleanup

Before starting the next iteration, free anything the previous task left running so the next task can come up clean. Currently this means: stop the MCP dev server if it is up.

```bash
make -C $HOME/git-workspace/claude-workspace/rs-mcp-server stop
```

`make stop` is a no-op if nothing is on port 8000, so it is safe to run unconditionally. Add similar one-line cleanups here as new long-lived dev processes appear (e.g., a future Discord bot dev runner).

Report any promotions, then **immediately return to Step 1**.

---

## Transition — Queue is empty

When the unified queue (Verify + In Progress + Ready) is empty and advance-ready promotes nothing:

### Check remaining items

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/status_items.py Todo
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/status_items.py Backlog
```

- **Items remain in any status** → report the state and stop. Blockers or deferred work may need manual attention before the project can complete.
- **All queues empty** → the project is done. Invoke /git-plan to plan the next one.
