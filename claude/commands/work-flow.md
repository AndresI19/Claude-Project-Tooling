# /work-flow

Drive the full project loop: work through all Ready issues, then plan the next project.

## Pre-flight — Advance Ready items

Run advance-ready first so any newly unblocked items surface before the loop starts:

```bash
python3 Claude-Project-Tooling/git-tools/interface/advance_ready.py
```

Report any items just promoted. Then enter the loop.

---

## Loop — Work through the Ready queue

Repeat steps 1–6 until the Ready queue is empty. **Do not stop between iterations** — after closing an issue, immediately return to step 1 without waiting for user instruction.

### Step 1 — Fetch Ready items

```bash
python3 Claude-Project-Tooling/git-tools/interface/ready_items.py
```

If the list is empty, go to **Transition**.

### Step 2 — Select a task

Display the Ready items in the same numbered format as /new-task. Default to item 1 — state it clearly so the user can redirect:

```
Continuing with #N — [title]. Enter a different number to switch, or say "go" to proceed.
```

Wait for confirmation or a redirect before moving on.

### Step 3 — Show issue context

```bash
gh issue view NUMBER --repo AndresI19/RS-Agent-Planning
```

Display the full issue body.

### Step 4 — Move to In Progress

```bash
python3 Claude-Project-Tooling/git-tools/interface/set_status.py ITEM_ID "In Progress"
```

### Step 5 — Do the work

Work the issue fully based on its labels:

- `Code` / `Service: MCP` → implement the feature; write, test, and verify the code
- `Inquiry` / `Discovery` → read planning docs, produce a concrete decision or finding, write it up in the appropriate planning file
- `DevOps` → implement the infrastructure or automation change

Continue until the issue is fully resolved. Surface blockers or open questions to the user as they arise.

### Step 6a — PR gate (must run before closing)

Check the issue labels:

- **Labels include `Code`, `Service: MCP`, or `DevOps`** → **STOP.** Ask the user:
  > "Want me to open a PR for this?"
  Wait for an explicit yes or no. If yes, invoke `/pr`. **Do not proceed to Step 6b until this is resolved.**
- **Labels are only `Inquiry`, `Discovery`, or documentation-only** → skip to Step 6b immediately.

### Step 6b — Close the issue

```bash
gh issue close NUMBER --repo AndresI19/RS-Agent-Planning
```

After closing, run advance-ready to surface any newly unblocked items:

```bash
python3 Claude-Project-Tooling/git-tools/interface/advance_ready.py
```

Report any promotions, then **immediately return to Step 1**.

---

## Transition — Queue is empty

When the Ready queue is empty and advance-ready promotes nothing:

### Check remaining items

```bash
python3 Claude-Project-Tooling/git-tools/interface/status_items.py "In Progress"
python3 Claude-Project-Tooling/git-tools/interface/status_items.py Todo
python3 Claude-Project-Tooling/git-tools/interface/status_items.py Backlog
```

- **Items remain in any status** → report the state and stop. Blockers or deferred work may need manual attention before the project can complete.
- **All queues empty** → the project is done. Invoke /git-plan to plan the next one.
