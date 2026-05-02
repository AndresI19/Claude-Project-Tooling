---
name: todo
description: Create a GitHub issue from free-form text. Routes the issue to the correct tracker repo (some workspace repos delegate their issues to a central tracker), then generates a short title, description, and appropriate labels before opening it.
---

Create a GitHub issue from the text passed as the skill argument.

## Step 1 — Read the input

The skill argument is the raw text the user typed after /todo. Use it to understand the intent.

## Step 2 — Pick the target tracker

Issues are filed in **tracker repos** — repos whose Issues tab actually accepts and tracks issues. Other workspace repos are **delegates**: their source code lives there, but their issues are tracked elsewhere. The picker presents only tracker repos.

### Workspace tracker map

This table is the source of truth for which repo accepts issues for each domain. When new repos join the workspace, add a row.

| Workspace repo | Acts as | Tracker | Auto Service tag |
|----------------|---------|---------|------------------|
| `AndresI19/RS-Agent-Planning` | tracker (self) | `AndresI19/RS-Agent-Planning` | — |
| `AndresI19/rs-mcp-server` | delegate | `AndresI19/RS-Agent-Planning` | `Service: MCP` |
| `AndresI19/Claude-Project-Tooling` | tracker (self) | `AndresI19/Claude-Project-Tooling` | — |
| (future RS-* code repo) | delegate | `AndresI19/RS-Agent-Planning` | `Service: <name>` |

**Why some repos delegate**: `RS-Agent-Planning` is the centralized issue tracker and project board for the entire RuneScape project. RS-* code repos (`rs-mcp-server` today; potentially a Discord bot, voice service, etc. in the future) all funnel their issues there with `Service: <name>` labels distinguishing which code repo each issue targets. `Claude-Project-Tooling` is general workspace tooling — not part of the RuneScape project — so it tracks its own issues.

### Discover candidates

```bash
gh repo list AndresI19 --json name,nameWithOwner,description,hasIssuesEnabled --limit 100
```

Filter the result to repos that are:
1. `hasIssuesEnabled: true`, AND
2. Present as a directory under `$HOME/git-workspace/claude-workspace/`:
   ```bash
   ls $HOME/git-workspace/claude-workspace
   ```
3. Listed as a **tracker** (`Acts as: tracker`) in the table above. Delegate repos are NOT eligible candidates — their issues route through their tracker.

### Determine the implied delegate (if any)

Inspect the issue text to identify which workspace component it concerns:
- If the issue is about an **RS-* code repo's domain** (e.g., MCP server tools, hiscores tooling, future Discord bot, etc.) → that delegate's tracker (`RS-Agent-Planning`) is the correct destination, AND the delegate's `Auto Service tag` should be applied automatically.
- If the issue is about **workspace tooling** (skills, scripts, hooks, /pr, /todo, /new-task, /work-flow, /review, etc.) → `Claude-Project-Tooling`'s self-tracker is the destination. No Service tag.
- If the issue is about **planning, agent architecture, or project-level concerns** that aren't tied to a specific RS code repo → `RS-Agent-Planning` directly. No Service tag.

### Rank top 3 trackers

Apply the domain hints above to rank the discovered tracker repos. The single top-ranked is the **Recommended** choice. Take the next two highest-ranked as alternates. With only two tracker repos in the workspace today, present 2 options (the auto-Other escape covers any third destination).

### Present the choice

Call the `AskUserQuestion` tool with one question:
- `question`: "Which repo should this issue go to?"
- `header`: "Repo"
- `multiSelect`: false
- `options`: up to 3 tracker repos. Each entry's `label` is the tracker's `nameWithOwner` (suffix " (Recommended)" on the highest-ranked). Each entry's `description` explains what kinds of issues that tracker accepts and, if relevant, which delegate code repos route to it.

The tool automatically appends an **Other** escape — the user can type any `<owner>/<repo>` (validated against `gh repo view`) or cancel.

### Resolve `TARGETREPO` and `SERVICE_TAG`

- `TARGETREPO` = the chosen tracker's `nameWithOwner`
- `SERVICE_TAG` = the auto Service tag from the table, IF the issue's subject is about a delegate that routes to `TARGETREPO`. Otherwise empty.

If the user picks **Other** and types a delegate code repo by mistake (e.g., `AndresI19/rs-mcp-server`), redirect: replace `TARGETREPO` with the delegate's tracker from the table, set `SERVICE_TAG` to the delegate's auto Service tag, and tell the user "filing in `<tracker>` with `<service tag>` since `<delegate>` delegates its issues there."

## Step 3 — Generate title, description, and labels

From the input text, derive:
- **Title**: short, imperative, max 6 words (e.g. "Add retry logic to pr skill", "Fix token usage parsing")
- **Description**: 1-3 sentences expanding on the intent. Be concise. No bullet lists. Do not speculate on root cause or solutions — describe only the observed problem or desired outcome.
- **Labels**: pick all that apply from the standard vocabulary below. Most issues take 1-2 labels. **If `SERVICE_TAG` is set from Step 2, include it automatically** in addition to whichever universal labels apply.

### Label vocabulary

| Label | When to use |
|-------|-------------|
| `Code` | Writing new feature code |
| `Defect` | Fixing broken or incorrect behavior |
| `Discovery` | Investigation or research needed before work can start |
| `Inquiry` | Open design question that must be resolved first |
| `DevOps` | Infrastructure, deployment, CI/CD, or automation work |
| `Service: <name>` | Changes specific to a named delegate repo (e.g. `Service: MCP`). Auto-applied by Step 2 when the issue routes through a tracker on behalf of a delegate. |
| `Epic` | Do not use — reserved for git-plan |

The universal labels (`Code`, `Defect`, `Discovery`, `Inquiry`, `DevOps`, `Epic`) are installed on every repo by `init_labels.py`. Service-specific tags are project-local and may not exist on every tracker — they're created by `init_labels.py` per-project as needed.

## Step 4 — Create the issue

Run:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/create_issue.py \
  --repo TARGETREPO \
  --title "TITLE" \
  --body "DESCRIPTION" \
  --label LABEL1 --label LABEL2 \
  [--project]
```

`TARGETREPO` is the full `owner/repo` from Step 2. Include `SERVICE_TAG` (if set) as one of the `--label` flags.

### `--project` flag

Include `--project` when `TARGETREPO` has an active GitHub Project board. Project-bearing trackers in the workspace today:

| Tracker | Project |
|---------|---------|
| `AndresI19/RS-Agent-Planning` | Build RuneScape MCP Server |

When new project-bearing trackers appear, add them to this table.

For trackers without a project board (e.g. `AndresI19/Claude-Project-Tooling` today), omit `--project`.

When `--project` is used, the script prints `ITEM_ID: <id>` followed by the issue URL. **Capture both.**

## Step 5 — Set initial project status (project-bearing trackers only)

Skip this step entirely for trackers without a project board.

For project-bearing trackers, decide between **Todo** (queued, blocked by other work) and **Ready** (can be picked up immediately) by inferring sequential dependencies from existing project items.

Fetch all current open project items:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/ready_items.py \
  --include-statuses="In Progress,Ready,Todo,Backlog"
```

Read the new issue's intent against the open items' titles. Apply this rule:

- The new task **logically depends on** another open item (it can only be done after that item completes — e.g., "deploy the server" depends on "provision hosting") → set status to **Todo**
- Otherwise → set status to **Ready**

Then run:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/set_status.py ITEM_ID "Todo"
# or
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/set_status.py ITEM_ID "Ready"
```

Do this silently — do not prompt the user. The chosen status appears in the final URL print.

## Step 6 — Print the result

Print the issue URL and the chosen initial status (if applicable).
