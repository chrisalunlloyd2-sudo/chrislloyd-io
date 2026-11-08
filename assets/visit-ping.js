/**
 * visit-ping.js - one small "someone opened a page" notification to the owner's phone.
 *
 * Sends ONE plain-text line to the relay URL in data/config.json (visitPingUrl, e.g. an ntfy.sh topic).
 * Empty/missing URL = does nothing. The URL is a public posting address, not a credential.
 *
 * What is sent: page path, page title, referring site (host only), search/social/direct,
 * utm_source/medium/campaign if present, browser time zone (a coarse region such as America/Edmonton),
 * browser language, device type and screen width bucket.
 * What is never sent: IP address from this script, name, email, form contents, exact location.
 * It never asks for the location permission.
 *
 * Skipped: bots and headless browsers, Do Not Track / Global Privacy Control, local files and localhost,
 * the owner (open any page once with ?me=1 to stop pinging from that browser, ?me=0 to resume),
 * and repeat pages in the same browser session (once per page per session).
 * Fire-and-forget (sendBeacon): never delays or breaks the page.
 */
(function () {
  "use strict";
  var BOT = /bot|crawl|spider|slurp|headless|lighthouse|preview|phantom|facebookexternalhit|curl|wget|python|java\//i;
  var SEARCH = /(^|\.)(google|bing|duckduckgo|yahoo|ecosia|brave|startpage|yandex|baidu)\./i;
  var SOCIAL = /(^|\.)(facebook|instagram|t\.co|twitter|x\.com|linkedin|reddit|pinterest|tiktok|youtube|kijiji|nextdoor)\b/i;

  function safe(s, n) {
    return String(s == null ? "" : s).replace(/[\u0000-\u001f\u007f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, n);
  }
  function store(kind, key, val) {
    try {
      var s = kind === "local" ? window.localStorage : window.sessionStorage;
      if (val === undefined) return s.getItem(key);
      s.setItem(key, val);
    } catch (e) { /* storage blocked: carry on */ }
    return null;
  }
  function param(name) {
    try { return new URLSearchParams(location.search).get(name) || ""; } catch (e) { return ""; }
  }
  function refInfo() {
    var host = "";
    try { host = document.referrer ? new URL(document.referrer).hostname : ""; } catch (e) { host = ""; }
    if (!host || host === location.hostname) return { host: "", kind: "direct" };
    return { host: safe(host, 60), kind: SEARCH.test(host) ? "search" : SOCIAL.test(host) ? "social" : "link" };
  }
  function line() {
    var r = refInfo(), tz = "", lang = safe(navigator.language, 12);
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) { tz = ""; }
    var w = window.screen && screen.width ? screen.width : 0;
    var device = (window.matchMedia && matchMedia("(pointer:coarse)").matches) || w < 820 ? "mobile" : "desktop";
    var utm = ["utm_source", "utm_medium", "utm_campaign"].map(function (k) {
      var v = safe(param(k), 40); return v ? k.slice(4) + "=" + v : "";
    }).filter(Boolean).join(" ");
    return [
      "Page: " + safe(location.pathname, 80) + " (" + safe(document.title, 60) + ")",
      "From: " + r.kind + (r.host ? " " + r.host : ""),
      utm ? "Campaign: " + utm : "",
      "Region: " + (safe(tz, 40) || "unknown") + ", " + (lang || "unknown"),
      "Device: " + device + (w ? ", " + (w < 500 ? "<500" : w < 820 ? "500-819" : w < 1200 ? "820-1199" : "1200+") + "px" : "")
    ].filter(Boolean).join("\n");
  }
  function skip() {
    if (location.protocol !== "https:" && location.protocol !== "http:") return true;
    if (/^(localhost|127\.|\[::1\])/.test(location.hostname)) return true;
    if (navigator.webdriver || BOT.test(navigator.userAgent || "")) return true;
    if (navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl) return true;
    var me = param("me");
    if (me === "1") store("local", "visitPingOff", "1");
    if (me === "0") store("local", "visitPingOff", "");
    if (store("local", "visitPingOff")) return true;
    var seen = "visitPing:" + location.pathname;
    if (store("session", seen)) return true;
    store("session", seen, "1");
    return false;
  }

  try {
    if (skip() || !window.fetch || !navigator.sendBeacon) return;
    fetch("data/config.json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (cfg) {
      var url = cfg && cfg.visitPingUrl;
      if (typeof url !== "string" || url.indexOf("https://") !== 0) return;
      navigator.sendBeacon(url, new Blob([line()], { type: "text/plain" }));
    }).catch(function () { /* ping is optional */ });
  } catch (e) { /* never break the page */ }
})();
