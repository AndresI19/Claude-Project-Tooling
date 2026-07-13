---
name: platform-logins
description: List the identities registered with platform-auth — usernames, which are admins, and when each was last seen — read from platform-db in the running cluster. Use when the user asks which accounts exist or which username is theirs. It shows NO codes: codes are stored one-way and cannot be recovered.
---

List the platform-auth identities from the running cluster.

## When to use

The user asks "which accounts exist", "which username did I sign up as", "which one is my admin", or
wants an overview of who has registered. It answers the *account* question, not the *credential* one.

## The hard limit — say it plainly

This tool shows **no codes, ever.** The auth service stores each code only as `HMAC-SHA256(pepper,
code)` in `code_lookup`; the code itself is never kept in a readable form — not for a regular user,
not for an admin (`AUTH_ADMINS` is a list of usernames, not codes). **A forgotten code cannot be
recovered, only reset.** If the user needs to get back into an account whose code is lost, the answer
is a code reset (a separate action that writes a new hash), or re-signing-up — not this tool.

## Run it

```bash
python3 "$HOME/git-workspace/claude-workspace/platform-orchestration/k8s/logins.py"
python3 "$HOME/git-workspace/claude-workspace/platform-orchestration/k8s/logins.py" --json
```

## Output

A table, newest login first: `USERNAME`, an `ADMIN` star (★ when the username is in the live
`AUTH_ADMINS`), `CREATED`, `LAST SEEN`, and the `ID` (the JWT `sub`). It ends with a count and a
reminder that codes are not shown. `--json` gives the same data machine-readable.

It reads the `identities` table via `psql` inside the `platform-db` pod and the admin list from the
live `platform-auth` secret, repointing the kubeconfig first. Errors are `ERROR: ...` lines — most
often a cluster that is down. Read-only: it never writes and never prints credential material.
