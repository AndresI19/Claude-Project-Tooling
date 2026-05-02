# /new-task

Pick the next task to work on, create its branch, and (for code tasks) enter plan mode with full issue context.

## Step 1 — Build the unified task list

**Always re-run this command at the start of every invocation. Never reuse JSON from a previous run, even within the same session.** Project board state can change between iterations from sources outside the current loop:
- The user may have closed an issue manually or moved its column
- A merged PR may have auto-closed the issue it `Closes`'d
- A previous `/work-flow` iteration may have moved an item to Verify or Done
- A `/todo` invocation may have added new Ready items

When invoked from `/work-flow`'s loop, treat each iteration as a brand-new state read — do not render the menu from in-context memory of a prior iteration's `ready_items.py` output.

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/ready_items.py --include-statuses="Verify,In Progress,Ready"
```

Parse the JSON. Each item has: `item_id`, `number`, `title`, `labels`, `url`, `status`.

**Render the menu as markdown in your text response — not via Bash printf.** Bash outputs over a few lines get auto-folded and the user has to expand them; markdown in your text response is always visible and supports hyperlinks.

Status is conveyed by an **emoji indicator** at the start of each row (no color column, no padding):
- `Verify` → 🟡
- `In Progress` → 🔵
- `Ready` → ⚪

The issue number is the link, rendered as a markdown hyperlink at the end of the line.

**Pagination**: show **20 items per page**. If more items remain, the line just above `0. Cancel` is `21. → List more (N remaining)` (numbering continues across pages, e.g. items 21–40 on page 2 keep numbers 21–40).

**Number formatting**: do NOT use a markdown ordered list (`1.`, `2.`, …) — its renderer doesn't pad single-digit numbers to align with double-digit ones, so emoji shift right at item 10+. Instead, render each row as a paragraph line with the number wrapped in backticks and **left-padded with one space when the total max number is two digits** (so ` 1.` aligns with `10.`). This puts all status emoji on the same column.

Format example (markdown in your text response):
```
**Pick a task** (page 1 of 3):

` 1.` 🟡 Add sanity tests for health and crash · [#27](https://github.com/AndresI19/RS-Agent-Planning/issues/27)
` 2.` 🔵 Implement search_wiki tool · [#11](https://github.com/AndresI19/RS-Agent-Planning/issues/11)
` 3.` ⚪ Implement get_player_stats tool · [#13](https://github.com/AndresI19/RS-Agent-Planning/issues/13)
` 4.` ⚪ Implement get_quest_info tool · [#14](https://github.com/AndresI19/RS-Agent-Planning/issues/14)
` 5.` ⚪ Add in-memory cache with per-tool TTLs · [#15](https://github.com/AndresI19/RS-Agent-Planning/issues/15)
` 6.` ⚪ Test all tools via mcp dev inspector · [#16](https://github.com/AndresI19/RS-Agent-Planning/issues/16)
`21.` → List more (N remaining)
` 0.` Cancel

Legend: 🟡 Verify · 🔵 In Progress · ⚪ Ready
```

Pad widths to whatever max is needed: 2 digits when the menu has 10–99 items, 3 digits for 100+. Single-digit-only menus need no padding.

Keep the `user-select.wav` sound on selection prompts (play via Bash before rendering the menu).

Ask: **"Which? (number, or 0 to cancel)"** — wait for the user.

If the user picks a **Verify** item, prompt:
> "This issue is in Verify. Open the PR / read the work and close the issue if approved, or pick another item."

Do not proceed past Step 1 for a Verify selection unless the user explicitly says to re-open the work.

## Step 2 — Infer target repo

RS-Agent-Planning holds **planning artifacts only** — never PRs (except those by `/todo`). Code work always happens in a code repo under `~/git-workspace/claude-workspace/`.

**Discover code repos** in the workspace:
```bash
find $HOME/git-workspace/claude-workspace -mindepth 2 -maxdepth 2 -name .git -type d 2>/dev/null \
  | xargs -n1 dirname | xargs -n1 basename | grep -v '^RS-Agent-Planning$'
```

**Inference rules**:
1. **`Service: <name>` labels** map deterministically: `Service: MCP` → `rs-mcp-server`. Convention: repo name is `rs-<name>` (lowercase). Future labels follow the same pattern.
2. **Generic code labels** (`Code` / `DevOps` / `Defect` without a `Service:` qualifier): infer from the issue body — file paths, repo names mentioned, or contextual clues. If unambiguous, proceed; if ambiguous, prompt the user with the discovered candidates as a numbered list.
3. **`Inquiry` / `Discovery` only** (no other code label): work on planning docs in `RS-Agent-Planning`. Print the caution banner below and skip Steps 3–4.

State the inferred repo to the user before proceeding so it can be redirected.

### Inquiry/Discovery caution

When the chosen issue routes to RS-Agent-Planning (planning docs only), print:
```
⚠ Inquiry/Discovery task — no branch will be created.
  Edits land on RS-Agent-Planning main and ride along with the next /record push.
```

Then jump to Step 5.

## Step 3 — Resume detection (code-bearing tasks only)

The branch naming convention bakes the issue number in (`-I<N>` suffix), so the branch itself is the resume key — no separate cache needed.

```bash
git -C $HOME/git-workspace/claude-workspace/<repo> fetch origin --quiet
git -C $HOME/git-workspace/claude-workspace/<repo> branch --all --format='%(refname:short)' \
  | grep -E "(^|/)[A-Za-z0-9-]+-I${ISSUE_NUMBER}$" \
  | head -1
```

- **Match found** → **Resume**:
  - Capture the branch name and any associated open PR:
    ```bash
    gh pr list --head <branch> --repo AndresI19/<repo> --json number,url
    ```
  - Switch to that branch: `git -C <repo> checkout <branch>` (handle pre-flight first if working tree is dirty — see Step 3b)
  - Skip Step 4 (no new branch creation)
- **No match** → continue to Step 3b, then Step 4

## Step 3b — Pre-flight: handle uncommitted changes

```bash
git -C <repo> status --short
git -C <repo> branch --show-current
```

**If working tree is clean and current branch is `main`** → skip to Step 4.

**Otherwise**, present this 4-option prompt:

```
The current branch (<branch>) has uncommitted changes:
  <git status output>

How should we proceed?
  1) Open a PR for these changes (invokes /pr, then continues on a new branch)
  2) Cancel — finish current work first
  3) Commit current changes and continue on this same branch (no new branch)
  4) Preserve current changes (commit OR stash) and start a new branch
```

- **Option 1** → invoke `/pr` skill → after PR succeeds, continue to Step 4
- **Option 2** → exit `/new-task` cleanly, do not move issue to In Progress
- **Option 3** → ask for a one-line commit message → `git -C <repo> commit -am "<msg>"` → skip Step 4 → continue to Step 5
- **Option 4** → sub-prompt: `(a) commit  (b) stash` → execute the chosen action, then continue to Step 4. If stash, remember to `git -C <repo> stash pop` after Step 4.

## Step 4 — Create the task branch

**Branch naming**: 2–3 word kebab-case descriptor of the issue + `-I<N>` suffix.
Examples: `server-refactoring-I19`, `endpoint-documentation-I20`, `fix-redis-timeout-I40`.

Print the proposed name. If a local branch with that exact name already exists (collision unrelated to resume), append `-2`, `-3`, etc.

Create off the latest `origin/main` in one shot — no intermediate `git checkout main`:
```bash
git -C <repo> fetch origin main --quiet
git -C <repo> checkout -b <branch-name> origin/main
```

If Step 3b chose Option 4 with stash → `git -C <repo> stash pop`.

## Step 5 — Move issue to In Progress

Skipped on resume (already In Progress).

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/set_status.py ITEM_ID "In Progress"
```

## Step 6 — Plan mode trigger (with full context kickoff)

- Labels include `Code` / `Service: MCP` / `DevOps` → **automatically call `EnterPlanMode`**
- Labels are only `Inquiry` / `Discovery` / docs → **ask the user**: "Enter plan mode for this task? (y/N)"

**On entering plan mode, immediately fetch issue context and print the kickoff block**:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/interface/issue_context.py NUMBER --repo AndresI19/RS-Agent-Planning
```

Print:
```
🧭 Plan mode for issue #N — <title>
   Issue:  [🔗](<url>)
   Branch: <branch-name>          (resumed from <last commit short sha> · PR #M open)
                                  — or — (fresh from origin/main)
   Repo:   <inferred repo>

📋 Recap
   <2–4 sentence summary of the issue body>

💬 Comments (most recent first)
   - @user (date): <first 200 chars of comment>
   - @user (date): <first 200 chars of comment>
```

For the resume status line, run `git -C <repo> log -1 --pretty='%h'` to get the short sha, and `gh pr list --head <branch> --json number` to detect any open PR.

**Once the user approves the plan, immediately call `ExitPlanMode` to begin implementation. Do not begin coding while still in plan mode.**

## Step 7 — Do the work

- `Code` / `Service: MCP` → implement the feature; write, test, verify
- `Inquiry` / `Discovery` → read planning docs, produce a concrete decision, write it up
- `DevOps` → implement the infrastructure or automation change
