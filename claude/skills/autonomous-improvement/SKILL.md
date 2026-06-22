---
name: autonomous-improvement
description: Run an autonomous, token-bounded code-quality pass on a repository — audit for duplication, latent bugs, scalability, and dependency bloat, then loop (fix → test → gate) committing at breakpoints while preserving behavior, until a token threshold is reached, then open a PR. Refactors and hardens existing code; never adds features or tools.
---

Run a self-driving quality pass over a repo's existing code: make it more succinct, readable, and
scalable, fix latent bugs, and trim the dependency tree — **without changing observable behavior and
without adding features**. The loop is bounded by a token budget and gated by the repo's own tests.

## Operating contract
- **One dedicated branch** off `main`; work only there.
- **Behavior is preserved.** Existing tests stay green; every fix adds or extends a test.
- **No new features or tools** — only refactor, fix, harden, optimize.
- **Commit + push only at clean breakpoints** (all gates green).
- **Stop and PR when ~5% of the context budget remains** (or the backlog is exhausted).
- Run **autonomously** — surface only genuine blockers or behavior-changing ambiguities.

## Step 1 — Baseline and branch
- Discover the repo's lint + unit gate (the first ```bash``` block under `## Pre-PR checks` in its
  `CLAUDE.md`, same as `/pr`). Run it. **If the baseline is red, stop and report** — never start from
  a broken state.
- Create the working branch off `origin/main`. Seed a task backlog.

## Step 2 — Audit (fan-out)
Launch parallel Explore agents over the codebase, each with a distinct lens:
- duplication / refactor / hierarchy,
- latent bugs, fragility, edge cases (malformed inputs, unhandled `None`, brittle parsing),
- scalability / HTTP / resource use (retries, pooling, unbounded caches, blocking calls),
- tests + infra + dependency tree.

Synthesize findings (with `file:line`) into a **prioritized backlog**: highest-ROI / lowest-risk
first (e.g. extract duplicated helpers into a shared module), then bug fixes, then scalability, then
readability/annotation polish, then dependency/infra.

## Step 3 — The fix loop (repeat per backlog item)
1. Make the **smallest surgical change** that preserves behavior.
2. **Lock it with a test.** For a bug, write a **fail-first adversarial test** — feed the malformed or
   edge input that "breaks the tool", confirm it fails, then fix until green. This is how "breaking
   the tools to see how they improve" stays safe: every break becomes a regression test.
3. Run the **lint + unit gate**. It must stay green before moving on. Mark the task done.

## Step 4 — Breakpoints (commit + push)
At each completed workstream or coherent group of fixes:
- Run the **integration/e2e suite** (e.g. a live-server smoke/FVT tier). Tool outputs must be
  unchanged from baseline.
- Commit with a clear, scoped message and push the branch.

## Step 5 — Dependencies (only if in scope)
- Audit declared dependencies against actual imports; **remove unused** ones.
- Prefer the **standard library** over adding a dependency when it removes fragility (e.g. an HTML
  parser over brittle regex); adopt a new library only when it clearly nets positive.
- Re-lock the dependency file and confirm the security/scan gate (e.g. Trivy) stays green.

## Step 6 — Stop and PR
When ~5% of the context budget remains (or the backlog is exhausted): run the **full gate**, push the
final commit, and open a PR whose body summarizes what landed, the behavior-preservation evidence
(tests green, outputs unchanged), and what remains for a future pass. Per the workspace rule, opening
the PR is the one step that needs explicit user intent — confirm before invoking `/pr`.

## Guardrails
- Never weaken, skip, or delete a test to make the gate pass.
- Keep every commit coherent and revertible — one workstream or theme per commit.
- If a change would alter observable behavior, stop and ask rather than guessing.
