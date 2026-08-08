---
name: cards
description: Author, edit and verify quiz cards in data-driven-quiz-server (cards/*.yaml). Covers the style contract that keeps cards consistent, the YAML and schema traps that crash the server at boot, and the verification loop that must run before committing. Use whenever adding a card, adding a section, or reviewing card changes.
---

Write cards that teach, then prove they load and render before committing.

The deck is data-driven: a YAML file per section, validated by strict zod at **module load**, which means
a bad card takes down the whole server rather than breaking one request. Most of this skill exists
because that failure is cheap to cause and expensive to discover.

Field mechanics live in `cards/_schema.md` — read it for what a field *does*. This skill is what
`_schema.md` deliberately is not: what makes a card good, what silently breaks, and how to check.

---

## Step 1 — Check coverage before writing anything

The most common defect is not a bad card, it is a **redundant** one — or worse, a term the deck already
uses as a distractor but never defines.

```bash
cd data-driven-quiz-server
grep -ril 'your-term' cards/[a-z]-*.yaml
```

Read the hits before deciding. Three outcomes:

- **Already taught** → do not duplicate. Extend the existing card instead.
- **Mentioned only as an `mc` distractor or an mcq option** → this is a real gap and a slightly
  embarrassing one: the deck offers it as a wrong answer without ever explaining it. Pub/sub, SSR and
  "Pub/sub vs point-to-point" were all found this way.
- **Adjacent but different angle** → write it, and say in the desc how it differs. A comparison card
  (`REST vs gRPC vs GraphQL`) does not cover mechanism (`how a gRPC connection works`).

Deliberately skipping a near-duplicate is a decision worth stating in the commit message.

---

## Step 2 — The style contract

Derived from the original deck; hold it so new cards are indistinguishable from old ones.

**One idea per card.** `topic` is the thing being tested. If the topic needs "and", consider two cards.

**`desc` states the answer.** It is the answer body, not a hint and not a teaser. Lead with the
conclusion, then the mechanism.

**`extras` use a fixed label vocabulary.** Do not invent new labels casually; each earns its place:

| Label | Contains |
|---|---|
| `e.g.` | A concrete, **named** real example — Stripe, SQS, WhatsApp, Oban. Never "a large company". |
| `Say` | The line to speak in an interview, in curly quotes “…”. First person, spoken register. |
| `Trap` | The specific mistake people make, and why it is wrong. Not a generic caution. |
| `Threshold` | The number at which a decision flips. Use where a card is about scale. |
| `Mitigation` | What you actually do about it. Use on failure-mode cards. |
| `Contrast` | The neighbouring concept this is confused with. |

**mcq prompts are scenarios, never definitions.** This is the single strongest style rule in the deck.

- Bad: *"What is SKIP LOCKED?"*
- Good: *"Ten workers poll the same jobs table with SELECT ... FOR UPDATE, and throughput is identical
  to running one worker. What is the most likely cause?"*

The scenario form tests recognition in the shape the knowledge is actually needed.

**Distractors must be plausible and same-category.** Wrong answers should be things a reasonable person
might believe, drawn from the same domain. A distractor nobody would pick teaches nothing.

**Derive numbers, do not assert them.** `1,200 posts/sec × 200 followers = 240,000 writes/sec` beats
"fan-out is expensive". The arithmetic is the teaching.

**Cloze answers are single distinctive terms.** If the blank could be filled three ways, rewrite it or
add `alts`.

---

## Step 3 — Placement

**Sections partition, labels cut across.** A card lives in exactly one lettered section and carries any
number of labels from `cards/_labels.yaml`. Put mechanism cards where their mechanism lives, not where
their application lives.

**Card IDs are positional** (`A1`, `A2`, …) and users' favourites and notes are keyed by ID in
localStorage. **Append to the end of a section. Never insert or reorder** — it silently rebinds
everyone's saved state. Inserting a card mid-file also shifts every later card's checklist indices.

**A label not declared in `_labels.yaml` is a hard error.** Add the label to the registry first.

New section? Add the file as `<letter>-<name>.yaml`, and add the key to a group in `_groups.yaml` —
every section should belong to exactly one group.

---

## Step 4 — The traps that actually bite

These are empirical. Each one has cost real debugging time.

**A plain YAML scalar cannot contain `": "` anywhere**, including continuation lines of a wrapped
string. `Derive it: 1,200 posts/sec` reparses as a mapping and the file fails to load. Quote the whole
scalar. This is by far the most frequent failure — run `scan-colons.py` (in this skill's directory)
rather than hunting by eye.

**Bare numbers in lists and tables parse as integers**, and the schema wants strings. `- 400` fails;
`- "400"` passes. Bites `mcq.options` and `table` rows most.

**Unknown or misspelled field = server boot crash.** The schema is `.strict()`. There is no warning
tier.

**`fill` drop-slots are `min-width: 104px`** — about 13 monospace characters replacing a 3-character
`{0}`. Any text *after* a placeholder on the same line is shoved right. In an ASCII diagram that
destroys the column alignment the reader depends on, so **put every `{N}` at end-of-line**, in an
aligned column. Existing code-fill passages sit at 23–35 chars for this reason.

  The legitimate exception is a **config listing where the blank is the key** — `{0}: nginx` in a
  Kubernetes manifest. Leading indentation is untouched and there is no column to break, so it reads
  fine. `check-cards.ts` allows that shape and flags the rest.

**Print cards are 416×272px.** Content overflows and clips beyond roughly +50px; the deck median
overflow is about +43px. Dense tables plus four extras will exceed it. Measure rather than guess
(Step 5).

**ASCII in a `code` block should stay ≤ 45 chars wide** to survive the print card. Deck median is 54,
max 81, but anything a learner must read *in full* to answer needs to fit.

**`_schema.md` has been stale before** — `mcq` and `order` went undocumented for a long time.
`src/shared/card-schema.ts` is the real contract.

---

## Step 5 — Modes: what unlocks what

A card's available modes are derived from its fields (`src/client/quiz/capabilities.ts`), not declared:

| Field | Mode |
|---|---|
| `cloze` | fill-in |
| `mcq` | multiple choice (its own prompt + options) |
| `match` | line matching — also auto-derived from a **2-column** table with ≥3 rows |
| `multi` | select-all; distractors pool from *other* cards' `multi` lists |
| `order` | put-in-order |
| `fill` | drag labels into blanks (`code: true` → monospace passage) |
| `code` | read-the-code; distractors from `mc` |
| `categorize` | sort a pool into columns |

**Only `cw` (from `code`) shows content BEFORE asking.** `renderMQ` renders the prompt text alone, and
the prompt is HTML-escaped and collapses newlines. So:

- To show a diagram and then ask about it → `code` with an ASCII diagram, or `fill` with `code: true`.
- A `diagram:` SVG renders in the **answer body**, so it is invisible while the question is posed.
- A multi-line mcq prompt will collapse to one line. Use a single-line arrow chain instead.

Aim for 2–3 modes per card. One is thin; five makes the card repeat itself in rotation.

---

## Step 6 — The verification loop

Run all of it. Every step here has caught a real defect.

```bash
cd data-driven-quiz-server

# 1. Colon-scalar sweep on the files you touched
python3 <skill-dir>/scan-colons.py cards/x-your-deck.yaml

# 2. The real strict-zod loader — catches type errors and unknown labels
cp <skill-dir>/check-cards.ts . && ./node_modules/.bin/tsx check-cards.ts; rm check-cards.ts

# 3. The full CI gate — never skip lint, it fails on formatting alone
npm test && npm run lint && npm run typecheck
```

Then **look at it**. A card that loads can still render wrong:

```bash
PORT=3111 npm start &          # print.html is built at startup from the same payload
node ~/git-workspace/claude-workspace/Claude-Project-Tooling/claude/tools/shot.mjs \
  --url http://127.0.0.1:3111/print.html --out /tmp/card.png --wait 2500 \
  --eval "const c=[...document.querySelectorAll('.card.back')].find(e=>e.textContent.includes('UNIQUE PHRASE')); if(c) c.id='tgt';" \
  --selector '#tgt'
```

For an interactive mode (`fill`, `cw`), the print sheet will not show it — build the client
(`npm run build`) and inject the mode's markup against the real stylesheet, or drive the app.

**Measure overflow** when a card is table-heavy or has a long code block — the eval in Step 5 of the
verification loop above can be adapted to report `scrollHeight - clientHeight` per `.card.back`.

---

## Step 7 — Deploying to the running quiz

Merging to main deploys the **image**, not the decks. Cards in the cluster are mounted from a
PersistentVolume, seeded once with `cp -rn`, which never overwrites. A card change reaches the running
quiz only via the `platform-content` skill plus a rollout restart.

**Ordering matters**: a card using a NEW schema field must ship its code/image *first*. Pushing such a
card to the volume ahead of the image crashes the running server at boot (strict zod).
