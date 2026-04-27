# /new-task

Query the active GitHub project for Ready items and guide the user to pick one to work on.

## Step 1 — Fetch Ready items

Run:

```bash
python3 Claude-Project-Tooling/git-tools/interface/ready_items.py
```

Parse the JSON. Each item has: `item_id`, `number`, `title`, `labels`, `url`, `status`.

If the list is empty, print:

```
No items are currently marked Ready.
Check the project board to see if items need to be unblocked first.
```

Then stop.

## Step 2 — Present the options

Display a numbered list of the Ready items. Column order: index, title, labels, issue number. Always append 0) Cancel as the last option.

Example format:
```
Ready to work on:

  1)  Resolve stack decisions             [Inquiry]          #6
  2)  Resolve infrastructure decisions    [Inquiry, DevOps]  #7
  0)  Cancel
```

Ask: **"Which would you like to work on? (enter a number)"**

Wait for the user to respond. If they enter 0 or "cancel", stop immediately.

## Step 3 — Show issue context and confirm start

Run:

```bash
gh issue view NUMBER --repo AndresI19/RS-Agent-Planning
```

Display the full issue body, then ask: **"Move this to In Progress?"**

If yes:

```bash
python3 Claude-Project-Tooling/git-tools/interface/set_status.py ITEM_ID "In Progress"
```

After confirming the status change, briefly suggest what starting looks like based on labels:

- `Code` / `Service: MCP` → create a feature branch and open relevant files
- `Inquiry` / `Discovery` → read the planning docs and capture a decision
- `DevOps` → review the infrastructure docs
