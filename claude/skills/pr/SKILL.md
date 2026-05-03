---
name: pr
description: Create a pull request for the relevant git repo under ~/git-workspace/claude-workspace/. Claude generates branch name, commit message, and PR body in-conversation, then passes them to a Python script that handles all git mechanics. Shows branch transitions in blue.
---

Create a pull request for the relevant repository.

## Pre-flight — Confirm explicit user request

**Before doing anything**, verify the user explicitly asked for a PR in their most recent message.

Accepted triggers: the user typed `/pr`, `pr`, "open a PR", "create a PR", "make a PR", or a clear equivalent.

If Claude is running this as a proactive follow-on step, an end-of-task suggestion, or anything other than a direct user request — **stop immediately and do not proceed**. Offer to create the PR instead:

> "Want me to open a PR for this?"

Only continue to Step 1 if the user's request is unambiguous.

---

## Step 1 — Identify the repo and gather context

From conversation context, determine which single repo under `$HOME/git-workspace/claude-workspace/` has the changes. Use that path as REPO.

Run in one command to get the diff context:
```bash
git -C REPO fetch origin && git -C REPO diff origin/main --stat && git -C REPO status --short && git -C REPO log origin/main..HEAD --oneline
```

## Step 2 — Run pre-PR checks

Before generating PR metadata, validate that the repo's lint and test checks pass — catches regressions locally before they reach CI.

**Discovery**: if `<REPO>/CLAUDE.md` exists and contains a `## Pre-PR checks` heading, extract the FIRST fenced ```bash``` block under that heading. Each non-blank, non-comment line of that block is one shell command.

**Execution**: from REPO as the working directory, run the commands in order via the Bash tool — chain with `&&` so the first non-zero exit halts the rest.

**On failure**: stop and report the failing command plus its output. Do **not** proceed to Step 3. The user fixes the issue, then re-invokes `/pr`.

**No checks defined**: if `<REPO>/CLAUDE.md` is missing, or the section is absent, skip silently and proceed. Repos opt in by adding the section — useful for trivial repos where lint/test setup isn't worth the overhead.

## Step 3 — Generate PR metadata

Based on the diff output, produce a JSON object with exactly these fields:
- `branch_name`: kebab-case, max 3 words, describes what changed
- `commit_message`: imperative mood, max 72 chars
- `pr_title`: max 70 chars, same intent as commit_message
- `pr_body`: plain prose, max 4 sentences, no bullet points. Describe the goal the change achieves — never list file paths, enumerate individual scripts, or echo the user's request. Avoid self-evident framing like "Replaces X with Y" or "Updates X to include Y" — lead with the substance. File locations and what changed are visible in the diff; the body should convey intent and why.
- `labels`: array of label strings to apply. Choose from the available labels below — multiple can apply.

### Linking issues in PR body

If this PR has an associated GitHub issue, the issue reference must be the very first line of `pr_body`, followed by a `---` divider and a blank line before the prose:

- Use `Closes ORG/REPO#N` when the merge fully resolves the issue with no further verification or follow-up required — GitHub auto-closes it on merge.
- Use `ORG/REPO#N` (bare reference) when the PR relates to an issue but does not fully close it.

`ORG` is the GitHub organization or account name (personal accounts are treated the same as orgs). Always use the full `ORG/REPO#N` form — never a bare `#N`, which silently resolves only within the PR's own repo and will target the wrong issue or nothing when the issue lives elsewhere.

```
Closes ORG/REPO#42

---

The rest of the body here...
```

Multiple issues stack on separate lines before the divider — mix `Closes ORG/REPO#N` and bare `ORG/REPO#N` as appropriate.

Do **not** use `Closes ORG/REPO#N` unless the merge fully resolves the issue with no further verification or follow-up remaining.

When a `Closes` clause is present, issues must **not** be closed via `gh issue close` — the merge handles it. Only use `gh issue close` directly for issues with no associated PR.

**Available labels:**
- `Trivial` — small, low-risk change
- `Non-Trivial` — needs a scan through, largely harmless
- `Complex` — requires focused review
- `Integrated` — touches core structure, likely to break without human review
- `System` — changes to OS, containerization, or automation
- `Documentation` — includes documentation updates
- `Fix` — bug fix or correction
- `Enhancement` — new feature or capability

## Step 4 — Run the script

Pass the JSON as a single-quoted string to `--meta`:

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/scripts/pr.py \
  --repo REPO \
  --meta 'JSON_HERE'
```

The script handles everything from here: sync state check, stash-only-if-needed, branch creation, commit, push, and PR creation.

## Step 5 — Interpret output

On success the script prints the PR URL and a numbered list of open PRs with the new one in blue.

Errors are labelled — if any appear:
- `ERROR: command failed (exit N)` → read CMD/STDOUT/STDERR and fix the underlying issue
- `ERROR: --meta is invalid` → fix the JSON shape and rerun
