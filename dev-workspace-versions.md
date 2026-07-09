![Dev Workspace](dev-workspace-thumbnail.svg)

# ⚙ Dev Workspace — Installed Versions

> **Machine:** fedora · Fedora Linux 43 Workstation
> **Date:** 2026-06-29
> **Package Manager:** Homebrew 5.1.9

---

## Tools

| Tool | Version |
|------|---------|
| **Git** | 2.53.0 |
| **Python** | 3.14.4 |
| **Pip** | 26.0.1 |
| **Node** | 25.9.0 |
| **npm** | 11.12.1 |
| **Java** | OpenJDK 25.0.2 (Homebrew) |
| **Go** | 1.26.4 (Homebrew) |
| **Docker** | 29.4.0 |
| **docker-buildx** | 0.33.0 (Homebrew; symlinked into `~/.docker/cli-plugins/`) |
| **kubectl** | v1.35.4 (Kustomize v5.7.1) |
| **Colima** | 0.10.1 |
| **Glow** | 2.1.2 |
| **Brave Browser** | 147.1.89.137 (dnf) |
| **VS Code** | 1.116.0 (dnf) |
| **Mermaid CLI** | 11.12.0 (npm) |
| **GNOME Tweaks** | 49.0 (dnf) |

---

## Notes

- All tools installed via **Homebrew** (`/home/linuxbrew/.linuxbrew`)
- **Docker** requires **Colima** as the container runtime on Linux
  ```
  colima start       # start the Docker daemon
  colima stop        # stop it
  colima status      # check status
  ```
- To update all tools at once:
  ```
  brew update && brew upgrade
  ```

---

## Markdown Viewer

This file is best viewed with **Glow** (installed via Homebrew):

```
glow ~/Desktop/dev-workspace-versions.md
```
