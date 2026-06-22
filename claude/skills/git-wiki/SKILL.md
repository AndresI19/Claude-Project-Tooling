---
name: git-wiki
description: Overhaul a git project's README into a tight three-section landing page — a two-sentence description, an auto-detected capability table, and run/connect instructions — and migrate all deeper documentation into a succinct multi-page GitHub wiki. Works generically across project types (MCP server, CLI, HTTP API, library).
---

Restructure a project's documentation: the README becomes a fast landing page with exactly three
sections, and everything deeper moves into a succinct, multi-page GitHub wiki. The target repo is
taken from the skill argument, the current directory, or — if ambiguous — ask the user.

## Step 1 — Identify the target repo

Resolve two values:
- `REPO` — the local path of a git repo under `$HOME/git-workspace/claude-workspace/`.
- `OWNERREPO` — its GitHub `owner/repo`: `gh repo view "$REPO" --json nameWithOwner -q .nameWithOwner`.

Confirm it has a GitHub remote. If the cwd isn't a single obvious repo, ask which one.

## Step 2 — Inventory the current docs

- Read `README.md` and list its section headings.
- Find other doc files: `docs/**/*.md`, plus top-level `*.md` **except `CLAUDE.md`** (agent guidance
  stays in-repo) and `CHANGELOG.md` (keep in-repo). `CONTRIBUTING.md` and design docs migrate.
- Classify each README section: **KEEP** (it maps to one of the three target sections below) vs
  **MIGRATE** (everything else — setup, build, CI, architecture, security, etc.).

## Step 3 — Detect the primary interface (drives Section 2)

The capability table adapts to what the project actually exposes. Pick the first match:

| Signal in the repo | Interface | Section 2 lists |
|--------------------|-----------|-----------------|
| MCP SDK dep, `@mcp.tool` / `@instrument` / tool registration in a server module | **Tools** | each tool + a one-line description |
| `argparse` / `click` / `typer` / `cobra`, `console_scripts`, a `bin/` dir | **Commands** | each subcommand + description |
| FastAPI / Flask / Express routes, an OpenAPI spec | **Endpoints** | `METHOD /path` + description |
| A packaged library with public exports | **API** | the main functions/classes + description |
| none of the above | **Features** | notable capabilities |

Build the table **from source** (decorated functions, route definitions, CLI parsers) — not from the
old README, which is often stale. One concise line per entry. Confirm the detected interface and the
entries with the user if the project type is ambiguous.

## Step 4 — Decide wiki handling (ask each run)

Check availability: `gh repo view "$OWNERREPO" --json hasWikiEnabled -q .hasWikiEnabled`.

Use `AskUserQuestion` to confirm how to handle the wiki this run:
- **Enabled** → default option "Migrate deeper docs to the wiki."
- **Disabled** → offer: *Enable + bootstrap* (`gh` enables it, then the bootstrap below) · *Keep docs
  in repo* (skip migration; leave deeper docs in a `docs/` folder) · *Cancel*.

If migrating, verify the wiki is **initialized**: `git ls-remote https://github.com/$OWNERREPO.wiki.git`.
GitHub doesn't create the `.wiki.git` repo until the first page exists. If this returns *"Repository
not found"*, ask the user to create one page via the repo's **Wiki tab** in the web UI (a one-time
bootstrap), then continue once it resolves.

## Step 5 — Rewrite the README to three sections

1. **Title + description** — `# <repo>` followed by a two-sentence description (what it is, what it
   serves/does). No heading; this is the intro.
2. **`## <Tools|Commands|Endpoints|API|Features>`** — the Step 3 table.
3. **`## Run & connect`** (or `## Usage`) — how to start/install/run, any port or env knobs, and the
   client/usage config (config JSON, install command, example invocation). Keep it copy-pasteable.

If migrating, end with a one-line pointer: `**Full documentation** → the [project wiki](<wiki URL>).`
Move every other section out. The result is exactly these three logical sections.

## Step 6 — Build the wiki pages (succinct, multi-page)

Only if migrating. **Derive** pages from the migrated content — do not hardcode a page list; group
related sections into short pages. Common pages (include those that apply):

| Page | Content |
|------|---------|
| `Home` | index/TOC linking every page + a one-line intro and a link back to the README |
| `Development` | install, local run, prerequisites |
| `Container-and-Deployment` | build, lifecycle, ports, endpoints |
| `Security` | hardening, threat model, secrets |
| `Testing-and-CI` | test commands, CI jobs |
| `Architecture` | layout, design notes |

Keep each page short. Cross-link with `[Title](Page-Name)` (wiki filenames use hyphens for spaces;
`Home` is the index). Write the pages into a **staging directory** (e.g. a temp dir under the
workspace) — one `.md` file per page.

## Step 7 — Publish the wiki

```bash
python3 $HOME/git-workspace/claude-workspace/Claude-Project-Tooling/git-tools/scripts/push_wiki.py \
  --repo "$OWNERREPO" --pages-dir "$STAGINGDIR" --message "Migrate docs into the wiki"
```

The script clones the wiki, copies the staged pages in, commits, and pushes `master` via GitPython —
the hook-safe path for the wiki's protected branch. If it reports *"Repository not found"*, the Step 4
bootstrap was skipped; resolve and re-run.

## Step 8 — Repoint references and delete migrated files

- `git rm` the migrated doc files (e.g. `docs/*.md`).
- Repoint any in-repo links to them — in the README, `CLAUDE.md`, and code comments — to the wiki URLs
  (`https://github.com/$OWNERREPO/wiki/<Page>`; append `#anchor` for a heading).
- `grep -rn '<removed path>'` to confirm no dangling references remain.

## Step 9 — Verify

- Run the repo's pre-PR checks if defined: extract the first ```bash``` block under a `## Pre-PR checks`
  heading in the repo's `CLAUDE.md` (same discovery the `/pr` skill uses) and run it; it must pass.
- Confirm the README has exactly the three sections and no dangling doc links.
- If the change touched runtime behavior (e.g. a new port/env knob in Section 3), exercise it.

## Step 10 — Open a PR (explicit approval only)

The repo changes (README, deleted docs, link updates, any code) are a normal PR. Per the workspace
rule, **do not** open a PR unless the user explicitly asks. Ask: *"Want me to open a PR for this?"* —
on an explicit yes, invoke `/pr`. The wiki is already published (wikis have no PR), so it needs no
further action.
