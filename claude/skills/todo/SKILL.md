---
name: todo
description: Create a GitHub issue from free-form text. Discovers issue-enabled repos in the workspace, suggests the top three by relevance, then generates a short title, description, and appropriate labels before opening the issue.
---

Create a GitHub issue from the text passed as the skill argument.

## Step 1 — Read the input

The skill argument is the raw text the user typed after /todo. Use it to understand the intent.

## Step 2 — Pick the target repo

The repo set is discovered, not hardcoded. As new repos join the workspace they appear here automatically — no skill edit needed.

### Discover candidates

```bash
gh repo list AndresI19 --json name,nameWithOwner,description,hasIssuesEnabled --limit 100
```

Filter the result to repos that:
1. Have `hasIssuesEnabled: true`, AND
2. Have a matching directory under `$HOME/git-workspace/claude-workspace/` (so archived or unrelated repos in the account don't get suggested):
   ```bash
   ls $HOME/git-workspace/claude-workspace
   ```

### Rank top 3

Score each candidate against the issue text. Combine these signals:
- **Lexical match**: issue keywords against the repo's name and description
- **Domain hints** (extend as new repos appear):
  - tooling, skills, scripts, claude config, workspace infrastructure, hooks, cron, /pr, /todo, /new-task, /work-flow, /review → favor `Claude-Project-Tooling`
  - planning, agents, architecture, MCP server, tools (search_wiki / get_item_price / get_player_stats / get_quest_info), wiki, hiscores, GE → favor `RS-Agent-Planning`

The single top-ranked candidate is the **Recommended** choice. Take the next two highest-ranked candidates as the alternates. If fewer than 3 candidates exist, present whatever you have (minimum 2 required by `AskUserQuestion`).

### Present the choice

Call the `AskUserQuestion` tool with one question:
- `question`: "Which repo should this issue go to?"
- `header`: "Repo"
- `multiSelect`: false
- `options`: up to 3 entries. Each entry's `label` is the repo `nameWithOwner` (suffix " (Recommended)" on the highest-ranked one, per the tool's convention). Each entry's `description` is a one-sentence rationale for why this repo fits.

The tool automatically appends an **Other** escape — selecting it lets the user type any `owner/repo` value (or cancel via escape).

### Resolve `TARGETREPO`

- Selected one of the presented options → use its `nameWithOwner` as `TARGETREPO`.
- Selected Other and typed a value → validate it matches `<owner>/<repo>` shape AND that `gh repo view <owner/repo>` succeeds. If validation fails, show the error and re-prompt.
- Cancelled → exit the skill silently.

## Step 3 — Generate title, description, and labels

From the input text, derive:
- **Title**: short, imperative, max 6 words (e.g. "Add retry logic to pr skill", "Fix token usage parsing")
- **Description**: 1-3 sentences expanding on the intent. Be concise. No bullet lists. Do not speculate on root cause or solutions — describe only the observed problem or desired outcome.
- **Labels**: pick all that apply from the standard vocabulary below. Most issues take 1-2 labels.

### Label vocabulary

| Label | When to use |
|-------|-------------|
| `Code` | Writing new feature code |
| `Defect` | Fixing broken or incorrect behavior |
| `Discovery` | Investigation or research needed before work can start |
| `Inquiry` | Open design question that must be resolved first |
| `DevOps` | Infrastructure, deployment, CI/CD, or automation work |
| `Service: <name>` | Changes specific to a named service (e.g. `Service: MCP`). Project-specific — only present on repos that defined them. |
| `Epic` | Do not use — reserved for git-plan |

The universal labels above (`Code`, `Defect`, `Discovery`, `Inquiry`, `DevOps`, `Epic`) are installed on every repo by `init_labels.py`. Service-specific tags are project-local and may not exist on the target repo — if uncertain, omit them and let the issue be re-tagged later.

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

`TARGETREPO` is the full `owner/repo` from Step 2.

### `--project` flag

Include `--project` when `TARGETREPO` has an active GitHub Project board. Project-bearing repos in the workspace today:

| Repo | Project |
|------|---------|
| `AndresI19/RS-Agent-Planning` | Build RuneScape MCP Server |

When new project-bearing repos appear, add them to this table.

For repos without a project board (e.g. `AndresI19/Claude-Project-Tooling` today), omit `--project`.

When `--project` is used, the script prints `ITEM_ID: <id>` followed by the issue URL. **Capture both.**

## Step 5 — Set initial project status (project-bearing repos only)

Skip this step entirely for repos without a project board.

For project-bearing repos, decide between **Todo** (queued, blocked by other work) and **Ready** (can be picked up immediately) by inferring sequential dependencies from existing project items.

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
