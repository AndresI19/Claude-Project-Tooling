---
name: shot
description: Capture a headless-browser screenshot of a URL — the whole viewport, the full scrollable page, or one element's bounding box — for visual verification of a deployed or local web page. Supports mobile emulation, seeding a platform identity, and clicking a panel/tab open before the shot. Use whenever a change needs an actual visual check instead of hand-writing CDP glue.
---

Take a screenshot with the reusable tool instead of writing a one-off browser script.

## When to use

Any time you would otherwise hand-write a headless-Chromium + DevTools-protocol script to look at a
page: verifying a deployed change on `andres.project-platform.me`, checking a locally-served build,
confirming a component renders, comparing desktop vs mobile. If you just need the DOM/text, prefer
`curl`; use this when the *rendered pixels* are what matter.

## Run it

```bash
node "$HOME/git-workspace/claude-workspace/Claude-Project-Tooling/claude/tools/shot.mjs" \
  --url <URL> --out <PATH.png> [options]
```

Then **Read the output PNG** to inspect it.

### Options

| Flag | Effect |
| --- | --- |
| `--url <url>` | page to load (required) |
| `--out <path>` | PNG output path (required) |
| `--selector <css>` | clip to this element's bounding box (else the viewport) |
| `--width <px>` / `--height <px>` | viewport size (default 1460×1200) |
| `--mobile` | emulate a 390px phone (scale 2, touch) |
| `--identity <val>` | seed `localStorage['platform:identity']` before load: `guest`, `user`, `admin`, or a raw JSON string |
| `--click <css[,css]>` | click these selectors in order before capturing (open a panel, switch a tab) |
| `--eval <js>` | run JS in the page before capturing |
| `--wait <ms>` | settle time after load and each action (default 4000) |
| `--full` | capture the full scrollable page (ignored with `--selector`) |

### Examples

Verify a deployed component, clipped to it:
```bash
node .../shot.mjs --url https://andres.project-platform.me/ --out /tmp/tile.png --selector '.feat-banner'
```

Open the architecture panel, switch to the second diagram, clip to it (the exact flow that used to be
a hand-written script):
```bash
node .../shot.mjs --url https://andres.project-platform.me/ --out /tmp/auth.png \
  --identity guest --click '[data-act=architecture]' \
  --eval "document.querySelectorAll('.arch-tab')[1].click()" --selector '.arch-slider'
```

Mobile view of a tile:
```bash
node .../shot.mjs --url https://andres.project-platform.me/ --out /tmp/m.png --mobile --selector '.feat'
```

## Output

Prints `wrote <path> (WxH)` on success, or a `ERROR: ...` line to stderr. A missing `--selector`
target, an unreachable page, or a browser that never starts each produce a labelled error. After a
successful run, Read the PNG to actually look at it.
