// Site-wide language (English / Français) and currency (CAD / USD).
// Load in <head>, before everything else. Choosing a language or currency saves it and reloads the
// page, so there is never a half-translated page to undo. French text lives in data/i18n/fr.json
// ({p: plain text, r: text that contains inline markup}); scripts/i18n_extract.py lists every English
// string that needs an entry and scripts/test_i18n.py fails if one is missing.
(function (root) {
  "use strict";

  var SKIP = { script: 1, style: 1, noscript: 1, textarea: 1, svg: 1 };
  var ATTRS = ["placeholder", "aria-label", "title", "alt"];
  var META_NAME = { description: 1, "twitter:title": 1, "twitter:description": 1 };
  var META_PROP = { "og:title": 1, "og:description": 1 };
  var UNSAFE = { input: 1, select: 1, textarea: 1, button: 1 };

  function norm(s) { return String(s).replace(/\s+/g, " ").trim(); }
  function has(map, k) { return Object.prototype.hasOwnProperty.call(map, k); }

  // ---- Pure part: walks a DOM-like tree and swaps English for French. -------------------------
  // plain unit = one text node / one attribute; rich unit = an element that has element children AND
  // text of its own, translated as a whole (innerHTML). Mirrors scripts/i18n_extract.py exactly.
  function makeTranslator(P, R) {
    function directWords(el) {
      var text = "", c = el.childNodes;
      for (var i = 0; i < c.length; i++) if (c[i].nodeType === 3) text += " " + c[i].nodeValue;
      var m = text.match(/[A-Za-z\u00C0-\u00FF]+/g);
      return m ? m.length : 0;
    }
    function unsafeInside(el) {
      var c = el.childNodes;
      for (var i = 0; i < c.length; i++) {
        if (c[i].nodeType !== 1) continue;
        if (UNSAFE[c[i].nodeName.toLowerCase()] || c[i].hasAttribute("id") || unsafeInside(c[i])) return true;
      }
      return false;
    }
    function isRich(el) {
      if (directWords(el) < 3) return false;
      var ok = false, c = el.childNodes;
      for (var i = 0; i < c.length; i++) if (c[i].nodeType === 1 && c[i].nodeName.toLowerCase() !== "svg") ok = true;
      return ok && !unsafeInside(el);
    }
    function plain(s) {
      var k = norm(s);
      return k && has(P, k) ? P[k] : null;
    }
    function attr(el, name) {
      if (!el.hasAttribute(name)) return;
      var v = plain(el.getAttribute(name));
      if (v !== null) el.setAttribute(name, v);
    }
    function walk(node) {
      if (node.nodeType === 3) {
        var v = plain(node.nodeValue);
        if (v !== null) {
          var m = /^(\s*)[\s\S]*?(\s*)$/.exec(node.nodeValue);
          node.nodeValue = m[1] + v + m[2];
        }
        return;
      }
      if (node.nodeType !== 1) return;
      var tag = node.nodeName.toLowerCase();
      if (SKIP[tag] || node.hasAttribute("data-no-i18n")) return;
      ATTRS.forEach(function (a) { attr(node, a); });
      if (tag === "input" && /^(submit|button|reset)$/.test(node.getAttribute("type") || "")) attr(node, "value");
      if (tag === "meta" && node.hasAttribute("content")) {
        var nm = node.getAttribute("name"), pr = node.getAttribute("property");
        if ((nm && has(META_NAME, nm)) || (pr && has(META_PROP, pr))) attr(node, "content");
      }
      if (isRich(node)) {
        var k = norm(node.textContent);
        if (has(R, k)) node.innerHTML = R[k];
        return;
      }
      var kids = Array.prototype.slice.call(node.childNodes);
      for (var i = 0; i < kids.length; i++) walk(kids[i]);
    }
    return { walk: walk, plain: plain };
  }

  // ---- Pure part: money. ----------------------------------------------------------------------
  function makeMoney(cur, rate, locale, Intl_) {
    function fmt(v, digits, code) {
      var d = digits === undefined ? 2 : digits;
      try {
        return new Intl_.NumberFormat(locale, { style: "currency", currency: code, minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
      } catch (e) {
        return (code === "USD" ? "US$" : "$") + v.toFixed(d);
      }
    }
    // amount is in `base` ("CAD" or "USD"); shown in the visitor's chosen currency when a rate is known.
    return function siteMoney(amount, base, digits) {
      base = base || "CAD";
      if (base === cur) return fmt(amount, digits, cur);
      if (!rate) return fmt(amount, digits, base);
      return fmt(base === "USD" ? amount * rate : amount / rate, digits, cur);
    };
  }

  var api = { norm: norm, makeTranslator: makeTranslator, makeMoney: makeMoney };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document === "undefined") return;

  // ---- Browser part. --------------------------------------------------------------------------
  var doc = document, html = doc.documentElement;
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function ssGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function ssSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} }

  var params = new URLSearchParams(location.search);
  var q = { lang: params.get("lang"), cur: params.get("cur") };
  if (q.lang === "fr" || q.lang === "en") lsSet("site.lang", q.lang);
  if (q.cur === "CAD" || q.cur === "USD") lsSet("site.cur", q.cur);
  if (q.lang || q.cur) {
    params["delete"]("lang"); params["delete"]("cur");
    var rest = params.toString();
    try { history.replaceState(null, "", location.pathname + (rest ? "?" + rest : "") + location.hash); } catch (e) {}
  }

  var navLang = String((navigator.languages && navigator.languages[0]) || navigator.language || "en").toLowerCase();
  var lang = lsGet("site.lang") || (navLang.indexOf("fr") === 0 ? "fr" : "en");
  if (lang !== "fr") lang = "en";
  var cur = lsGet("site.cur") || (/^en-us$/.test(navLang) ? "USD" : "CAD");
  if (cur !== "USD") cur = "CAD";
  var locale = lang === "fr" ? "fr-CA" : "en-CA";

  html.setAttribute("data-lang", lang);
  html.setAttribute("data-cur", cur);
  html.setAttribute("lang", lang === "fr" ? "fr-CA" : "en");

  var style = doc.createElement("style");
  style.textContent =
    'html[data-lang="fr"]:not(.i18n-ready) body{visibility:hidden}' +
    'html[data-cur="CAD"]:not(.i18n-ready) .amt{visibility:hidden}';
  (doc.head || html).appendChild(style);

  window.i18n = { lang: lang, cur: cur, locale: locale };
  var P = {}, R = {}, rate = 0, fxInfo = null, config = {};
  var translator = makeTranslator(P, R);
  var money = makeMoney(cur, 0, locale, Intl);

  function t(key, vars) {
    var s = lang === "fr" && has(P, norm(key)) ? P[norm(key)] : key;
    if (vars) for (var k in vars) if (has(vars, k)) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  }

  function getJson(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " " + r.status);
      return r.json();
    });
  }

  // USD -> CAD rate: Bank of Canada daily rate, fetched once per browser session and kept for the
  // whole visit; data/fx.json is the fallback if the live lookup fails.
  function loadFx() {
    var cached = ssGet("site.fx");
    if (cached) { try { var c = JSON.parse(cached); if (c && c.rate > 0) return Promise.resolve(c); } catch (e) {} }
    return getJson("https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1")
      .then(function (d) {
        var o = d.observations[d.observations.length - 1];
        var r = parseFloat(o.FXUSDCAD.v);
        if (!(r > 0)) throw new Error("bad rate");
        return { rate: r, date: o.d, source: "Bank of Canada" };
      })
      .catch(function () { return getJson("data/fx.json"); })
      .then(function (c) {
        if (!(c && c.rate > 0)) throw new Error("no rate");
        ssSet("site.fx", JSON.stringify(c));
        return c;
      });
  }

  function formatAmounts(scope) {
    var list = scope.querySelectorAll ? scope.querySelectorAll("[data-usd]") : [];
    for (var i = 0; i < list.length; i++) {
      var v = parseFloat(list[i].getAttribute("data-usd"));
      if (v >= 0) list[i].textContent = money(v, "USD", 2);
    }
    if (scope.getAttribute && scope.hasAttribute("data-usd")) {
      var s = parseFloat(scope.getAttribute("data-usd"));
      if (s >= 0) scope.textContent = money(s, "USD", 2);
    }
  }

  // Links into the Shopify store carry the visitor's country (and French path, if the store has
  // published French). Both are off until switched on in data/config.json.
  function decorate(scope) {
    if (!config.shopifyCountryParam && !(config.shopifyLocales || []).length) return;
    var list = scope.querySelectorAll ? scope.querySelectorAll('a[href*="myshopify.com"]') : [];
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      if (a.getAttribute("data-shop-done") === lang + cur) continue;
      var u;
      try { u = new URL(a.getAttribute("data-shop-orig") || a.href); } catch (e) { continue; }
      if (!a.getAttribute("data-shop-orig")) a.setAttribute("data-shop-orig", a.href);
      if (config.shopifyCountryParam) u.searchParams.set("country", cur === "USD" ? "US" : "CA");
      if (lang === "fr" && (config.shopifyLocales || []).indexOf("fr") >= 0 && !/^\/fr(\/|$)/.test(u.pathname)) u.pathname = "/fr" + u.pathname;
      a.href = u.toString();
      a.setAttribute("data-shop-done", lang + cur);
    }
  }

  function process(scope) {
    if (lang === "fr") translator.walk(scope);
    formatAmounts(scope);
    decorate(scope);
  }

  function buildSwitch() {
    var host = doc.querySelector(".nav-in");
    if (!host || host.querySelector(".i18n-switch")) return;
    var box = doc.createElement("div");
    box.className = "i18n-switch";
    box.setAttribute("data-no-i18n", "");
    function group(label, name, current, opts, apply) {
      var g = doc.createElement("div");
      g.className = "i18n-group";
      g.setAttribute("role", "group");
      g.setAttribute("aria-label", label);
      opts.forEach(function (o) {
        var b = doc.createElement("button");
        b.type = "button";
        b.textContent = o[1];
        b.setAttribute("aria-pressed", o[0] === current ? "true" : "false");
        if (o[2]) b.setAttribute("lang", o[2]);
        b.addEventListener("click", function () { if (o[0] !== current) apply(o[0]); });
        g.appendChild(b);
      });
      return g;
    }
    box.appendChild(group(t("Language"), "lang", lang, [["en", "EN", "en"], ["fr", "FR", "fr"]],
      function (v) { lsSet("site.lang", v); location.reload(); }));
    box.appendChild(group(t("Currency"), "cur", cur, [["CAD", "CAD"], ["USD", "USD"]],
      function (v) { lsSet("site.cur", v); location.reload(); }));
    var cta = host.querySelector(".nav-cta");
    host.insertBefore(box, cta || null);
  }

  function observe() {
    var mo = new MutationObserver(function (recs) {
      mo.disconnect();
      var roots = [];
      recs.forEach(function (r) {
        var n = r.target;
        if (n && roots.indexOf(n) < 0) roots.push(n);
      });
      roots = roots.filter(function (n) { return !roots.some(function (o) { return o !== n && o.contains && o.contains(n); }); });
      roots.forEach(function (n) {
        if (n.nodeType === 3) {
          var p = n.parentNode;
          if (p && !SKIP[p.nodeName.toLowerCase()] && !(p.closest && p.closest("[data-no-i18n]"))) translator.walk(n);
        } else if (n.nodeType === 1 && !(n.closest && n.closest("[data-no-i18n]"))) {
          process(n);
        }
      });
      mo.observe(html, { childList: true, subtree: true, characterData: true });
    });
    mo.observe(html, { childList: true, subtree: true, characterData: true });
  }

  var domReady = new Promise(function (res) {
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", res); else res();
  });
  var catalog = lang === "fr"
    ? getJson("data/i18n/fr.json").then(function (c) { P = c.p || {}; R = c.r || {}; translator = makeTranslator(P, R); }).catch(function () {
      lang = "en"; locale = "en-CA";
      html.setAttribute("data-lang", "en"); html.setAttribute("lang", "en");
      window.i18n.lang = lang; window.i18n.locale = locale;
    })
    : Promise.resolve();
  var fx = loadFx().then(function (c) {
    rate = c.rate; fxInfo = c;
    money = makeMoney(cur, rate, locale, Intl);
  }).catch(function () {
    cur = "USD";
    html.setAttribute("data-cur", "USD");
    money = makeMoney("USD", 0, locale, Intl);
  });
  var cfg = getJson("data/config.json").then(function (c) { config = c || {}; }).catch(function () {});

  var ready = Promise.all([catalog, fx, cfg, domReady]);
  var timeout = new Promise(function (res) { setTimeout(res, 3000); });

  var finish = function () {
    process(doc.documentElement);
    buildSwitch();
    observe();
    html.classList.add("i18n-ready");
    if (fxInfo) {
      var note = doc.querySelectorAll("[data-fx-note]");
      for (var i = 0; i < note.length; i++) note[i].textContent = "1 USD = " + fxInfo.rate + " CAD (" + fxInfo.source + ", " + fxInfo.date + ")";
    }
  };
  var done = false;
  function once() { if (!done) { done = true; finish(); } }
  window.i18nReady = ready.then(function () { once(); }, function () { once(); });
  domReady.then(function () { timeout.then(once); });
  window.i18nStrings = catalog;
  window.t = t;
  window.siteMoney = function (a, b, d) { return money(a, b, d); };
})(this);
