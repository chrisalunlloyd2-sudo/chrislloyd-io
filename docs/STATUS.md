# Site status

Dated snapshot, per PLAN-SITE-100.md phase 1 step 2. Regenerate (don't hand-edit numbers)
by rerunning the commands below; this file records what was actually measured, not a target.

## 2026-11-18

**Tests** (PLAN-SITE-100 step 1):
- `scripts/test_site_scripts.py`: 52 tests, OK.
- `scripts/test_store.py`: 10 tests, OK.
- `scripts/test_i18n.py`: 7 tests, OK (1 failure fixed this run — see below).
- `scripts/test_estimator_logic.js`: OK.
- `scripts/test_estimator_smoke.js`: OK.
- `scripts/test_gallery_logic.js`: OK.
- `scripts/test_getready_smoke.js`: OK.
- `scripts/test_i18n.js`: OK.
- `scripts/test_lead_tier.js`: OK.
- `scripts/test_visit_ping.js`: OK.
- Total: 69 Python + 7 JS suites, all green.

**Fix applied this run:** `test_i18n.py::test_source_is_current` was failing — the i18n
extraction source (`data/i18n/source.json`) was stale against `data/store.json` after a
daily product sync added/removed items. Ran `python3 scripts/i18n_extract.py --sync`
(updates the extracted-strings source only; does not translate or invent copy). Test now
passes. Output: 637 strings (16 rich), 49473 chars in English source; **155 strings still
have no French** (shown in English on the live site) — this is the real backlog for
PLAN-SITE-100 phase 5 (translation pipeline), not yet built.

**Pages:** 7 HTML pages (`index`, `products`, `blog`, `leduc`, `sherwood-park`,
`spruce-grove`, `st-albert`). Largest: `products.html` 58,075 bytes, `index.html`
23,105 bytes; the four area pages are 9.1-9.2 KB each.

**Products:** 49 items across 10 categories in `data/store.json` (synced daily from
Shopify by `scripts/sync_store.py`; see store-daily-sync-and-pages-lock memory).

**Languages:** `data/i18n/` has `source.json`, `fr.json`, `fr-archive.json`, `keep.json`.
French is the only language with any translated strings, and 155/637 source strings are
still untranslated (English fallback). No language beyond French exists yet —
PLAN-SITE-100 phases 5-6 (languages 2-5) have not started.

**Sitemap:** `sitemap.xml` has 9 `<url>` entries (7 pages + 2 non-page URLs — not
re-verified against `crawl_links.py`, which doesn't exist yet; step 5 of this plan).

**Repo hygiene:** removed 8 stray `.whl`/`.tar.gz` files from the repo root (already
gitignored, untracked, unreferenced by any script — leftover pip downloads, not a
dependency of anything here). PLAN-SITE-100 step 3.

**Update 2026-11-18 (later same day) — phase 1 complete:**

- **Found and fixed a real gap**: `products.html` (49 real items, the site's biggest
  page, linked from every nav) was missing from `sitemap.xml` entirely — `gen_sitemap.py`
  never listed it. Fixed; sitemap now has 10 URLs, not 9.
- `crawl_links.py` built: internal link graph, dead-link + orphan detection. Current
  site: clean, 0 dead links, 0 orphans (7 pages).
- `perf_budget.py` built: per-page weight (HTML + local assets). `products.html` is
  genuinely over a 1MB total-weight budget (2.27MB, almost all 49 product images at
  ~45KB each) — real finding, not hidden behind a test that would just be red for the
  wrong reason. Every other page is well under budget. Note: product images already use
  `loading="lazy"`, so this is total page weight, not what loads on first paint.
- `img_budget.py` built: dimension/size audit from raw PNG/JPEG headers, no Pillow.
  Alt-text is already check_a11y.py's job, not duplicated here. One false positive
  caught and fixed before shipping: several product photos are taller than square and
  got flagged as "oversized" by a naive width/height compare — they're intentionally
  cropped via `object-fit: cover` (confirmed in `assets/style.css`), so comparing the
  shorter native dimension against the shorter declared one was the right fix. Site is
  clean under the corrected check.
- `provenance.py` built (skeleton, as planned): maps every `data/*.json` file to the
  `assets/*.js` that fetches it, and counts hand-authored text nodes per page. Several
  data files (`lidar.json`, `voice.json`, `opensource.json`, `reviews.json`, `shop.json`,
  `fx.json`, `area-pages.json` is actually build-time-only, etc.) show no client-side
  fetcher — checked, not alarming: they back currently-hidden sections
  (open-source showcase, old shop/reviews) or are consumed by Python generator scripts
  at build time, not runtime JS.
- `robots.txt` now disallows `/blog-drafts/` (raw unpublished `.md`/`.txt` draft files
  were previously crawlable with no exclusion). Tested against both robots.txt and
  sitemap.xml.
- Full suite: 69 Python test functions in `test_site_scripts.py` alone (was ~9 covering
  this area before today), 7 JS suites, all green. `test_i18n.py` and `test_store.py`
  still green too.

Tagged `site-baseline-2026-11` — PLAN-SITE-100 phase 1 (steps 1-10) is done.
