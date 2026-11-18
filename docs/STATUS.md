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

**Not yet built from this plan:** `perf_budget.py`, `crawl_links.py`, `img_budget.py`,
`provenance.py`, `robots.txt` blog-drafts test (steps 4, 5, 6, 7, 9). Say this plainly —
phase 1 baseline is partially done (1, 2, 3 this run), not complete.
