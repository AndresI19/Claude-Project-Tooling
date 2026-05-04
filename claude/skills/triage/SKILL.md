---
name: triage
description: Project-wide issue triage. Pulls every open item in a GitHub Project, reasons about each one (dependencies, observable PR state, staleness, label intent), proposes status moves with explanations, and applies them as a batch after explicit user authorization. Use when project board statuses have drifted, after a /git-plan creation pass, or when issues have closed externally and dependent items need to advance.
---

Triage a GitHub Project: read every open item, propose status moves with reasoning, present them as a table, get the user's approval, apply the batch.

## Step 1 — Pick the project

The skill argument (if any) is a free-form project name. Resolve it to a project number:

- **No argument** → render the selector menu:
  ```bash
  python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/list_projects.py --no-create-new
  ```
  Play `user-select.wav` before prompting; ask "Pick? (number, or 0 to cancel)". The user picks.

- **Argument provided** → load the project list as JSON:
  ```bash
  python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/list_projects.py --json
  ```
  Match the argument against project titles:
  - **Exact (case-insensitive) match** → proceed with that project
  - **Multiple plausible matches** (substring or fuzzy) → present a "Did you mean…" disambiguation prompt; do not silently substitute
  - **No matches** → render the full selector menu

Capture `PROJECT_NUMBER` and `OWNER` for the rest of the flow. `OWNER` comes from the workspace config; `PROJECT_NUMBER` is the user's selection.

## Step 2 — Pull all items + their issue context

Fetch every open item in the project:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/ready_items.py \
  --include-statuses="Backlog,Todo,Ready,In Progress,Verify"
```

This returns a JSON array of items with `item_id`, `number`, `title`, `labels`, `url`, `status`. Done items aren't included — they don't need triage.

For each item, fetch its body and recent comments:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/issue_context.py NUMBER --repo OWNER/REPO
```

Cache all context in-memory for the rest of the session. For a 20-item project, expect ~20 calls; that's the budget.

## Step 3 — Reason per item

For each open item, decide on a **proposed status**. Consider:

- **Observable PR state** — Use `gh pr list --search "linked:NUMBER"` (or scan the issue body / comments for `Closes`, `Fixes`, `Resolves` clauses) to find linked PRs. If a `Closes` PR has merged, item should move to **Done**. If a PR is open and review is pending, **Verify** is appropriate.
- **Mentioned blockers** — Issue bodies may still contain `## Blocked By` sections (the writer side wasn't removed). Treat them as a hint, not a rule. If all blockers have closed, the item can advance from Todo → Ready. If at least one blocker is still open, the item belongs in Todo (or Backlog if also low-priority).
- **Labels** — Epic items never move; their child items advance instead. Discovery/Inquiry items can move Backlog → Ready when there's bandwidth and they aren't blocked. Defect items in the active queue typically take precedence over Backlog work.
- **Comment activity** — A Verify item with no PR and no activity for 30+ days is a signal for either Done (forgotten close) or back to Ready (forgotten work). Read the body before guessing.
- **Project shape** — If 5 items are already In Progress, don't propose moving more from Ready to In Progress. Surface workflow imbalance instead.

For each item, produce a tuple:

```
(item_id, number, title, current_status, proposed_status, dependencies_summary, reasoning)
```

If `proposed_status == current_status`, the row is a "no change" row and renders muted in the table — but the user still sees it (transparency over brevity).

## Step 4 — Render the proposal table

Format the proposal as a markdown table. Use status emojis from the canonical map (see `git-tools/lib/status_emojis.py`):

```
Triage proposal — <Project Title> (N items, M changes proposed)

| #   | Issue                        | Now           | →  | Proposed     | Dependencies        | Reasoning                                          |
|-----|------------------------------|---------------|----|--------------|---------------------|----------------------------------------------------|
| 1.  | #41 Add street prices …      | 🟡 Verify     | →  | 🟢 Done      | PR #33 merged       | PR merged 2 days ago; safe to close                |
| 2.  | #21 Configure TLS and proxy  | ⚪ Ready      | →  | 🟠 Todo      | needs #20           | #20 not yet started; can't do TLS without host     |
| 3.  | #46 Investigate RS LLM       | ⚪ Ready      | →  | ⚫ Backlog   | —                   | No active driver; defer until Phase 2 starts       |
| 4.  | #29 Investigate Actions notif| 🟡 Verify     | →  | 🟢 Done      | PRs #48 & #61 merged| Both companion PRs merged                          |
| 5.  | #19 Validate cache TTL       | ⚪ Ready      |    | (no change)  | —                   | Already in correct state                           |
| …   | (other no-change rows)       |               |    |              |                     |                                                    |

Legend: ⚫ Backlog · 🟠 Todo · ⚪ Ready · 🔵 In Progress · 🟡 Verify · 🟢 Done

Apply all M changes? (y / e / n)
  y = approve all
  e = edit (specify rows to skip or override; see below)
  n = cancel
```

Number the rows 1..N, including no-change rows, so the user can reference any row by its number when editing.

## Step 5 — Authorization gate (with edits)

Play `user-select.wav` before the prompt, then call `AskUserQuestion` with one question:

- `question`: "Apply <N> proposed status change(s)?"
- `header`: "Triage"
- `multiSelect`: false
- `options`:
  - **Approve all** — proceed to Step 6 with the proposal as-is.
  - **Propose change** — open a free-text follow-up prompt where the user lists edits.
  - **Cancel** — abort. Print "Triage cancelled — no changes applied." and exit.

If the user picks **Propose change**, ask "What changes? (one per line)". Parse each line as a directive:
- `skip <row>` — remove row's proposed change from the batch (turns into "no change")
- `<row> → <Status>` — override the proposed status for that row (e.g. `3 → Todo` keeps issue #46 as Todo instead of demoting to Backlog)
- `add <row> → <Status>` — promote a previously-no-change row into the batch with the given target status

After applying edits, re-render the table from Step 4 with overrides and re-prompt with `AskUserQuestion` again. Loop until **Approve all** or **Cancel**.

Status names in directives match the canonical names: Backlog, Todo, Ready, In Progress, Verify, Done.

## Step 6 — Apply the batch

Build a JSON array of approved moves and pipe to the batch endpoint:

```bash
echo '[{"item_id":"PVTI_…","status":"Done"},{"item_id":"PVTI_…","status":"Backlog"}]' | \
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/set_statuses.py
```

The script applies all mutations in a single GraphQL request and prints `✓ N status mutation(s) applied.`

If the call fails, surface the error to the user — the underlying call is atomic per-item server-side, so partial application is rare but possible. On failure, list which items succeeded vs. failed (parse from the GraphQL response if needed).

## Step 7 — Report

Print a one-line confirmation with the project name, count of moves applied, and a link back to the project board so the user can verify. Done.

---

## Notes for `/git-plan` Branch A integration

When invoked from `/git-plan`'s "operate on existing project" sub-flow, skip Step 1 (the project is already chosen) and start at Step 2.
