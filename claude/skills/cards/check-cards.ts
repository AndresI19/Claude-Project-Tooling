/**
 * Run the REAL strict-zod loader over cards/, then report what the deck now contains.
 *
 * This is the gate that matters: the same code path the server runs at module load, so anything
 * that passes here will not crash the server at boot. It also surfaces the things a plain parse
 * cannot — unknown labels, out-of-range answerIndex, and which quiz modes each card actually got.
 *
 * Copy into the repo root and run, then delete:
 *   cp <skill-dir>/check-cards.ts . && ./node_modules/.bin/tsx check-cards.ts; rm check-cards.ts
 *
 * Optional argument: a section letter to list in detail, e.g. `tsx check-cards.ts P`
 */
import { availableModes } from './src/client/quiz/capabilities.ts';
import { loadCardsPayload } from './src/shared/load-cards.ts';

const p = loadCardsPayload('./cards');
const focus = (process.argv[2] || '').toUpperCase();

console.log(`${p.cards.length} cards across ${Object.keys(p.cats).length} sections`);

const bySection: Record<string, number> = {};
for (const c of p.cards) bySection[c.cat] = (bySection[c.cat] ?? 0) + 1;
console.log(
  'sections:',
  Object.keys(p.cats)
    .map((k) => `${k}:${bySection[k]}`)
    .join(' '),
);
console.log('groups:  ', p.groups.map((g) => `${g.key}[${g.sections.join('')}]`).join(' '));

const labelTally: Record<string, number> = {};
for (const c of p.cards) for (const l of c.labels) labelTally[l] = (labelTally[l] ?? 0) + 1;
console.log('labels:  ', labelTally);

const unlabelled = p.cards.filter((c) => !c.labels.length);
if (unlabelled.length) console.log(`!! ${unlabelled.length} unlabelled: ${unlabelled.slice(0, 8).map((c) => c.id).join(' ')}`);

// A card with only the always-available identify mode is thin — usually a missing cloze or mcq.
const thin = p.cards.filter((c) => availableModes(c).length <= 1);
if (thin.length) console.log(`!! ${thin.length} card(s) with a single mode: ${thin.slice(0, 8).map((c) => c.id).join(' ')}`);

// fill placeholders must match blanks 1:1 with no repeated index, or slots bind wrongly.
for (const c of p.cards.filter((x) => x.fill)) {
  const idx = [...c.fill!.text.matchAll(/\{(\d+)\}/g)].map((m) => +m[1]);
  const dup = idx.length !== new Set(idx).size;
  const expected = c.fill!.blanks.map((_, i) => i).join(',');
  const got = idx.slice().sort((a, b) => a - b).join(',');
  if (dup || got !== expected) console.log(`!! ${c.id} fill placeholders [${idx}] vs ${c.fill!.blanks.length} blanks`);
  // A slot expands to ~104px against a 3-char {N}, shoving anything after it on the same line.
  // That only MATTERS when the following text is column-aligned, as in an ASCII diagram. The
  // legitimate exception is a config listing where the blank is the key — `{0}: nginx` — since
  // leading indentation is untouched and there is no column to break.
  const risky = c.fill!.text
    .split('\n')
    .filter((l) => /\{\d+\}/.test(l) && !l.trimEnd().endsWith('}') && !/\{\d+\}\s*:/.test(l));
  if (c.fill!.code && risky.length)
    console.log(`!! ${c.id} has ${risky.length} mid-line slot(s) with trailing text — check alignment`);
}

if (focus) {
  console.log(`\nsection ${focus}:`);
  for (const c of p.cards.filter((c) => c.cat === focus)) {
    console.log(`  ${c.id.padEnd(5)} ${c.topic.slice(0, 46).padEnd(48)} [${c.labels.join(',')}]  ${availableModes(c).join(',')}`);
  }
}
