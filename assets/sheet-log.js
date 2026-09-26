/**
 * sheet-log.js — fire-and-forget duplicate logging of contact form submissions
 * to a Google Sheet via an Apps Script Web App endpoint (task 019).
 *
 * Why: Formspree's free tier keeps only 30 days of history and gates CSV
 * export/webhooks behind paid plans. The owner wants an unlimited-history
 * dataset of inquiry volume + lead_tier for season-over-season demand
 * analysis. This module posts the same fields the form already collects to
 * a Google Sheet, ALONGSIDE (never instead of) the existing Formspree/mailto
 * submission.
 *
 * Hard rules:
 *   - Fire-and-forget: a slow/down/unset endpoint must never delay, block,
 *     or break the primary submission path. All errors are swallowed.
 *   - If data/config.json has no `sheetLogEndpoint` (empty/missing), this
 *     module no-ops silently — safe to ship before the owner's one-time
 *     Apps Script setup (docs/sheet-logging-setup.md).
 *   - No PII beyond what the form already collects. No new form fields.
 *   - No secrets: the Apps Script web-app URL is a public posting endpoint,
 *     not a credential (see docs/sheet-logging-setup.md).
 */

var SHEET_LOG_CONFIG_URL = "data/config.json";

function setupSheetLog(form) {
  if (!form) return;
  var endpoint = "";
  fetch(SHEET_LOG_CONFIG_URL)
    .then(function (r) { return r.ok ? r.json() : {}; })
    .then(function (cfg) { endpoint = (cfg && cfg.sheetLogEndpoint) || ""; })
    .catch(function () { endpoint = ""; });

  // Bubble-phase submit listener: runs after the capture-phase tier stamping
  // in main.js, so the hidden lead_tier field is already populated when we
  // snapshot the form data below.
  form.addEventListener("submit", function () {
    if (!endpoint) return; // unset/unknown -> silent no-op
    try {
      var fd = new FormData(form);
      var tier = (document.getElementById("lead-tier") || {}).value || "";
      var payload = {
        submittedAt: new Date().toISOString(),
        name: fd.get("name") || "",
        heardAbout: fd.get("heard_about") || "",
        project: fd.get("project") || "",
        propertyStatus: fd.get("property_status") || "",
        timeline: fd.get("timeline") || "",
        budget: fd.get("budget") || "",
        contactPreference: fd.get("contact_preference") || "",
        phone: fd.get("phone") || "",
        leadTier: tier
      };
      var blob = new Blob([JSON.stringify(payload)], { type: "text/plain;charset=utf-8" });
      // Blob body avoids a CORS preflight that a JSON content-type header
      // would trigger; Apps Script's doPost(e).postBody receives it directly.
      fetch(endpoint, { method: "POST", body: blob, mode: "no-cors", keepalive: true })
        .catch(function () { /* never surface logging failures */ });
    } catch (err) { /* swallowed — logging must never break submission */ }
  });
}