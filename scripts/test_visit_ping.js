// Runs assets/visit-ping.js against a fake browser. Run: node scripts/test_visit_ping.js
const fs = require("fs"), vm = require("vm"), path = require("path"), assert = require("assert");
const src = fs.readFileSync(path.join(__dirname, "..", "assets", "visit-ping.js"), "utf8");
const URL_OK = "https://ntfy.sh/visits-test";

function run(opts = {}) {
  const sent = [], local = {}, sess = {};
  const mk = (o) => ({ getItem: (k) => (k in o ? o[k] : null), setItem: (k, v) => { o[k] = String(v); } });
  Object.assign(local, opts.local || {});
  const win = {
    localStorage: mk(local), sessionStorage: mk(sess), screen: { width: opts.width || 390 },
    matchMedia: () => ({ matches: opts.coarse !== false }), fetch: undefined,
  };
  const nav = { userAgent: opts.ua || "Mozilla/5.0 (Linux; Android 9) Chrome/120 Mobile", language: "en-CA",
    webdriver: !!opts.webdriver, doNotTrack: opts.dnt || null, globalPrivacyControl: !!opts.gpc,
    sendBeacon: (u, b) => { sent.push({ u, b }); return true; } };
  win.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(opts.cfg === undefined ? { visitPingUrl: URL_OK } : opts.cfg) });
  const ctx = { window: win, navigator: nav, document: { title: "Painter", referrer: opts.ref || "" },
    location: { protocol: opts.proto || "https:", hostname: opts.host || "chrislloyd.io", pathname: opts.path || "/", search: opts.search || "" },
    screen: win.screen, matchMedia: win.matchMedia, fetch: win.fetch, URL, URLSearchParams, Blob, Intl,
    console };
  ctx.window = Object.assign(ctx, win);
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  return new Promise((r) => setTimeout(() => r({ sent, local, sess }), 20));
}
const text = async (s) => (s.b instanceof Blob ? await s.b.text() : String(s.b));

(async () => {
  let r = await run({ ref: "https://www.google.com/search?q=painter", search: "?utm_source=flyer&utm_campaign=spring" });
  assert.strictEqual(r.sent.length, 1);
  assert.strictEqual(r.sent[0].u, URL_OK);
  const t = await text(r.sent[0]);
  assert.match(t, /Page: \/ \(Painter\)/);
  assert.match(t, /From: search www\.google\.com/);
  assert.match(t, /Campaign: source=flyer campaign=spring/);
  assert.match(t, /Region: .*, en-CA/);
  assert.match(t, /Device: mobile, <500px/);
  assert.ok(!/q=painter/.test(t), "referrer path/query must not be sent");

  r = await run({ ref: "https://chrislloyd.io/blog.html" });
  assert.match(await text(r.sent[0]), /From: direct/);

  // silent cases
  assert.strictEqual((await run({ ua: "Googlebot/2.1" })).sent.length, 0, "bot");
  assert.strictEqual((await run({ webdriver: true })).sent.length, 0, "webdriver");
  assert.strictEqual((await run({ dnt: "1" })).sent.length, 0, "DNT");
  assert.strictEqual((await run({ gpc: true })).sent.length, 0, "GPC");
  assert.strictEqual((await run({ host: "localhost" })).sent.length, 0, "localhost");
  assert.strictEqual((await run({ proto: "file:" })).sent.length, 0, "file");
  assert.strictEqual((await run({ cfg: {} })).sent.length, 0, "no url");
  assert.strictEqual((await run({ cfg: { visitPingUrl: "http://ntfy.sh/x" } })).sent.length, 0, "http url rejected");
  assert.strictEqual((await run({ local: { visitPingOff: "1" } })).sent.length, 0, "owner off");
  r = await run({ search: "?me=1" });
  assert.strictEqual(r.sent.length, 0); assert.strictEqual(r.local.visitPingOff, "1");
  r = await run({ search: "?me=0", local: { visitPingOff: "1" } });
  assert.strictEqual(r.sent.length, 1, "?me=0 resumes");

  // no sensitive APIs in the script
  for (const bad of ["geolocation", "document.cookie", "FormData", "ip="]) assert.ok(!src.includes(bad), bad);
  console.log("visit-ping: all checks passed");
})().catch((e) => { console.error(e); process.exit(1); });
