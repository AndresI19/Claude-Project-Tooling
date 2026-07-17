#!/usr/bin/env node
// shots.mjs — manifest-driven visual baselines: capture a set of screenshots, and fail when they change.
//
// WHY THIS EXISTS. The platform's three front-ends have zero layout test coverage, and that is not an
// oversight — it is structural. All three test under happy-dom, which has no layout engine, so
// getBoundingClientRect returns zeros and geometry CANNOT be asserted there. Every layout bug the
// platform has shipped was therefore invisible to CI by construction: a garden with a quarter of itself
// unreachable, a diagram whose labels render at 3px, a table clipped instead of scrolled. A rendered
// screenshot is the only artefact that can see any of them.
//
// This is deliberately NOT a general visual-regression framework. It is a list of views, a folder of
// PNGs, and a diff.
//
// Usage:
//   node shots.mjs --manifest <file> --update        # write/refresh the baselines
//   node shots.mjs --manifest <file> --check         # compare; non-zero exit on any change
//   node shots.mjs --manifest <file> --check --only garden-mobile
//
// Options:
//   --manifest <file>    JSON describing the shots                          (required)
//   --update | --check   what to do                                         (required, one of)
//   --base-url <url>     override the manifest's baseUrl (e.g. a local preview)
//   --only <name>        just this one shot
//   --tolerance <n>      default fraction of pixels allowed to differ       (default 0.001)
//
// Manifest shape — paths are relative to the manifest's own directory:
//   {
//     "baseUrl": "http://localhost:3000",
//     "dir": "test/shots",
//     "shots": [
//       { "name": "garden-mobile", "path": "/garden", "selector": ".boardwrap",
//         "mobile": true, "identity": "user" },
//       { "name": "arch-cicd", "path": "/", "mobile": true, "identity": "guest",
//         "click": "[data-act=architecture]",
//         "eval": "document.querySelectorAll('.arch-tab')[1].click()",
//         "selector": ".arch-slider", "tolerance": 0.005 }
//     ]
//   }
//
// Every key besides name/path maps straight onto a shot.mjs flag — this file owns no browser logic. It
// SPAWNS shot.mjs rather than importing it, so there is exactly one place that knows how to drive a
// browser, and a fix there (a leaked process, a guessed port) is a fix here for free.

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOT = join(HERE, 'shot.mjs');

const fail = (msg) => { console.error(`ERROR: ${msg}`); process.exit(1); };

// ---- args -------------------------------------------------------------------
const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i++) {
  if (!argv[i].startsWith('--')) continue;
  const key = argv[i].slice(2);
  opt[key] = new Set(['update', 'check']).has(key) ? true : argv[++i];
}
if (!opt.manifest) fail('--manifest is required. See the header for the shape.');
if (!opt.update && !opt.check) fail('pass --update (write baselines) or --check (compare against them).');
if (opt.update && opt.check) fail('--update and --check are opposites; pass one.');

const manifestPath = resolve(opt.manifest);
if (!existsSync(manifestPath)) fail(`no manifest at ${manifestPath}`);
let manifest;
try {
  manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
} catch (e) {
  fail(`manifest is not valid JSON: ${e.message}`);
}
const root = dirname(manifestPath);
const baseUrl = String(opt['base-url'] || manifest.baseUrl || '').replace(/\/+$/, '');
if (!baseUrl) fail('no baseUrl: put one in the manifest or pass --base-url');
const dir = resolve(root, manifest.dir || 'shots');
const defaultTolerance = Number(opt.tolerance ?? 0.001);
const shots = (manifest.shots || []).filter((s) => !opt.only || s.name === opt.only);
if (!shots.length) fail(opt.only ? `no shot named ${opt.only}` : 'the manifest lists no shots');

// ---- capture ----------------------------------------------------------------
/** One shot, via shot.mjs. Returns the PNG path, or throws with shot.mjs's own error text. */
function capture(shot, out) {
  const args = ['--url', `${baseUrl}${shot.path ?? '/'}`, '--out', out];
  // Reduced motion is the DEFAULT here, opt-out rather than opt-in: a baseline of a view that moves on
  // its own is not a baseline. Set "reduced-motion": false on a shot that is specifically about motion.
  if (shot['reduced-motion'] !== false) args.push('--reduced-motion');
  for (const k of ['selector', 'identity', 'click', 'eval', 'wait', 'width', 'height']) {
    if (shot[k] !== undefined) args.push(`--${k}`, String(shot[k]));
  }
  for (const k of ['mobile', 'full', 'reduced-motion']) if (shot[k]) args.push(`--${k}`);
  const r = spawnSync('node', [SHOT, ...args], { encoding: 'utf8' });
  if (r.status !== 0) {
    throw new Error((r.stderr || r.stdout || `shot.mjs exited ${r.status}`).trim().split('\n').pop());
  }
  return out;
}

const size = (png) => {
  const b = readFileSync(png);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
};

/**
 * Differing pixels between two PNGs, via ImageMagick.
 *
 * A size change is reported as its own thing rather than as a pixel count, and that is the point: for
 * the bugs this exists to catch, the SIZE is the symptom. A diagram that collapsed from 1720px tall to
 * 217px, a board that stopped overflowing — those are size changes, and a pixel metric on mismatched
 * dimensions is either an error or a meaningless number.
 */
function compare(a, b, diffOut) {
  const sa = size(a);
  const sb = size(b);
  if (sa.w !== sb.w || sa.h !== sb.h) {
    return { changed: true, why: `size ${sa.w}x${sa.h} -> ${sb.w}x${sb.h}` };
  }
  // -metric AE counts absolute differing pixels; -fuzz absorbs antialiasing noise. compare exits 1 when
  // the images differ, which is not an error here — it is the answer.
  const r = spawnSync('compare', ['-metric', 'AE', '-fuzz', '1%', a, b, diffOut], { encoding: 'utf8' });
  if (r.error) return { changed: true, why: 'ImageMagick `compare` not found — install it to diff' };

  // PARSE THE PARENTHESISED COUNT, and do not get clever.
  //
  // ImageMagick 7 Q16 reports AE as "<count*65535> (<count>)" — e.g. `65535 (1)` for one differing
  // pixel; other builds print a bare "<count>". The first number is the count scaled by the quantum
  // range, so dividing by 65535 would be wrong on a Q8 build. Verified against deliberate 1/100/900-px
  // diffs on 7.1.1-47 Q16-HDRI.
  //
  // This is worth a comment because the naive parse — strip everything that is not a digit or a dot —
  // silently turns "1.38672e+08" into "1.3867208" by eating the exponent. That yields ~1 differing
  // pixel for a diff of 2116, which is under every sane tolerance, so the checker reports `ok` for any
  // change at all. A regression net that always passes is worse than none: it is a green light nobody
  // re-examines. It shipped that way for exactly one test run.
  const err = (r.stderr || '').trim();
  const paren = err.match(/\(([\d.eE+-]+)\)\s*$/);
  const n = Number(paren ? paren[1] : err.split(/\s+/)[0]);
  if (!Number.isFinite(n)) return { changed: true, why: `could not read compare's output: "${err}"` };
  const total = sa.w * sa.h;
  return { changed: false, pixels: n, total, ratio: total ? n / total : 0 };
}

// ---- go ---------------------------------------------------------------------
mkdirSync(dir, { recursive: true });
const tmp = join('/tmp', `shots-${process.pid}`);
mkdirSync(tmp, { recursive: true });

let failed = 0;
let updated = 0;
console.log(`${opt.update ? 'updating' : 'checking'} ${shots.length} shot(s) against ${baseUrl}`);

for (const shot of shots) {
  if (!shot.name) fail('every shot needs a "name"');
  const baseline = join(dir, `${shot.name}.png`);
  const label = shot.name.padEnd(28);

  if (opt.update) {
    try {
      capture(shot, baseline);
      const { w, h } = size(baseline);
      console.log(`  ${label} baseline ${w}x${h}`);
      updated++;
    } catch (e) {
      console.error(`  ${label} FAILED: ${e.message}`);
      failed++;
    }
    continue;
  }

  // --check
  if (!existsSync(baseline)) {
    console.error(`  ${label} NO BASELINE — run --update first`);
    failed++;
    continue;
  }
  const fresh = join(tmp, `${shot.name}.png`);
  let cmp;
  try {
    capture(shot, fresh);
    cmp = compare(baseline, fresh, join(dir, `${shot.name}.diff.png`));
  } catch (e) {
    console.error(`  ${label} FAILED: ${e.message}`);
    failed++;
    continue;
  }
  const tol = Number(shot.tolerance ?? defaultTolerance);
  if (cmp.why) {
    console.error(`  ${label} CHANGED: ${cmp.why}`);
    failed++;
  } else if (cmp.ratio > tol) {
    const pct = (cmp.ratio * 100).toFixed(3);
    console.error(`  ${label} CHANGED: ${cmp.pixels} px (${pct}% > ${(tol * 100).toFixed(3)}%) — see ${shot.name}.diff.png`);
    failed++;
  } else {
    // A clean shot leaves no diff image behind to confuse the next reader.
    rmSync(join(dir, `${shot.name}.diff.png`), { force: true });
    console.log(`  ${label} ok`);
  }
}

rmSync(tmp, { recursive: true, force: true });

if (opt.update) {
  console.log(`${updated} baseline(s) written to ${dir}`);
  process.exit(failed ? 1 : 0);
}
if (failed) {
  console.error(`\n${failed} shot(s) changed. Look at the diff PNGs; if the change is intended, re-run with --update.`);
  process.exit(1);
}
console.log('all shots match their baselines');
