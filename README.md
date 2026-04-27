# Claude-Project-Tooling

Shared scripts, configuration, and tooling for the Claude Code workspace. Used by Claude to automate development workflows across projects.

## Structure

- **`git-tools/scripts/`** — Git workflow automation
  - `pr.py` — Creates pull requests; accepts metadata from Claude in-conversation and handles all git mechanics
  - `push_sessions.py` — Pushes changes in RS-Agent-Planning and Claude-Project-Tooling to origin/main in a single call
- **`claude/recording/`** — Supporting scripts for the `/record` skill
  - `session_detect.py` — Detects the current session log state (new, append, or ask)
  - `token_usage.py` — Calculates token usage across all Claude session files and outputs a markdown table
- **`New Boot/`** — New machine setup guide
- **`dev-workspace-versions.md`** — Installed tool and package versions tracker

## Skills

Skills are Claude Code slash commands that orchestrate the tooling in this repo. They live in two places:

- **`claude/skills/`** — tracked copies checked into this repo (source of truth for history and PRs)
- **`~/.claude/skills/`** — live copies loaded by Claude Code at runtime

Project-level commands (available only inside `claude-workspace/`) live in `.claude/commands/` of the workspace root.

### Summary

| Skill | Scope | Description |
|-------|-------|-------------|
| `/pr` | user | Generate PR metadata in-conversation, then run `pr.py` to branch, commit, push, and open the PR |
| `/record` | user | Write or append to the session log in RS-Agent-Planning, update token usage, and push |
| `/review` | user | List open PRs in a Ptyxis window, load a selected PR, and produce a structured code review |
| `/todo` | user | Create a GitHub issue from free-form text with auto-generated title, body, and labels |
| `/git-plan` | project | Plan a new GitHub project top-down (Epics → Issues), iterate until approved, then create it |
| `/new-task` | project | Pick a Ready issue from the project board and move it to In Progress |
| `/work-flow` | project | Drive the full project loop — work all Ready issues, then trigger `/git-plan` when done |

---

### `/pr`

Create a pull request for any repo in the workspace.

```
Claude (in-conversation)
  └─ generates JSON: { branch_name, commit_message, pr_title, pr_body, labels }
       └─ scripts/pr.py --repo PATH --meta '{...}'
            └─ git, gh CLI  (stash · branch · commit · push · gh pr create)
```

---

### `/record`

Append or create a session log, update token totals, and push.

```
claude/recording/session_detect.py   ← determines: new | append | ask
  │
  ├─ Claude writes/appends session log file directly
  │
  ├─ claude/recording/token_usage.py  ← reads ~/.claude/**/*.jsonl, outputs markdown rows
  │
  └─ scripts/push_sessions.py         ← stages Claude Sessions/, commits, pushes to origin/main
       └─ git CLI
```

---

### `/review`

List open PRs, load the selected one, and review it.

```
interface/list_prs.py --window
  └─ scripts/list_prs.py :: show()
       └─ lib/prs.py        ← collects PRs across all workspace repos
            └─ lib/display.py  ← ANSI color badges

scripts/load_pr.py NUMBER
  └─ lib/prs.py :: get_pr_view() + get_pr_diff()
       └─ lib/github_client.py  ← REST API (gh auth token)

Claude  ← synthesises review from loaded diff + metadata
```

---

### `/todo`

Create a GitHub issue from typed text.

```
Claude (in-conversation)
  └─ generates: title, body, labels
       └─ interface/create_issue.py --repo ... --title ... --body ... --label ...
            └─ scripts/create_issue.py :: create()
                 └─ lib/github_client.py :: get_or_create_issue()  ← REST POST /repos/.../issues
```

---

### `/git-plan`

Plan and execute a new GitHub project.

```
── Pre-flight ──────────────────────────────────────────────────────
interface/advance_ready.py
  └─ scripts/project_advance.py :: run()
       └─ lib/project.py :: advance_ready()
            └─ lib/github_client.py  ← GraphQL (project field mutations)

interface/loop_state.py
  └─ scripts/project_state.py :: loop_state()
       └─ lib/project.py :: items_by_status()

── Phase 1 (plan) ──────────────────────────────────────────────────
Claude reads RS-Agent-Planning/Planning/  ← architecture, tasks, overview
Claude writes plan to plan file; iterates with user

── Phase 2 (execute) ───────────────────────────────────────────────
scripts/git-plan.py --meta '{...}'
  └─ lib/github_client.py  ← GraphQL (create project · epics · issues · link)
```

---

### `/new-task`

Pick a ready task and start it.

```
scripts/project_items.py --status Ready --json
  └─ lib/project.py :: items_by_status()
       └─ lib/github_client.py  ← GraphQL

gh issue view NUMBER  ← direct CLI

scripts/project_items.py --set-status ITEM_ID "In Progress"
  └─ lib/project.py :: set_item_status_by_name()
       └─ lib/github_client.py  ← GraphQL (project field mutation)
```

---

### `/work-flow`

Drive the full project loop autonomously.

```
── Pre-flight ──────────────────────────────────────────────────────
interface/advance_ready.py  (same as /git-plan pre-flight above)

── Per-issue loop ──────────────────────────────────────────────────
interface/ready_items.py
  └─ scripts/project_items.py :: list_items(status="Ready")

gh issue view NUMBER  ← direct CLI

interface/set_status.py ITEM_ID "In Progress"
  └─ scripts/project_items.py :: update_status()

Claude  ← does the work based on issue labels

interface/advance_ready.py  ← promotes any newly unblocked items

── Transition ──────────────────────────────────────────────────────
interface/status_items.py STATUS   ← called for: In Progress · Todo · Backlog
  └─ scripts/project_items.py :: list_items(status=STATUS)

/git-plan  ← invoked when all queues are empty
```
