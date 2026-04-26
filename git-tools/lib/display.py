#!/usr/bin/env python3
"""
display.py — Shared ANSI terminal rendering helpers.
"""
import re

RESET = "\033[0m"
BOLD  = "\033[1m"
BLUE  = "\033[34m"
GREEN = "\033[32m"
DIM   = "\033[2m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def ansi_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"


def ansi_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"


def visible_len(s):
    return len(_ANSI_RE.sub("", s))


def ljust_visible(s, width):
    pad = width - visible_len(s)
    return s + (" " * max(pad, 0))


def color_label(name, color_map):
    """Render a colored label badge. color_map: {name_lower: {bg: (r,g,b), fg: (r,g,b)}}"""
    style = color_map.get(name.lower())
    if not style:
        return f" {name} "
    return f"{ansi_bg(*style['bg'])}{ansi_fg(*style['fg'])} {name} {RESET}"
