---
name: refactor
description: Ground-up, behavior-preserving refactor of a SINGLE repo to the five quality goals — clear hierarchy, least duplicate code, hardcoded values parameterized, no dead code, optimization. Assumes the repo already has a test suite and uses it as the behavior-preservation oracle; rewrites in a scratch dir then overlays (never edits in place), runs a local gate plus an optional live-snapshot E2E, and ends at a STAGED (un-merged) PR. Reusable and iterative — safe to re-run for successive tightening passes against the same spec.
---

Refactor one repo from the ground up while preserving its observable behavior. The target repo is taken
from the skill argument, the current directory, or — if ambiguous — ask. This is deliberately
**iterative**: re-running it on the same repo tightens the code further against the same goal-spec, with
the repo's existing test suite guarding against regressions. It ends at a **staged PR**, never an
auto-merge.

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

---

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

## Step 4 — Rewrite from scratch in a scratch dir (never in place)

Build the complete new version in a sibling **`REPO.rewrite/`** directory, with the untouched original
beside it as live reference. Rewrite to the five goals, preserving behavior. Working in a scratch tree
keeps cross-file references coherent and makes the old→new switch atomic — there is never a half-rewritten
repo.

Calibrate the ambition to the code: a **well-structured** repo wants targeted dedup / dead-code / perf
passes, not a speculative architectural overhaul; a genuinely tangled module wants the structural rewrite.
Meet the goals; don't invent churn.

## Step 5 — Overlay atomically

Switch the repo to the new version as a mirror-with-deletions:

```bash
rsync -a --delete --exclude=.git --exclude=node_modules --exclude=.venv REPO.rewrite/ REPO/
```

Then reinstall deps in `REPO` (`npm ci` / venv reinstall) so the tree is buildable.

## Step 6 — Local gate: behavior preserved + goals met

Re-run the exact Step 1/Step 3 gate in `REPO`. It must **match the baseline**: the full existing suite
green (green against the rewrite = behavior preserved). Then walk the five goals as an explicit checklist
and confirm each is actually met — hierarchy, duplication, parameters, dead code, optimization. If a test
went red, the rewrite changed behavior: fix the rewrite (not the test) or abort. Fix lint before proceeding.

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
the conversation or a file list. **Stage it — do not merge.** Merging is a separate, user-gated step (for
the platform, a merge is a production deploy); if several repos are being refactored, merge them in a
planned order with a live re-verify after each.

## Step 9 — Iterate

This skill is re-runnable. A second pass reuses the Step 2 spec and the existing test suite as its oracle,
and tightens the code further against the same five goals. Each pass leaves the repo cleaner than it found
it, with behavior provably unchanged.
