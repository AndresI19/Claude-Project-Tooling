# /git-plan

Generate a top-down GitHub project plan, then create it in GitHub upon approval.

## Pre-flight — Check for an active project

**Before doing anything else**, run:

```bash
python3 Claude-Project-Tooling/git-tools/interface/loop_state.py
```

`loop_state.py` returns JSON with `next_action`:

- `"continue"` — Ready or In Progress items exist. Stop and report; the project is still active.
- `"blocked"` — Todo/Backlog items remain but all blockers are still open. Stop; issues must be resolved first.
- `"plan"` — all queues empty. Proceed to Phase 1.

---

## Hierarchy

| Level | GitHub object | Scope |
|-------|--------------|-------|
| Project | GitHub Project | One sequential deliverable end-to-end (e.g. "Build MCP Server") |
| Epic | Issue + "Epic" label | 3–12 issues; a coherent chunk of work within a project |
| Issue | Issue | One deliverable unit, ≤2 tasks, simple and achievable |

**All planning issues, epics, and projects are created in `AndresI19/RS-Agent-Planning`.**

## Phase 1 — Plan (read-only)

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

## Phase 2 — Execute (after ExitPlanMode approval)

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
