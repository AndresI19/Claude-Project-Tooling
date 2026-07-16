#!/usr/bin/env node
// shot.mjs — one reusable headless-browser screenshot, so this stops being hand-written CDP glue
// every time a change needs a visual check.
//
// Drives a headless Chromium/Brave over the DevTools protocol: navigate, optionally seed an identity,
// optionally emulate a phone, optionally click things open, then capture — the whole viewport, the
// full scrollable page, or the bounding box of one element.
//
// Usage:
//   node shot.mjs --url <URL> --out <PATH> [options]
//
// Options:
//   --url <url>          page to load                                        (required)
//   --out <path>         PNG output path                                     (required)
//   --selector <css>     clip to this element's bounding box (else viewport)
//   --width <px>         viewport width                                      (default 1460)
//   --height <px>        viewport height                                     (default 1200)
//   --mobile             emulate a 390px phone (deviceScaleFactor 2, touch)
//   --identity <val>     seed localStorage['platform:identity'] before load:
//                          guest | admin | user | '<raw JSON>'
//   --click <css[,css]>  click these selectors in order before capturing (open a panel, switch a tab)
//   --eval <js>          run this JS in the page before capturing (power tool)
//   --wait <ms>          settle time after load and after each action        (default 4000)
//   --full               capture the full scrollable page (ignored with --selector)
//   --reduced-motion     emulate prefers-reduced-motion: reduce — freezes CSS animations, which is
//                        what makes a pixel baseline of an animated view possible at all
//   --browser <path>     browser binary (else auto-detected)
//   --timeout <ms>       hard cap on the whole run                           (default 90000)
//
// Prints the output path and the captured pixel size, or a labelled ERROR: line for the caller.

import { spawn, spawnSync } from 'node:child_process';
import { writeFileSync, existsSync, readFileSync, rmSync } from 'node:fs';

const fail = (msg) => { console.error(`ERROR: ${msg}`); process.exit(1); };

// ---- args -------------------------------------------------------------------
const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) continue;
  const key = a.slice(2);
  const flags = new Set(['mobile', 'full', 'reduced-motion']);
  opt[key] = flags.has(key) ? true : argv[++i];
}
if (!opt.url || !opt.out) fail('both --url and --out are required. See the header for usage.');

const WIDTH = Number(opt.width || 1460);
const HEIGHT = Number(opt.height || 1200);
const WAIT = Number(opt.wait || 4000);
const TIMEOUT = Number(opt.timeout || 90000);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- identity presets -------------------------------------------------------
const IDENTITY = {
  guest: '{"mode":"guest"}',
  user: '{"mode":"user","username":"demo","admin":false}',
  admin: '{"mode":"user","username":"demo","admin":true}',
};
const identityJson = opt.identity ? (IDENTITY[opt.identity] ?? opt.identity) : null;

// ---- find a browser ---------------------------------------------------------
function findBrowser() {
  if (opt.browser) return opt.browser;
  const candidates = [
    '/usr/bin/brave-browser', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
  ];
  for (const c of candidates) if (existsSync(c)) return c;
  // last resort: ask the shell
  for (const name of ['brave-browser', 'chromium', 'google-chrome']) {
    const w = spawnSync('which', [name]);
    if (w.status === 0) return w.stdout.toString().trim();
  }
  fail('no headless browser found (looked for brave-browser, chromium, google-chrome). Pass --browser.');
}

// ---- CDP over the websocket -------------------------------------------------
async function main() {
  const browser = findBrowser();
  const profile = `/tmp/shot-${process.pid}-${Date.now()}`;
  // PORT 0, NOT A GUESS. The browser picks a free port and writes it to DevToolsActivePort in its own
  // profile dir; we read it back from there.
  //
  // This used to be `9200 + random(700)` and then talk to whatever answered on that port — which is not
  // necessarily the browser we just spawned. Other tools on this machine open debug ports in the same
  // range (resume-lab's build.mjs uses 9300 + random(500)), and headless browsers outlive their parent
  // when a run dies. The failure is silent and awful: you attach to a STRANGER's browser, drive it, and
  // screenshot its page with its emulation still set. Caught red-handed — a `--width 1200` shot came back
  // 390x1500, the exact metrics of a mobile run whose browser had not exited. A screenshot tool that can
  // quietly photograph the wrong browser is worse than no screenshot tool, and a baseline captured that
  // way would be worse still.
  const args = [
    '--headless=new', '--disable-gpu', '--no-sandbox', `--user-data-dir=${profile}`,
    '--remote-debugging-port=0', `--window-size=${WIDTH},${HEIGHT}`, 'about:blank',
  ];
  // `detached` makes the child a PROCESS GROUP LEADER, which is the only reason killAll below can
  // actually reap it. A browser is not one process: brave forks a zygote and a renderer per tab, and
  // SIGKILL on the direct child leaves the rest orphaned and running — holding their debug port open.
  // This leaked ~4 processes on EVERY shot ever taken; the machine had 406 of them alive when it was
  // found, which is also what made the port guessing above collide in the first place. Two bugs, one
  // cause.
  const proc = spawn(browser, args, { stdio: 'ignore', detached: true });
  let reaped = false;
  const killAll = () => {
    if (reaped) return;
    reaped = true;
    // Negative pid = the whole process group. This is the line that actually ends the browser.
    try { process.kill(-proc.pid, 'SIGKILL'); } catch {}
    try { proc.kill('SIGKILL'); } catch {}
    try { rmSync(profile, { recursive: true, force: true }); } catch {}
  };
  // Cover the paths that are not the happy one: an uncaught throw, a Ctrl-C, a parent that just ends.
  process.on('exit', killAll);
  process.on('SIGINT', () => { killAll(); process.exit(130); });
  process.on('SIGTERM', () => { killAll(); process.exit(143); });
  const hardStop = setTimeout(() => { killAll(); fail(`timed out after ${TIMEOUT}ms`); }, TIMEOUT);

  // The port our browser actually got. First line of the file is the port, second the browser ws path.
  let port = null;
  for (let i = 0; i < 120 && !port; i++) {
    try {
      const line = readFileSync(`${profile}/DevToolsActivePort`, 'utf8').split('\n')[0].trim();
      if (line) port = Number(line);
    } catch { /* not written yet */ }
    if (!port) await sleep(250);
  }
  if (!port) { killAll(); fail('the browser never wrote DevToolsActivePort — it did not start'); }

  // discover the page target
  let wsUrl = null;
  for (let i = 0; i < 80 && !wsUrl; i++) {
    try {
      const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
      wsUrl = list.find((t) => t.type === 'page')?.webSocketDebuggerUrl ?? null;
    } catch { /* not up yet */ }
    if (!wsUrl) await sleep(250);
  }
  if (!wsUrl) { killAll(); fail('the browser never exposed a CDP endpoint'); }

  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws')); });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (m) => {
    const x = JSON.parse(m.data);
    if (x.id && pending.has(x.id)) { pending.get(x.id)(x.result); pending.delete(x.id); }
  };
  const send = (method, params = {}) =>
    new Promise((res) => { const n = ++id; pending.set(n, res); ws.send(JSON.stringify({ id: n, method, params })); });
  const evaluate = (expression) =>
    send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression }).then((r) => r.result?.value);

  await send('Page.enable');
  await send('Runtime.enable');

  if (opt.mobile) {
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 1500, deviceScaleFactor: 2, mobile: true });
  }
  /* Ask the PAGE to hold still, rather than trying to time it.
     An animating view cannot have a pixel baseline: the quiz's garden has falling particles and
     animated animals, so two captures of an unchanged page differ by thousands of pixels and every
     check cries wolf. Sleeping longer does not help — there is no frame at which an infinite animation
     is "done". These apps already answer this exact question for real users, via
     `@media (prefers-reduced-motion: reduce) { animation: none }`, so the honest move is to be a user
     who asked for that. It freezes what the app itself agrees is decoration and touches nothing else. */
  if (opt['reduced-motion']) {
    await send('Emulation.setEmulatedMedia', {
      features: [{ name: 'prefers-reduced-motion', value: 'reduce' }],
    });
  }
  if (identityJson) {
    // A quoted, escaped literal so any characters in the JSON survive the round-trip.
    const src = `localStorage.setItem('platform:identity', ${JSON.stringify(identityJson)});`;
    await send('Page.addScriptToEvaluateOnNewDocument', { source: src });
  }

  await send('Page.navigate', { url: opt.url });
  await sleep(WAIT);

  if (opt.click) {
    for (const sel of String(opt.click).split(',').map((s) => s.trim()).filter(Boolean)) {
      const clicked = await evaluate(
        `(()=>{const el=document.querySelector(${JSON.stringify(sel)});if(!el)return false;el.click();return true;})()`,
      );
      if (!clicked) console.error(`  note: --click selector not found: ${sel}`);
      await sleep(WAIT);
    }
  }
  if (opt.eval) { await evaluate(String(opt.eval)); await sleep(WAIT); }

  // Where to clip.
  let clip;
  if (opt.selector) {
    clip = await evaluate(
      `(()=>{const e=document.querySelector(${JSON.stringify(opt.selector)});if(!e)return null;` +
      `const r=e.getBoundingClientRect();return{x:Math.max(0,r.x-4),y:Math.max(0,r.y-4),width:r.width+8,height:r.height+8,scale:1};})()`,
    );
    if (!clip) { killAll(); fail(`--selector matched no element: ${opt.selector}`); }
  }

  const { data } = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: Boolean(opt.selector || opt.full),
    clip: clip || undefined,
  });
  if (!data) { killAll(); fail('the browser returned no image data'); }
  const png = Buffer.from(data, 'base64');
  writeFileSync(opt.out, png);

  // The size is read back out of the PNG's own IHDR, not recomputed from what we asked for.
  //
  // It used to print WIDTH x HEIGHT — the defaults — whenever there was no --selector, which was wrong
  // in every interesting case: --mobile overrides the metrics to 390x1500 at 2x, and --full captures the
  // whole scrollable page. A mobile full-page shot reported `1460x1200` for a file that was actually
  // 780x10796, so the one line telling you what you captured was the one line you could not trust.
  // IHDR is bytes 16..23 of every PNG, big-endian, and it describes the file that now exists.
  const w = png.readUInt32BE(16);
  const h = png.readUInt32BE(20);
  const scale = opt.mobile ? 2 : 1;
  const css = scale > 1 ? `, ${Math.round(w / scale)}x${Math.round(h / scale)} CSS @${scale}x` : '';
  console.log(`wrote ${opt.out} (${w}x${h}${css})`);

  clearTimeout(hardStop);
  // Ask it to leave before making it. Browser.close lets brave tear its own children down cleanly;
  // killAll is the backstop for when it will not, and for every path that never gets here.
  try { await Promise.race([send('Browser.close'), sleep(2000)]); } catch {}
  ws.close();
  killAll();
  process.exit(0);
}

main().catch((e) => fail(e?.message || String(e)));
