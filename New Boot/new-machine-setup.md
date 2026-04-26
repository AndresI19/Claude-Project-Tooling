# 🖥 New Machine Setup — Fedora Workstation

> Based on the setup of `fedora` (Fedora Linux 43 Workstation) — 2026-04-19
> Reproduces the full dev environment including Claude Code, Homebrew tools,
> browsers, desktop shortcuts, and session tracking.

---

## 1. Prerequisites

Update all system packages before installing anything:
```bash
sudo dnf update --refresh
```

Then confirm your user has sudo access and the following are available:
```bash
sudo -v           # confirm sudo works
curl --version
flatpak --version
```

---

## 2. Install Claude Code

Claude Code is the AI-powered CLI. Install it via npm (Node required — install Homebrew first
if Node isn't available, then come back to this step).

```bash
# Install Claude Code globally
npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

Log in with your Anthropic account on first run:
```bash
claude
```

---

## 3. Install Homebrew

Homebrew is the primary package manager for dev tools on this machine.

```bash
# Install (do NOT use sudo — it prompts internally)
NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add to PATH (add this to ~/.bashrc or ~/.zshrc too)
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# Verify
brew --version
```

Add to shell profile so it persists:
```bash
echo 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"' >> ~/.bashrc
source ~/.bashrc
```

---

## 4. Install Dev Tools via Homebrew

```bash
# Core dev tools
brew install git python node openjdk kubectl

# Link Java so system can find it
brew link --force openjdk

# Container tools
brew install docker colima

# Markdown viewer
brew install glow

# Verify all versions
git --version
python3 --version && pip3 --version
node --version && npm --version
java --version
docker --version
kubectl version --client
colima version
glow --version
```

---

## 5. Install Brave Browser

```bash
# Add Brave RPM repo
sudo dnf config-manager addrepo \
  --from-repofile=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo

# Install
sudo dnf install -y brave-browser

# Verify
brave-browser --version
```

---

## 6. Install VS Code

```bash
# Import Microsoft GPG key
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc

# Write the repo file
printf '[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc\n' \
  | sudo tee /etc/yum.repos.d/vscode.repo

# Install
sudo dnf install -y code

# Verify
code --version
```

---

## 7. Enable GNOME Desktop Icons & Tweaks

Desktop icons are off by default on GNOME. Enable via Extension Manager:

```bash
# Install Extension Manager (Flatpak)
flatpak install flathub com.mattjakeman.ExtensionManager

# Install GNOME Tweaks
sudo dnf install -y gnome-tweaks
```

Then open **Extension Manager** → search for **Desktop Icons NG** → install and enable.

Open **GNOME Tweaks** → **Window Titlebars** → enable **Minimize** button so window minimize controls appear on all windows.

---

## 8. Desktop Shortcuts

```bash
# Brave Browser
cp /usr/share/applications/brave-browser.desktop ~/Desktop/
chmod +x ~/Desktop/brave-browser.desktop

# VS Code
cp /usr/share/applications/code.desktop ~/Desktop/
chmod +x ~/Desktop/code.desktop

# Terminal (Ptyxis)
cp /usr/share/applications/org.gnome.Ptyxis.desktop ~/Desktop/
chmod +x ~/Desktop/org.gnome.Ptyxis.desktop

# Calculator
cp /usr/share/applications/org.gnome.Calculator.desktop ~/Desktop/
chmod +x ~/Desktop/org.gnome.Calculator.desktop

# GNOME Tweaks
cp /usr/share/applications/org.gnome.tweaks.desktop ~/Desktop/
chmod +x ~/Desktop/org.gnome.tweaks.desktop
```

GNOME may prompt **"Allow Launching"** on first click — approve it.

---

## 9. Set Glow as Default Markdown Viewer

```bash
# Create desktop entry for glow
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/glow.desktop << 'EOF'
[Desktop Entry]
Name=Glow
Comment=Markdown Reader
Exec=bash -c 'eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)" && glow "$1"; read -p "Press Enter to close..."' -- %F
Terminal=true
Type=Application
MimeType=text/markdown;text/x-markdown;
Icon=text-x-readme
Categories=Utility;TextEditor;
EOF

# Register as default
xdg-mime default glow.desktop text/markdown
xdg-mime default glow.desktop text/x-markdown
```

---

## 10. Git Workspace Folder + Shortcut

```bash
# Create folder structure
mkdir -p ~/git-workspace/claude-workspace/planning

# Create desktop shortcut
printf '[Desktop Entry]\nName=Git Workspace\nComment=Git Projects\nExec=nautilus /home/YOUR_USERNAME/git-workspace\nIcon=folder-development\nTerminal=false\nType=Application\n' \
  > ~/Desktop/git-workspace.desktop

chmod +x ~/Desktop/git-workspace.desktop
```

> Replace `YOUR_USERNAME` with your actual username (e.g. `andresirarragorri`).

The workspace structure:
```
~/git-workspace/
└── claude-workspace/
    └── planning/
```

To clone a repo into git-workspace (requires GitHub auth):
```bash
cd ~/git-workspace
git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git   # SSH (recommended)
# or
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git  # HTTPS (prompts for credentials)
```

> **Note:** HTTPS cloning requires interactive credential input — use SSH keys for a smoother experience. Heredoc (`<< 'EOF'`) syntax does not work with the Claude Code `!` prefix; use `printf` instead.

---

## 11. Claude Sessions Folder

```bash
mkdir -p ~/Desktop/Claude\ Sessions
```

---

## 12. Claude Code Session Skills

Create these two slash commands for session tracking. Replace `YOUR_USERNAME` as needed.

**`~/.claude/commands/sess-add.md`** — creates a new session file:
```
Create a new Claude session summary file in ~/git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions/.

Steps:
1. Run `date +"%Y-%m-%d %H:%M"` to get the current date and time.
2. Name the file `YYYY-MM-DD-HH:MM.md` using that date/time.
3. Write a session summary in this format:
   - `# Claude Session — YYYY-MM-DD HH:MM` as the title
   - `## Summary` — a concise paragraph of what was accomplished this session
   - `## Terminal Commands` — all bash commands run during the session in a single fenced code block with inline comments
   - `## Files Created` — a markdown table of files created or modified (path + description)
   - `## Notes` — any important reminders or follow-up items
4. Save the file to `~/git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions/YYYY-MM-DD-HH:MM.md`.
5. Update ~/git-workspace/claude-workspace/Claude-Project-Tooling/dev-workspace-versions.md with any applications installed or updated during
   this session, including their version numbers. Add or update rows; do not remove existing entries.
```

**`~/.claude/commands/sess-append.md`** — appends to the latest session file:
```
Append a new section to the most recently modified session file in ~/git-workspace/claude-workspace/RS-Agent-Planning/Claude Sessions/.

Steps:
1. Run `ls -t ~/Desktop/Claude\ Sessions/*.md | head -1` to find the most recent file.
2. Read the existing file to understand what was already logged.
3. Append a new `## Post-Summary Additions` section covering everything done since last written.
   - Include all new terminal commands in a fenced code block with inline comments
   - Include any new files created or modified in a table
   - Keep the same tone and format as the rest of the file
4. Do not modify anything above the appended section.
5. Update ~/git-workspace/claude-workspace/Claude-Project-Tooling/dev-workspace-versions.md with any apps installed or updated this session.
```

---

## 13. Dev Workspace Versions Reference Card

Create `~/git-workspace/claude-workspace/Claude-Project-Tooling/dev-workspace-versions.md` using the template below, then run each
version command to fill in the current values:

```bash
git --version
python3 --version
pip3 --version
node --version && npm --version
java --version
docker --version
kubectl version --client
colima version
brew --version
glow --version
brave-browser --version
code --version
claude --version
```

Template:
```markdown
# ⚙ Dev Workspace — Installed Versions

> **Machine:** hostname · OS name
> **Date:** YYYY-MM-DD
> **Package Manager:** Homebrew X.X.X

## Tools

| Tool | Version |
|------|---------|
| **Git** | ... |
| **Python** | ... |
| **Pip** | ... |
| **Node** | ... |
| **npm** | ... |
| **Java** | ... |
| **Docker** | ... |
| **kubectl** | ... |
| **Colima** | ... |
| **Glow** | ... |
| **Brave Browser** | ... |
| **VS Code** | ... |
| **Claude Code** | ... |
```

---

## Post-Install Checklist

- [ ] `colima start` — start Docker daemon before using Docker
- [ ] Enable **Desktop Icons NG** in Extension Manager
- [ ] Click each desktop shortcut once and approve "Allow Launching"
- [ ] Set wallpaper: copy from `/usr/share/backgrounds/fedora-workstation/` to `~/Pictures/`
      then set via **Settings → Background**
- [ ] Run `source ~/.bashrc` to reload shell with Homebrew in PATH
- [ ] Log in to Brave and sync bookmarks
- [ ] Log in to VS Code and sync settings/extensions
- [ ] If desktop icons appear cut off at the bottom, open **Extension Manager → Desktop Icons NG → Settings** and adjust the icon start position or margins

---

## 14. Claude Workspace Profile

Set up a scoped Claude profile inside `~/git-workspace/claude-workspace/` that enforces
forks-only git workflow, secrets checking on every commit, and a sandboxed permission scope.

```bash
mkdir -p ~/git-workspace/claude-workspace/.claude/hooks
```

**`~/git-workspace/claude-workspace/CLAUDE.md`** — create with these rules:
- `dangerouslySkipPermissions` is scoped strictly to this directory — no path traversal outside it
- Only work within forks named after the authenticated git user
- All commits are intercepted by a secrets check hook; never use `--no-verify`

**`~/git-workspace/claude-workspace/.claude/settings.json`**:
```json
{
  "dangerouslySkipPermissions": true,
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/home/YOUR_USERNAME/git-workspace/claude-workspace/.claude/hooks/secrets-check.sh"
          }
        ]
      }
    ]
  }
}
```

**`~/git-workspace/claude-workspace/.claude/hooks/secrets-check.sh`** — intercepts
`git commit` commands and scans staged diffs for:
- AWS Access/Secret keys
- Private keys (RSA, EC, DSA, OpenSSH)
- Google API keys, GitHub tokens, Slack tokens
- Generic secrets, passwords, and hardcoded `.env` values

Blocks the commit (exit 2) if any are found. Make it executable:
```bash
chmod +x ~/git-workspace/claude-workspace/.claude/hooks/secrets-check.sh
```

> Replace `YOUR_USERNAME` with your actual username.

---

## Keeping Tools Updated

```bash
# Homebrew tools
brew update && brew upgrade

# DNF tools (Brave, VS Code)
sudo dnf upgrade brave-browser code

# Claude Code
npm update -g @anthropic-ai/claude-code
```
