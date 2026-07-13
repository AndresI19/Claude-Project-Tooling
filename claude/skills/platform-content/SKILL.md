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
bash "$HOME/git-workspace/claude-workspace/platform-orchestration/k8s/pv-content.sh" <command>
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

It brings up a throwaway `pv-writer` pod that mounts the same PVC read-write (the volume is mounted
read-only into the real pods, so it cannot be written through them), copies the file in, tears the
pod down, then **rolls the consuming deployment** — required because a replaced single file gets a new
inode and the old subPath bind-mount would keep serving the old one. The script repoints the
kubeconfig first (Colima/minikube forwarded-port quirk), so no manual setup is needed.

## Output

Prints the copied file's listing and the rollout status, ending in `done`. Errors are `ERROR: ...`
lines — a missing file, a wrong extension (résumé must be `.pdf`), or a cluster that is down.
