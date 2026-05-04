"""Single source of truth for the GitHub Project status emojis.

Used by /new-task, /triage, /git-plan, and any future skill that surfaces
statuses. Keep this in lockstep with the STATUS_* constants in project.py
and the actual option names on the GitHub Project board.

The lifecycle gradient (deferred → blocked → available → active → review →
complete) is intentional — the colors carry semantic information at a glance.
"""

STATUS_EMOJI = {
    "Backlog":     "⚫",
    "Todo":        "🟠",
    "Ready":       "⚪",
    "In Progress": "🔵",
    "Verify":      "🟡",
    "Done":        "🟢",
}


def emoji_for(status: str) -> str:
    """Return the emoji for a status name, or empty string if unknown."""
    return STATUS_EMOJI.get(status, "")


def legend(separator: str = " · ") -> str:
    """Return a one-line legend like '⚫ Backlog · 🟠 Todo · ⚪ Ready · …'."""
    return separator.join(f"{e} {n}" for n, e in STATUS_EMOJI.items())
