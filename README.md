# Claude-Project-Tooling

Shared scripts, configuration, and tooling for the Claude Code workspace. Used by Claude to automate development workflows across projects.

## Structure

- **`git-tools/scripts/`** — Git workflow automation
  - `pr.py` — Creates pull requests; accepts metadata from Claude in-conversation and handles all git mechanics
  - `push_sessions.py` — Pushes changes in RS-Agent-Planning and Claude-Project-Tooling to origin/main in a single call
- **`claude/recording/`** — Supporting scripts for the `/record` skill
  - `session_detect.py` — Detects the current session log state (new, append, or ask)
  - `token_usage.py` — Calculates token usage across all Claude session files and outputs a markdown table
- **`New Boot/`** — New machine setup guide
- **`dev-workspace-versions.md`** — Installed tool and package versions tracker

## Skills

Claude skills that use this tooling live in `~/.claude/skills/` and are not checked in here. The scripts in this repo are the mechanical layer those skills delegate to.
