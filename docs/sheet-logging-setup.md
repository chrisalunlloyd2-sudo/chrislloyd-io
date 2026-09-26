# Google Sheet logging — one-time owner setup (task 019)

This gives every contact-form submission a second, free, unlimited-history
log in a Google Sheet, alongside the existing Formspree/email delivery
(nothing is replaced). Formspree's free tier only keeps 30 days of history
and gates CSV export behind paid plans; the Sheet becomes your
season-over-season dataset of inquiry volume and lead tiers.

You do this once. It takes about 5 minutes. The site already ships the
logging code (`assets/sheet-log.js`) — until you finish step 4, it simply
does nothing (no errors, no visitor-visible anything).

## Step 1 — Create the Sheet

1. Go to <https://sheets.new> (logged into your Google account).
2. Name it something like `Site enquiries`.
3. In row 1, paste this header row (one column per letter):

```
timestamp	name	heardAbout	project	propertyStatus	timeline	budget	contactPreference	phone	leadTier
```

(The tab characters between words make separate columns. Or just type:
`timestamp`, `name`, `heardAbout`, `project`, `propertyStatus`, `timeline`,
`budget`, `contactPreference`, `phone`, `leadTier` into A1–J1.)

## Step 2 — Add the Apps Script

1. In the Sheet: **Extensions → Apps Script**.
2. Delete any code in the editor and paste ALL of this:

```javascript
// Appends one row per contact-form submission (task 019).
function doPost(e) {
  try {
    var data = JSON.parse(e.postBody.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    sheet.appendRow([
      data.submittedAt || new Date().toISOString(),
      data.name || '',
      data.heardAbout || '',
      data.project || '',
      data.propertyStatus || '',
      data.timeline || '',
      data.budget || '',
      data.contactPreference || '',
      data.phone || '',
      data.leadTier || ''
    ]);
    return ContentService.createTextOutput(JSON.stringify({ ok: true }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ ok: false }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// One-time browser ping so you can verify the deployment works.
function doGet() {
  return ContentService.createTextOutput('sheet log web app is live');
}
```

3. Save (Ctrl+S), name the project anything, e.g. `enquiry-log`.

## Step 3 — Deploy as Web App

1. Click **Deploy → New deployment**.
2. Type (gear icon): **Web app**.
3. Description: anything. Execute as: **Me**. Who has access: **Anyone**.
   ("Anyone" is required — the site's visitors don't have Google accounts.
   This is safe: the URL only accepts rows into your sheet, it can't read
   the sheet back, and it holds no credentials.)
4. Click **Deploy**, approve the authorization prompt
   ("Review permissions → your account → Advanced → Go to … (unsafe)" —
   that wording is Google's standard warning for your own unpublished
   scripts; it only wants access to the sheet you made).
5. Copy the **Web app URL** (`https://script.google.com/macros/s/…/exec`).

## Step 4 — Point the site at it (the only value you supply)

1. Open `data/config.json` in the site repo and add one line:

```json
{
  "web3FlexEnabled": false,
  "web3": { "chainId": 1, "ownerEns": "" },
  "sheetLogEndpoint": "https://script.google.com/macros/s/PASTE-YOURS/exec"
}
```

2. Commit + push (or ask me to do it — just paste me the URL and say so).

## Step 5 — Verify (2 minutes)

1. Submit a test enquiry through the site's contact form.
2. Reload the Sheet — a row with your test answers and a `leadTier`
   (`hot` / `warm` / `filtered`) should appear within a second or two.
3. If it doesn't: confirm the URL ends in `/exec` (not `/dev`), and that
   access was set to "Anyone". Each later edit to the script needs
   **Deploy → Manage deployments → edit → New version** to take effect.

## Notes

- Every submission still goes through Formspree/email exactly as before —
  the Sheet is a parallel log, not a replacement.
- If the Sheet endpoint is ever slow or down, the site ignores it and the
  visitor's submission is unaffected.
- Row limits: Google Sheets is effectively unlimited for this use
  (10 million cells ≈ 1M enquiries).