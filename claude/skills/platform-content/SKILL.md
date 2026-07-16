---
name: platform-content
description: Replace files on the platform's shared PersistentVolume (the résumé served at /resume.pdf, and the quiz card decks) without an image rebuild. Use when the user wants to swap in a new résumé PDF or edit/replace card decks on the running cluster.
---

Replace content on the `platform-content` PersistentVolume in the running cluster.

## When to use

The user wants to update a file that is mounted from the volume rather than baked into an image —
most often **a new résumé** (`/resume.pdf` on the home page), or **card decks** for the quiz. These
live on the PVC precisely so they can change without a rebuild.

Do NOT use this for code or manifests — those go through a normal build/deploy.

## Run it

```bash
bash "$HOME/git-workspace/claude-workspace/platform-ops/pv-content.sh" <command>
```

Commands:

| Command | Effect |
| --- | --- |
| `ls` | list what is on the volume (the résumé, and the card decks under `cards/`) |
| `set-resume <local.pdf>` | replace `/resume.pdf`, then roll `home` so it is served |
| `set-cards <dir \| one.yaml>` | copy a deck directory or a single deck onto the volume, then roll `quiz` |

### Examples

```bash
bash .../pv-content.sh ls
bash .../pv-content.sh set-resume ~/Documents/resume-2026.pdf
bash .../pv-content.sh set-cards ~/git-workspace/claude-workspace/data-driven-quiz-server/cards
```

## How it works (so nothing surprises you)

It brings up a throwaway `pv-writer` pod that mounts the same PVC read-write, copies the file in, and
tears the pod down. The script repoints the kubeconfig first (Colima/minikube forwarded-port quirk), so
no manual setup is needed.

**`set-cards` rolls the quiz; `set-resume` rolls nothing.** The quiz builds its decks once at startup,
so a new deck on the volume changes nothing until that pod restarts — and note a malformed deck fails
the quiz's *next* boot, not the copy. The résumé needs no roll: home reads it per request from the
volume's directory mount, so the next request already serves the new file.

(The résumé used to need a roll, and the reason is worth keeping: it arrived as a subPath single-file
mount, which is a bind mount pinned to the file's inode at container start. A replaced file has a new
inode and the mount kept serving the old one. home now reads the directory mount, which resolves by
name on every lookup.)

## There is an HTTP path too

home serves an admin-only `PUT /api/content/<path>` for the same volume — no kubectl, no pod:

```bash
curl -X PUT https://andres.project-platform.me/api/content/resume.pdf \
     -H "Authorization: Bearer <admin token>" \
     -H 'Content-Type: application/pdf' --data-binary @resume.pdf
```

Prefer it for routine swaps. It accepts only `resume.pdf` and `cards/<name>.yaml` (an allowlist —
`platform-version.json` and anything else are refused), and writes atomically. This script remains the
escape hatch: it works when home is broken, unbuilt or mid-rollout, and it is the only way to reach
paths the allowlist refuses.

## Output

Prints the copied file's listing and, for `set-cards`, the rollout status — ending in `done`. Errors are
`ERROR: ...` lines — a missing file, a wrong extension (résumé must be `.pdf`), or a cluster that is down.
