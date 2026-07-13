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
//   --browser <path>     browser binary (else auto-detected)
//   --timeout <ms>       hard cap on the whole run                           (default 90000)
//
// Prints the output path and the captured pixel size, or a labelled ERROR: line for the caller.

import { spawn, spawnSync } from 'node:child_process';
import { writeFileSync, existsSync } from 'node:fs';

const fail = (msg) => { console.error(`ERROR: ${msg}`); process.exit(1); };

// ---- args -------------------------------------------------------------------
const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) continue;
  const key = a.slice(2);
  const flags = new Set(['mobile', 'full']);
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
  // A per-run port and profile dir so concurrent shots never collide. Math.random is fine here — this
  // is a one-shot CLI, not the resumable workflow runtime.
  const port = 9200 + Math.floor(Math.random() * 700);
  const profile = `/tmp/shot-${Date.now()}-${port}`;
  const args = [
    '--headless=new', '--disable-gpu', '--no-sandbox', `--user-data-dir=${profile}`,
    `--remote-debugging-port=${port}`, `--window-size=${WIDTH},${HEIGHT}`, 'about:blank',
  ];
  const proc = spawn(browser, args, { stdio: 'ignore' });
  const killAll = () => { try { proc.kill('SIGKILL'); } catch {} };
  const hardStop = setTimeout(() => { killAll(); fail(`timed out after ${TIMEOUT}ms`); }, TIMEOUT);

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
  writeFileSync(opt.out, Buffer.from(data, 'base64'));

  const w = clip ? Math.round(clip.width) : WIDTH;
  const h = clip ? Math.round(clip.height) : HEIGHT;
  console.log(`wrote ${opt.out} (${w}x${h})`);

  clearTimeout(hardStop);
  ws.close();
  killAll();
  process.exit(0);
}

main().catch((e) => fail(e?.message || String(e)));
