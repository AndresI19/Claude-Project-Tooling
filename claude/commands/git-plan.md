# /git-plan

Operate on a GitHub project: pick an existing one to triage or extend, or create a new one from scratch.

## Pre-flight — Project selector

**Before doing anything else**, render the selector menu:

```bash
python3 Claude-Project-Tooling/git-tools/interface/list_projects.py
```

The script prints a numbered list of every existing project (oldest first, with the oldest active project highlighted as `/work-flow default`) plus a `0. + Create new project` row.

Play `user-select.wav` and prompt: "Pick? (number, or 0 to cancel)".

- **User picks 1..N** → the chosen project becomes `PROJECT`. Proceed to **Branch A: operate on existing project**.
- **User picks 0** → proceed to **Branch B: create new project**.
- **User cancels** → exit cleanly.

---

## Branch A — Operate on existing project

Show the chosen project's status counts (already returned by `list_projects.py --json`), then sub-prompt:

> "What do you want to do with `<Project title>`?
>   1. Triage — review proposed status moves
>   2. Extend — add new Epics or Issues
>   3. Both — triage first, then extend
>   0. Cancel"

Play `user-select.wav` before the prompt.

### Branch A.1 — Triage

Invoke the `/triage` skill against the selected project. Skip its Step 1 (project already chosen) and start at Step 2 — pull all open items, reason about each, render the proposal table, get authorization, apply.

### Branch A.2 — Extend

Run a **modified Phase 1/2** that adds new Epics/Issues to the existing project without touching anything that already exists.

#### Phase 1 (extend) — Plan additions only

Call `EnterPlanMode` immediately. Then:

1. **Gather context.** Read `RS-Agent-Planning/Planning/project-overview.md`, `architecture.md`, and `tasks.md`. List the existing project's open items (from the JSON output of `list_projects.py`) so the new plan complements rather than duplicates them.

2. **Draft additions only.** Propose new Epics and/or new Issues that fit into the existing project. Do NOT re-list items that already exist.

3. **Write the plan** to the plan file in the same format as Branch B (see "Plan File Format" below), but only the new content.

4. **Iterate.** Adjust based on feedback.

5. Call `ExitPlanMode` to present the plan for final approval.

#### Phase 2 (extend) — Execute

Serialize the approved additions into the same JSON schema as Branch B, with `project_title` set to **the existing project's exact title**:

```bash
python3 Claude-Project-Tooling/git-tools/scripts/git-plan.py --meta '<JSON>'
```

`git-plan.py` is idempotent for existing items — it creates new Epics/Issues, links child issue numbers into Epic checklists, and **only sets status on newly created issues**. Existing items are never overwritten on re-runs. That property is what makes "extend" safe.

### Branch A.3 — Both

Run Branch A.1 (triage) first. After moves are applied, ask if the user wants to extend; if yes, run Branch A.2.

---

## Branch B — Create new project

This is the original `/git-plan` create-from-scratch flow. The Phase 1/2 logic below is unchanged.

### Hierarchy

| Level | GitHub object | Scope |
|-------|--------------|-------|
| Project | GitHub Project | One sequential deliverable end-to-end (e.g. "Build MCP Server") |
| Epic | Issue + "Epic" label | 3–12 issues; a coherent chunk of work within a project |
| Issue | Issue | One deliverable unit, ≤2 tasks, simple and achievable |

**All planning issues, epics, and projects are created in `AndresI19/RS-Agent-Planning`.**

### Phase 1 — Plan (read-only)

Call `EnterPlanMode` immediately before doing anything else.

Then:

1. **Gather context.** Read `RS-Agent-Planning/Planning/project-overview.md`, `architecture.md`, and `tasks.md`. If the user provided a scope as an argument (e.g. `/git-plan MCP Server Phase 1`), focus there. Otherwise ask.

2. **Generate top-down:**
   - Propose the Project (name + one-line goal)
   - Break into Epics
   - For each Epic, draft Issues with labels, status, and explicit blockers

3. **Write the plan** to the plan file in the format below.

4. **Iterate.** Adjust based on feedback, update the plan file, and re-present until approved.

5. Call `ExitPlanMode` to present the plan for final approval.

### Plan File Format

```
## <Project Name>
<One sentence: what this project delivers>

### Epic 1: <Title>
<One sentence: what this epic covers>
- [ ] <Issue title> — <one-line description> · labels: <label, label> · status: Ready · blocked_by: none
- [ ] <Issue title> — <one-line description> · labels: <label> · status: Todo · blocked_by: <Issue title>
- [ ] ...

### Epic 2: ...
```

**Status rules:**
- `Ready` — no blocker; can be picked up immediately
- `Todo` — blocked by one or more specific issues that must complete first
- `Backlog` — intentionally deferred; not yet in scope for active work
- Epics always get `Todo` (they track child completion, not active work)
- Only the first unblocked issue(s) in a dependency chain are `Ready`; everything downstream is `Todo`
- Issues in later epics that are far from current work should be `Backlog`

**Blocker rules:**
- List the exact titles of blocking issues in `blocked_by`
- A blocker must be another issue in this plan
- Multiple blockers are comma-separated
- Use `none` when there are no blockers

### Phase 2 — Execute (after ExitPlanMode approval)

Serialize the approved plan into the JSON schema below and run:

```bash
python3 Claude-Project-Tooling/git-tools/scripts/git-plan.py --meta '<JSON>'
```

### JSON Schema

```json
{
  "project_title": "...",
  "repo": "AndresI19/RS-Agent-Planning",
  "epics": [
    {
      "title": "...",
      "description": "One sentence covering what this epic delivers.",
      "status": "Todo",
      "issues": [
        {
          "title": "...",
          "description": "One sentence describing the deliverable.",
          "labels": ["Code", "Service: MCP"],
          "status": "Ready",
          "blocked_by": []
        },
        {
          "title": "...",
          "description": "One sentence describing the deliverable.",
          "labels": ["Code", "Service: MCP"],
          "status": "Todo",
          "blocked_by": ["Title of blocking issue"]
        }
      ]
    }
  ]
}
```

`status` must be one of: `"Ready"`, `"Todo"`, `"Backlog"`. Epics always use `"Todo"`.
`blocked_by` is a list of issue titles from this plan. Empty list `[]` means no blockers.

The script:
1. Creates the GitHub Project, Epics, and Issues
2. Appends a `## Blocked By` section to issue bodies listing resolved issue numbers
3. Links child issue numbers back into each Epic's checklist body
4. Adds everything to the project board with the correct initial status
5. **Only sets status on newly created issues** — existing items are never overwritten on re-runs

---

## Label Guidelines

Epics always receive the **Epic** label. For issues:
- **Code** — writing new feature code
- **Service: MCP** — changes to the MCP server specifically
- **DevOps** — infra, deployment, CI/CD
- **Discovery** — investigation needed before work can start
- **Inquiry** — open design decision that must be resolved first
- **Defect** — fixing broken behavior

## Constraints

- Epics: minimum 3 issues, maximum 12
- Issues: maximum 2 sub-tasks; one deliverable per issue
- Projects: one sequential scope per project; don't mix unrelated deliverables
