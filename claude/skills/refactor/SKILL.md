---
name: refactor
description: Ground-up, behavior-preserving refactor of a SINGLE repo to the five quality goals — clear hierarchy, least duplicate code, hardcoded values parameterized, no dead code, optimization (plus stale-comment/doc accuracy). Runs SEVERAL themed passes in ONE invocation (naming → dedup → control-flow → optimization → idioms/types → an adversarial verification closer), each its own commit, with the repo's existing test suite as the behavior oracle and before/after metrics as evidence. Edits in place for targeted passes; scratch-dir + overlay only for a genuine structural rewrite. Gates each pass against the FULL CI (formatter --check + a build, not just lint+test), optionally live-snapshot-E2E-verifies deployed components, and ends at a STAGED (un-merged) PR. Starts with a budget/scale gate so a large multi-repo fan-out isn't launched without session headroom. Reusable and iterative.
---

Refactor one repo from the ground up while preserving its observable behavior. The target repo is taken
from the skill argument, the current directory, or — if ambiguous — ask. This is deliberately
**iterative by construction**: a single invocation makes **several themed passes** over the code (Step 4),
each committing on top of the last, so one run reaches the depth that an ad-hoc "refactor this" reaches
only after being asked over and over. Re-running later tightens further still. Throughout, the repo's
existing test suite guards against regressions, and it ends at a **staged PR**, never an auto-merge.

**Assumption: the repo already has a test suite.** This skill treats those tests as the behavior oracle —
it does not author a characterization net from scratch. If a rewrite would touch logic the suite genuinely
doesn't cover, that's a gap to flag to the user, not a reason to block the pass.

## The five refactoring goals (the contract — every pass must meet these)

1. **Clear hierarchy** — modules/functions organized by responsibility; obvious where each thing lives.
2. **Least duplicate code** — one source of truth; fold twin implementations, centralize shared logic.
3. **Hardcoded values → parameters** — magic numbers/strings/paths become named constants, config, or env.
4. **No dead code** — remove unused exports, unreachable branches, orphaned files, stale tables/flags.
5. **Optimization** — remove needless work (recompute, re-render, N+1, redundant IO) without changing behavior.

**Non-negotiable overlay on all five: behavior is preserved.** The refactor is a rewrite of *how*, never
*what*. The goal-spec (Step 2) and the existing test suite (Step 3) are what prove that.

**Comments and docs count as the artifact too.** A comment, README, or CLAUDE.md claim the *current* code
contradicts is a defect — fix it against the code you can see (docs drift as code evolves; verify, don't
trust). Tighten verbose prose while you are there — cut lines and words — but keep the *fact* of every
bug-preventing "why" (an ordering rule, an inode/caching gotcha). Never preserve a lie because it was
there before, and never delete a load-bearing warning to save a line.

---

## Pre-flight — Budget & scale gate (a refactor is expensive; size it before you start)

A full six-lens pass is not cheap, and a fan-out multiplies it: the last **6-repo × 4-pass** run burned
~2.4M subagent tokens — roughly **half a session's usage**. Estimate the cost and confirm the budget
BEFORE launching, or you strand the work half-done when the session limit hits mid-run.

- **Size the run.** One repo, six lenses ≈ one unit; N repos in a workflow ≈ N units. Multi-repo fan-outs
  are the expensive shape.
- **Surface it and ask — do not assume.** There is no reliable bash query for remaining session usage; it
  lives in the interactive **`/usage`** dialog. So state the estimate and ask the user to read `/usage`,
  then confirm explicitly: *"This run is roughly `<estimate>` (the last N-repo pass took ~half a session);
  how much do you have left — proceed, or scope it down?"* Never launch a large fan-out on a guess.
- **When run via a Workflow, gate on the real budget** rather than guessing: read the `budget` global and
  stop spawning passes once it drops below a per-pass reserve —
  `while (budget.total && budget.remaining() > RESERVE) { …next pass… }` — so the run degrades gracefully
  instead of dying mid-pass.
- **If budget is tight, scope down — don't abort blindly.** Fewer repos, or the four build lenses now and
  optimization + verification on a later run. Each pass is a committed checkpoint, so a partial run is
  still a clean, mergeable improvement.

## Step 0 — Isolate if concurrent

If another Claude session is active (SessionStart said so, or `.claude/sessions/` has another fresh
marker), call **`EnterWorktree`** (no args) before any write, and run the whole skill from that worktree.
Solo → work in place. This is the workspace's standard concurrent-agent isolation.

## Step 1 — Identify the repo and establish the baseline is green

Resolve `REPO` — one git repo under `$HOME/git-workspace/claude-workspace/`. Confirm a clean working tree
(`git -C REPO status --short`) and note the current branch/HEAD. Then **prove the repo is green as-is**:
run its lint + test gate (discover via the repo's `CLAUDE.md` `## Pre-PR checks` block, else
`package.json` scripts / `Makefile` / `pyproject.toml`). Record the exact pass counts — this is the
baseline every later step must match. If it's already red, stop and report; you can't refactor on a broken
base.

Also snapshot a cheap **before-metrics** baseline the PR will report against: source LOC, a duplication
signal, cyclomatic complexity if a tool is handy, and — for a deployed component — built image size and
test-suite wall-time. Re-measure at the end (Step 8): a refactor that moved nothing measurable, or made a
number worse, is one to reconsider.

For a **deployed platform component**, also capture the live rollback anchor now (see Step 7): the
component's own `helm history <comp> -n platform` top revision and live `/version`.

## Step 2 — Goal-spec: CLAUDE.md written FROM THE ORIGINAL

The refactor must satisfy a spec derived from the *original*, not one backfilled to the new code.

- If `REPO/CLAUDE.md` already exists and describes goals/behavior/pitfalls/decisions, treat it as the spec
  (refresh anything stale against the current code).
- If it's missing or thin, **read the original code and write it**: what the repo is for, its public
  surface (tools/commands/endpoints/exports), the invariants and edge cases it honors, known pitfalls, and
  the decisions that must not regress. Do this **before** touching any logic.

This file is the contract: after the rewrite, every claim in it must still hold.

## Step 3 — Baseline the existing test suite (the behavior oracle)

The repo's existing tests are the behavior contract — the rewrite is correct exactly when they stay green.
Locate the suite, confirm the full run passes on the ORIGINAL, and record the exact pass count as the
baseline. Skim it to understand which behaviors are pinned (computations, state machines, timers,
formatting, security/deny paths, edge cases) so the rewrite keeps those exact contracts.

- If, while rewriting, you find behavior-critical logic the suite genuinely doesn't cover, **flag the gap
  to the user** rather than silently trusting the rewrite there — do not treat it as a blocker, and do not
  turn this into a test-authoring effort.
- If the rewrite relocates or adds any test files, honor the layout: a **top-level `test/` dir, never
  co-located in `src/`** (keeps a Dockerfile `COPY src` clean so tests never ship); include glob `test/**`;
  `test/` and `**/*.test.*` in `.dockerignore`; add `test` to a tsconfig `include` ONLY if the build
  doesn't `tsc` (vite builds are safe; a `tsc` build must keep its build tsconfig at `include:[src]`).

## Step 4 — The refactor: several themed passes, not one glance

The failure this step exists to prevent: fixing the first thing you see and declaring victory. A real
refactor makes **multiple passes, each with a different lens**, because one lens is blind to what another
catches. **Default to five build passes, then a mandatory verification pass** — the shape that
consistently exhausts *and re-checks* a well-kept repo. Each pass builds on the code the previous pass
left, and each is **its own commit on the same branch**, so the PR carries one commit per pass.

Run these lenses in order; each still serves the five goals but **leads with its theme** so the passes stay
distinct. The first five build; the sixth audits.

1. **Naming & consistency** — intention-revealing identifiers; consistent casing, terminology, and
   ordering of imports/members; drop obscuring abbreviations. Fold in the comment/doc accuracy sweep above.
2. **Duplication & single-source** — fold twin logic into one helper; lift repeated literals into named
   constants/config. Do NOT cross a package/submodule boundary (see Guardrails).
3. **Control flow & complexity** — early returns / guard clauses over nesting; simplify conditionals;
   split over-long functions into named steps; flatten needless indirection.
4. **Optimization** — the goal-5 lens the others are blind to: cut *needless work* without changing
   behavior — hoist/memoize recomputation, kill N+1 access and redundant IO/allocation, make eager work
   lazy, drop re-renders/re-measurements. If you can't prove the new form is equivalent, don't make it.
5. **Idioms, dead code, types & polish** — idiomatic language constructs; remove dead code / unused
   exports / unreachable branches; **tighten types** (narrow wide types, kill `any`/escape hatches, make
   illegal states unrepresentable — discriminated unions, `readonly`); final formatting sweep.
6. **Verification (adversarial closer)** — the one pass that builds nothing. Re-read the *whole* accumulated
   diff with skeptical, fresh eyes trying to **disprove** that behavior was preserved, scrutinizing hardest
   the code the test suite does NOT cover (the coverage gaps you flagged). Fix any regression it surfaces;
   ideally it finds none. It may end without a commit — but it must RUN, every time. The other five are
   optimistic builders; this is the skeptic that keeps them honest.

After **each build pass**, run the Step 6 gate and commit only if it is green — a red pass changed behavior,
so fix or drop that change before moving on. Do genuine work every pass; if a lens finds little, look harder
before settling — but never fabricate churn or touch behavior.

**Where to work.** For the targeted passes a well-structured repo actually wants, edit **in place** — the
test suite is your net and the per-pass commits are your atomic history. Reserve the sibling
**`REPO.rewrite/` scratch-dir + rsync overlay** (Step 5) only for the rare module that needs a genuine
from-scratch structural rewrite, where a half-rewritten tree would be incoherent. Calibrate to the code:
meet the goals, don't invent an architectural overhaul a clean repo doesn't need.

## Step 5 — Overlay atomically (only if Step 4 used a scratch rewrite)

Skip this for the in-place themed passes — those are already committed on the branch. Only when a module
was rebuilt in `REPO.rewrite/`, switch the repo to the new version as a mirror-with-deletions:

```bash
rsync -a --delete --exclude=.git --exclude=node_modules --exclude=.venv REPO.rewrite/ REPO/
```

Then reinstall deps in `REPO` (`npm ci` / venv reinstall) so the tree is buildable.

## Step 6 — The gate after each pass: behavior preserved + goals met

Re-run the gate in `REPO` after **each** pass. It must **match the baseline**: the full existing suite
green against the rewrite is the proof behavior is preserved. Walk the five goals as a checklist. If a test
went red, the change altered behavior: fix the change (not the test) or drop it.

**The local gate must be the CI gate, not a subset of it.** A green `lint`+`test` is *not* a green CI — the
checks that only run in CI are exactly the ones a local pass forgets. Discover the repo's real checks
(`.github/workflows/`) and run their local equivalents before trusting a pass:
- the **formatter in `--check` mode** (`ruff format --check` / `biome format` / `gofmt -l`) — distinct from
  the linter, and the single most common miss (a green `ruff`/`biome check` can still fail `format --check`);
- a **build of the artifact** where feasible (`tsc`, `docker build`) — it catches an import or type break
  the test env hides (a slim runtime image may lack a dev dep the tests had).

When a CI check is red, **read the actual log** to sort refactor-caused from pre-existing: a *build* break
or a *format/lint* failure is yours to fix; a **Trivy / dependency CVE scan** on an unchanged base image or
lockfile is pre-existing (identical on `main`) and is not something a behavior-preserving refactor
introduced — note it, don't chase it. (`#18 DONE` in a docker-build log means the build passed and the red
is the scan after it.)

## Step 7 — Live snapshot verify (deployed components only)

Skip for repos that don't deploy to the live platform. For those that do, prove integration "as it used to
work" **before** the PR, without touching `main`/tags/released images:

The platform is **six Helm releases** — `platform-infra` plus one per service — so a snapshot touches
only the component you are refactoring. Its siblings are untouched by construction.

1. Record the component's own top revision: `helm history <comp> -n platform` (your rollback target).
2. Build the working-tree image as `platform-<comp>:<snap>`, then **side-load it into the node**:
   ```bash
   tar=$(mktemp -t snap-XXXX.tar) && docker save "platform-<comp>:<snap>" -o "$tar"
   minikube cp "$tar" /home/docker/img.tar
   minikube ssh -- "docker load -i /home/docker/img.tar && rm -f /home/docker/img.tar"
   minikube ssh -- "docker image inspect platform-<comp>:<snap> >/dev/null" || echo "NOT in the node"
   ```
   **Not `minikube image load`** — it silently no-ops when the tag is already in the node and still
   exits 0, so the cluster goes on running the old code while every step reports success. `k8s/deploy.sh`
   avoids it for exactly this reason; do the same here.
3. Deploy the snapshot onto that component's release — its own repo's values, in full, plus the local
   image:
   ```bash
   helm upgrade <comp> <ws>/platform-orchestration/charts/service -n platform \
     -f <the repo that ships <comp>>/deploy/<comp>.values.yaml \
     --set image.repo=platform-<comp> --set image.tag=<snap> --set version=<snap> \
     --wait --force-conflicts
   ```
   `image.repo` is set explicitly because this deploys the **side-loaded local** image, not the
   registry one CI deploys. `--wait` is right here and deliberately unlike CI: you want the rollout
   finished before the oracle runs, and there is no runner queue to free.
4. Run the E2E oracle from `platform-e2e/`:
   `PLAYWRIGHT_BROWSERS_PATH=<ws>/.pw-browsers npx playwright test`. It must be fully green.
5. `helm rollback <comp> <recorded-rev> -n platform --force-conflicts` to return the public site to
   released code — that restores the registry image CI deployed. Log the event + result in
   `REFACTOR-LEDGER.md`.

## Step 8 — Stage the PR (explicit approval only)

Per the workspace rule, **do not open a PR unless the user explicitly asks.** Prepare the branch and a
clean commit, then ask: *"Refactor is green — want me to stage the PR?"* On an explicit yes, invoke `/pr`.
The PR body describes the *artifact* (what the refactored code does and the concrete improvements), never
the conversation or a file list. Include the before→after metric deltas from Step 1 (LOC, duplication,
complexity, image size, test runtime) so the improvement reads as evidence, not adjectives. **Stage it — do not merge.** Merging is a separate, user-gated step (for
the platform, a merge is a production deploy); if several repos are being refactored, merge them in a
planned order with a live re-verify after each.

## Guardrails (learned across the platform repos)

- **A red baseline is a finding, not a nuisance.** If Step 1 is red, STOP — a repo whose `main` lint job
  has quietly failed for weeks (while independent release jobs keep deploying) is hiding a broken CI. Fix
  or flag the baseline first; you cannot prove behavior-preservation on a broken base.
- **Branch off `origin/main` fresh.** The local checkout is routinely behind — a clean working tree with a
  fat `git diff origin/main` is the tell. `git fetch && git checkout -B <branch> origin/main`.
- **Stage only what you edited** (explicit `git add`, never `-A`) — don't sweep in submodule-pointer,
  lockfile, or `.env` drift.
- **Respect DELIBERATE duplication.** If a comment documents *why* two similar things are kept separate (a
  test-monkeypatch locality, an intentional split), leave it — unifying it is churn or a behavior change.
- **Don't cross a package/submodule boundary.** Folding shared code into a vendored design system is a
  separate, coordinated change (plus a submodule-pointer bump in the consumer), not an in-repo refactor.
- **No-test-oracle repos** (shell / YAML / Helm): the oracle is `bash -n` + shellcheck + `helm template`
  **byte-stability** + a YAML parse. Limit to mechanically-safe changes (naming, dedup, dead flags) — no
  control-flow rewrites without a render/parse proof, and mind shell quoting (a stray `'` inside a
  single-quoted `bash -c` breaks it).
- **Leave behavior-adjacent strings alone** — tool-output guide strings, user-facing copy asserted in
  tests: they read like prose but they are behavior.
- **Flag coverage gaps.** Behavior-critical logic the suite doesn't pin (large generated markup, DOM
  wiring) — say so; don't silently trust the rewrite there, and don't turn the pass into a test-authoring
  effort.

## Step 9 — Iterate

One invocation already runs the themed loop (Step 4). Re-running the whole skill later is still valuable —
a fresh baseline and a fresh eye catch what the last run's momentum passed over. Each run reuses the Step 2
spec and the test suite as its oracle and leaves the repo cleaner, behavior provably unchanged.
