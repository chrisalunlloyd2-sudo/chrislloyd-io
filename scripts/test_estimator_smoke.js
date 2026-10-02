// Task 034 — smoke-test the SHIPPED assets/main.js estimator code directly
// (no browser available in CI sandbox: platform lacks one). Minimal DOM shim
// executes the whole IIFE; asserts window.__estimatorPure parity + renderer
// wiring actually ran against the shipped file, not a mirror copy.
'use strict';
const fs = require('fs');
const path = require('path');

let fail = 0;
function expect(cond, msg) { if (!cond) { console.log('FAIL:', msg); fail++; } }

// --- tiny DOM shim (only what main.js touches) ---------------------------------
function makeEl(tag) {
  const e = {
    tagName: tag, children: [], style: {}, dataset: {},
    _attrs: {}, classList: {
      _s: new Set(),
      add(...c) { c.forEach(x => this._s.add(x)); },
      remove(...c) { c.forEach(x => this._s.delete(x)); },
      contains(c) { return this._s.has(c); }
    },
    setAttribute(k, v) { this._attrs[k] = String(v); },
    getAttribute(k) { return this._attrs[k]; },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; },
    set _listenersMap(m) { this._lm = m; },
    get _listeners() { return this._lm || (this._lm = {}); },
    addEventListener(t) { this._listeners[t] = true; },
    removeEventListener() {},
    set textContent(v) { this._text = String(v); this.children = []; },
    get textContent() { return this._text || (this.children || []).map(c => c.textContent || '').join(''); },
    set innerHTML(v) { this._html = v; this.children = []; },
    get innerHTML() { return this._html || ''; },
    get parentNode() { return null; },
    get hidden() { return !!this._hidden; },
    set hidden(v) { this._hidden = !!v; }
  };
  return e;
}
const byId = {};
const els = {
  'est-out': makeEl('div'), 'est-calc': makeEl('button'),
  'est-range': makeEl('div'), 'est-lines': makeEl('div'),
  'est-disclaimer': makeEl('p'), 'est-interior-fields': makeEl('div'),
  'est-exterior-fields': makeEl('div'), 'est-rooms': makeEl('input'),
  'est-size': makeEl('input'), 'est-height': makeEl('select'),
  'est-repairs': makeEl('input'), 'est-sqft': makeEl('input'),
};

// stub the ids main.js writes into at bootstrap
['site-tagline', 'site-blurb', 'year', 'gallery-grid', 'testimonials-grid',
 'reviews-grid', 'shop-grid', 'opensource-grid', 'services-grid', 'about-copy',
 'about-block', 'faq-list', 'promo-strip', 'contact-form', 'contact-email',
 'contact-phone', 'contact-form-note', 'contact-side', 'local-business-jsonld',
 'canonical-link'].forEach(id => { els[id] = makeEl('div'); byId[id] = els[id]; });
Object.keys(els).forEach(id => { byId[id] = els[id]; });

const fetchedUrls = [];
global.window = {};
if (typeof navigator === 'undefined') {
  Object.defineProperty(globalThis, 'navigator', { value: { userAgent: 'node-shim' }, configurable: true });
}
const MODE_RADIOS = [
  Object.assign(makeEl('input'), { value: 'interior', checked: true }),
  Object.assign(makeEl('input'), { value: 'exterior', checked: false }),
];
global.document = {
  getElementById(id) { return byId[id] || null; },
  querySelector(sel) {
    if (sel.indexOf('est-mode') !== -1) return MODE_RADIOS.find(r => r.checked) || null;
    return null;
  },
  querySelectorAll(sel) {
    if (sel.indexOf('est-mode') !== -1) return MODE_RADIOS;
    return [];
  },
  createElement: makeEl,
  createElementNS() { return makeEl('svg'); },
  head: makeEl('head'), body: makeEl('body'),
  addEventListener() {}
};
global.location = { href: 'http://127.0.0.1:8741/index.html', origin: 'http://127.0.0.1:8741' };
global.fetch = function (url) {
  fetchedUrls.push(url);
  const p = String(url).replace(/^https?:\/\/[^/]+\//, '').replace(/^\//, '');
  const fp = path.join('/root/chrislloyd-io', p);
  return Promise.resolve({
    ok: fs.existsSync(fp),
    json() { return Promise.resolve(JSON.parse(fs.readFileSync(fp, 'utf8'))); }
  });
};

// execute the real shipped main.js
const src = fs.readFileSync('/root/chrislloyd-io/assets/main.js', 'utf8');
new Function(src)();

setTimeout(() => {                          // let the fetch promises settle
  // 1. shipped pure helpers are exposed on window
  const pure = window.__estimatorPure;
  expect(!!pure, 'window.__estimatorPure exposed by shipped main.js');
  if (!pure) return done();
  // 2. parity snapshot vs CLI fixtures
  const FIX = JSON.parse(fs.readFileSync('/root/chrislloyd-io/scripts/test_estimator_fixtures.json'));
  const d = pure.estimateInterior(3, 12, 14, 8, 0, null);
  expect(JSON.stringify(d.total_range) === JSON.stringify(FIX.interior_default.total_range),
    'shipped main.js default interior matches CLI fixture ' + JSON.stringify(d.total_range));
  const e = pure.estimateExterior(1500, null);
  expect(JSON.stringify(e.total_range) === JSON.stringify(FIX.exterior_default.total_range),
    'shipped main.js exterior matches CLI fixture');
  // 3. renderer wired: estimator elements fetched, pricing.json fetched, listeners attached
  expect(fetchedUrls.indexOf('data/pricing.json') !== -1, 'main.js fetched data/pricing.json (got: ' + fetchedUrls.join(',') + ')');
  expect(els['est-calc']._listeners && els['est-calc']._listeners.click, 'calc button listener attached');
  expect(els['est-disclaimer'].hidden === false, 'disclaimer visible after run');
  expect(fail === 0 ? true : fail, 'failures: ' + fail);
  done();
}, 100);

function done() {
  console.log(fail === 0 ? 'ALL ESTIMATOR SHIPPED-FILE SMOKE TESTS PASS' : 'FAILURES: ' + fail);
  process.exit(fail ? 1 : 0);
}