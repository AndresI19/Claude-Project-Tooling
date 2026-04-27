---
name: todo
description: Create a GitHub issue from free-form text. Prompts the user to choose a repo (Claude-Project-Tooling or RS-Agent-Planning), then generates a short title, description, and appropriate labels before opening the issue.
---

Create a GitHub issue from the text passed as the skill argument.

## Step 1 — Read the input

The skill argument is the raw text the user typed after /todo. Use it to understand the intent.

## Step 2 — Suggest a repo

Infer which repo the issue belongs to based on the text:
- If it relates to tooling, skills, setup, Claude config, or workspace infrastructure → suggest **Claude-Project-Tooling**
- If it relates to planning, agents, architecture, or project work → suggest **RS-Agent-Planning**
- If unclear → suggest **Claude-Project-Tooling** as default

Run the matching bash command to display a colored menu. The suggested repo is highlighted in bold green.

If **Claude-Project-Tooling** is suggested:
```bash
printf '\nWhich repo should this issue go to?\n\n'
printf '  1) \033[1;32mClaude-Project-Tooling\033[0m  \033[32m← suggested\033[0m\n'
printf '  2) RS-Agent-Planning\n\n'
```

If **RS-Agent-Planning** is suggested:
```bash
printf '\nWhich repo should this issue go to?\n\n'
printf '  1) Claude-Project-Tooling\n'
printf '  2) \033[1;32mRS-Agent-Planning\033[0m  \033[32m← suggested\033[0m\n\n'
```

After running the printf command, output **only** a short prompt — do not re-echo the menu in text. The Bash output is already visible. Example follow-up: `Which? (1 or 2)`

Wait for the user to respond with 1 or 2. Use their choice as TARGETREPO.

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
| `Service: MCP` | Changes specific to the MCP server |
| `Epic` | Do not use — reserved for git-plan |

## Step 4 — Create the issue

Run:

```bash
python3 Claude-Project-Tooling/git-tools/interface/create_issue.py \
  --repo AndresI19/TARGETREPO \
  --title "TITLE" \
  --body "DESCRIPTION" \
  --label LABEL1 --label LABEL2
```

Omit `--label` flags if no labels apply. Print the issue URL when done.
