# chrislloyd-io: 30 improvements + 100-step plan

Approved by Chris 2026-11-15 (all 30, all 100). Revised the same day on his instruction:
**local-first, no-dependency-first**. Static HTML + JSON data, stdlib Python scripts, vanilla JS. No
build step, no frameworks, no pip installs, no paid services, no new accounts without asking. External
tools (Search Console, Pillow, Lighthouse) are optional checks that come after our own module works.

Goal: a local-SEO-first business site for Chris Alun Lloyd Ltd (painting, Edmonton and area), the store
page mirroring Shopify daily, and a link to the on-device voice assistant/translator
(/root/Claude/docs/PLAN-VOICE-100.md).

Facts: custom domain NOT registered (canonical empty on purpose); Google Business Profile (GBP) not
created (owner); Formspree form live; Pages deploys from branch; never fabricate; CASL consent for email.
Owner-only: domain, GBP, photos, client reviews, Instagram/Facebook, gist PAT, census table fetch.

## Risks -> workarounds (our own modules and bots)

| Risk | Workaround we build ourselves |
|---|---|
| Doorway / thin pages lower ranking | `scripts/content_density.py`: a page is generated only if its owner-written fields are non-empty and its text is < 60 % shared with any sibling page. Bot `density-check` runs before every deploy. |
| Thin machine translation | Our Five-S pipeline (shared with the voice plan) + `noindex` until owner approves + 5-language cap. `scripts/i18n/sift.py` is the gate. |
| No Hunspell / Apertium | Shared modules from /root/Claude/life/xlate (glossary, phrase table, rules, edit-distance spell). Site scripts import them by path; no package install. |
| LocalBusiness schema with missing address | `scripts/check_schema_data.py` refuses LocalBusiness unless site.json has name, address, phone, hours; NAP block renders only then. |
| No image tooling (Pillow) | `scripts/img_budget.py`: size and dimension check from the file header (stdlib struct). Owner resizes on the phone; WebP is an optional later upgrade. |
| Census data guessed | Owner fetches the Statistics Canada table once; `data/edmonton-languages.json` with URL and date; `test_i18n.py` refuses languages absent from it. |
| No analytics without third parties | `scripts/visit_report.py` over the existing visit-ping log: counts only, weekly, to data-exports. |
| Lighthouse unavailable on the phone | `scripts/perf_budget.py`: HTML < 60 KB, no render-blocking scripts, no external fonts, image budget; fails the test suite. |
| Invented content slipping in | `scripts/provenance.py`: every rendered string must trace to a data file with a `source` field; test fails otherwise. |

## Own modules
`content_density.py`, `perf_budget.py`, `img_budget.py`, `provenance.py`, `visit_report.py`,
`crawl_links.py`, `gen_faq.py` (FAQPage + speakable JSON-LD), `scripts/i18n/{seek,seed,shape,splice,sift}.py`,
`scripts/lead_schema.py` (one schema shared with the voice intent and the dashboard Leads tab).
## Own bots (script on a timer, no LLM)
`density-check` and `perf-budget` before deploy, `visit-report` weekly, `store-journal` daily (removed handles),
`faq-proposal` monthly (from the voice question log, owner approves).

## 30 improvements (approved)
Local SEO
1. FAQ page from data/faq.json with FAQPage schema; real customer questions only (owner supplies).
2. speakable schema on FAQ answers, same JSON the voice reads.
3. Service x area pages only where content_density passes; max 4 areas x 3 services.
4. NAP block + LocalBusiness schema gated on real details.
5. hreflang for every translated page; language sitemap.
6. Internal link lint (<= 2 clicks from home), our crawler.
7. Alt-text lint + img_budget.
8. perf_budget test (HTML size, blocking scripts, fonts).
9. /review page explaining how to leave a review (link filled by owner).
10. Seasonal content slot per month from promo-calendar.json (owner review).
Content without invention
11. Testimonials hidden until reviews.json has one real entry (test).
12. Gallery hidden until one real owner photo pair.
13. Blog posts need a sources field; drafts stay drafts without it.
14. Pricing page explains estimator assumptions; numbers only from pricing.json.
15. "How we work" page written by owner.
Translation (ours)
16. Five-S scripts with fixtures.
17. Glossary per language, owner-checked.
18. Gate: our spell + glossary + ratio; failing strings keep English with lang attribute.
19. Language selector remembered in localStorage; default by Accept-Language.
20. Cap at 5 languages from the owner-fetched census file.
Store page
21. Disclosure lint.
22. No-invention lint (card text substring of the Shopify listing).
23. Removed-handle journal line.
24. Click counter via redirect page (local JSON, no cookies).
25. Monthly cycle-out of bottom 3 (proposal, owner approves).
Conversion and leads
26. Lead fields mirror the shared lead schema.
27. Thank-you page with next steps (no paid tools).
28. Estimator "email me this" via Formspree with CASL consent box.
29. Weekly visit_report to data-exports.
30. Lead-tier rule explained in one sentence on the form.

## 100 steps in 10 phases (local-first; tick with a date)

### Phase 1: baseline (1-10)
1. [x] 2026-11-18 Ran every scripts/test_*.py and test_*.js (69 Python + 7 JS suites). One
   real failure found and fixed: test_i18n.py's source was stale after the daily store
   sync; ran `i18n_extract.py --sync`, now green. 155/637 strings still have no French.
2. [x] 2026-11-18 docs/STATUS.md written (dated, real measured counts, not targets).
3. [x] 2026-11-18 Deleted 8 stray pip wheels/tarballs from the repo root (already
   gitignored, untracked, unused by any script).
4. [x] 2026-11-18 scripts/perf_budget.py: per-page HTML+local-asset weight table, 1MB
   total budget. Wired into test_site_scripts.py (TestPerfBudget, 3 tests). Real finding:
   products.html is 2.27MB (49 product images at ~45KB each, already `loading="lazy"`)
   — genuinely over budget; every other page is well under.
5. [x] 2026-11-18 scripts/crawl_links.py: internal link graph, dead-link + orphan
   detection (TestCrawlLinks, 3 tests). Site is currently clean (0 dead, 0 orphans).
6. [x] 2026-11-18 scripts/img_budget.py: size/dimension from raw PNG/JPEG headers (no
   Pillow). Alt-text stays check_a11y.py's job, not duplicated. Caught and fixed a false
   positive in my own first draft before shipping: `object-fit: cover` product photos
   were flagged as "oversized" by a naive dimension compare; fixed to compare the
   shorter native vs shorter declared dimension (TestImgBudget, 4 tests incl. a
   regression test for that exact bug).
7. [x] 2026-11-18 scripts/provenance.py (skeleton, as scoped): data/*.json -> fetching
   assets/*.js map + hand-authored text-node counts per page (TestProvenance, 3 tests).
8. [x] 2026-11-18 gen_sitemap.py verified against crawl_links — and a real bug found in
   the process: products.html (the site's biggest page) was missing from sitemap.xml
   entirely. Fixed; sitemap now has 10 URLs. Regression tests added (TestSitemap).
9. [x] 2026-11-18 robots.txt now disallows /blog-drafts/ (raw unpublished draft files
   were crawlable with no exclusion before this). Tested against robots.txt + sitemap.xml.
10. [x] 2026-11-18 Tagged site-baseline-2026-11.

### Phase 2: FAQ and speakable (11-20)
11. [ ] data/faq.json schema (question, answer, area, service, language, source).
12. [ ] Owner supplies 10 real questions.
13. [ ] gen_faq.py: FAQ page.
14. [ ] FAQPage JSON-LD.
15. [ ] speakable JSON-LD per answer.
16. [ ] check_schema_data.py extended for FAQ.
17. [ ] Top-3 FAQ block on home.
18. [ ] Area-filtered FAQ blocks on area pages.
19. [ ] Daily local mirror of data/*.json into ~/.life for the voice (voice step 67).
20. [ ] Test: voice answer text == faq.json text.

### Phase 3: local pages that earn their place (21-30)
21. [ ] Owner picks 3 services for the matrix.
22. [ ] Area template gains a service section (real photos only).
23. [ ] content_density.py; generate only passing pages.
24. [ ] density-check bot before deploy.
25. [ ] Service-area page with owner travel notes.
26. [ ] Breadcrumb schema.
27. [ ] Blog -> area page links by tag.
28. [ ] crawl_links covers the new pages.
29. [ ] Sitemap update.
30. [ ] Tag site-local-pages.

### Phase 4: NAP, GBP, citations (31-40) [owner-gated]
31. [ ] site.json address/phone/hours fields (empty until owner fills).
32. [ ] NAP component renders only when complete.
33. [ ] LocalBusiness schema gate test.
34. [ ] Owner creates GBP; pastes gbp-draft.json.
35. [ ] Review short link into review-sms-template.
36. [ ] /review page.
37. [ ] citation-targets.json status per directory.
38. [ ] Owner submits human-only citations (Yelp, HomeStars).
39. [ ] NAP consistency test (site == gbp-draft).
40. [ ] Tag site-nap.

### Phase 5: our translation pipeline (41-55)
41. [x] 2026-11-23 scripts/i18n_seek.py: diffs source.json vs fr.json, classifies untranslated/stale(rich-only)/orphaned. (Division of labour across 41-45 shifted slightly from this plan's original sketch once the real fr.json schema was in hand -- seek discovers, seed does the actual fill via /root/Claude/life/xlate, shape is pure typography, splice merges into rendered HTML not into fr.json; sift is the gate. All five real stages exist and are tested.)
42. [x] 2026-11-23 scripts/i18n_seed.py: fills via /root/Claude/life/xlate's real TranslationCombiningGate; writes fr.json using its existing plain-string shape only, abstains to a review file; never invents a translation.
43. [x] 2026-11-23 scripts/i18n_shape.py: French typography (NBSP, curly apostrophes), HTML-tag-aware. Dry-run against the live catalog found 198/482 entries would change -- NOT applied; Chris hasn't signed off on reshaping already-approved human translations.
44. [x] 2026-11-23 scripts/i18n_splice.py: stdlib DOM splicer (i18n_extract.py's own void-tag convention, no bs4), injects canonical+hreflang. Ran for real against all 7 live pages (read-only source, temp output) -- correct output, verified by sift.
45. [x] 2026-11-23 scripts/i18n_sift.py: placeholder + tag-parity + SEO-head QA gate. 0 violations across 637 real strings.
46. [x] 2026-11-23 scripts/test_phase5_site_i18n.py: 6 fixtures covering the full pipeline plus the real site's 91-test suite (test_i18n/test_store/test_site_scripts) stay green alongside it.
47. [ ] Glossaries for the first 2 languages (owner checks).
48. [ ] Owner fetches census table -> data/edmonton-languages.json; test refuses others.
49. [ ] French through the pipeline; compare with the existing catalog.
50. [ ] Language 2 through the pipeline.
51. [x] 2026-11-23 hreflang tags -- i18n_splice.py injects them per page (steps 44 above); scripts/seo_lint.py verifies cross-page reciprocity (never a false failure against today's un-localized live pages, since it only checks pages that already declare one).
52. [x] 2026-11-23 Language sitemap -- scripts/gen_sitemap.py --langs en,fr (opt-in, off by default; today's live sitemap.xml unchanged until localized pages actually ship).
53. [ ] Language selector (localStorage).
54. [ ] Gate pass rate per language in STATUS.md; translated pages noindex until approved.
55. [ ] Tag site-i18n-2.

### Phase 6: store page (56-65)
56. [ ] Disclosure lint test.
57. [ ] No-invention lint test.
58. [ ] store-journal bot: removed handles.
59. [ ] Redirect click counter (local JSON, no cookies).
60. [ ] Weekly click counts to data-exports.
61. [ ] Monthly cycle-out proposal script.
62. [ ] Low-stock -> store handle link (dashboard step 50).
63. [ ] Store titles through our i18n pipeline (descriptions stay source).
64. [ ] Store sync log check in the housekeeper.
65. [ ] Tag site-store-hardened.

### Phase 7: leads (66-75)
66. [ ] scripts/lead_schema.py: one schema; copied to the Claude repo by a test, never diverging.
67. [ ] Form fields aligned to it.
68. [ ] Thank-you page.
69. [ ] Estimator "email me this" + CASL consent.
70. [ ] Lead-tier sentence on the form.
71. [ ] visit_report.py weekly bot.
72. [ ] docs/ENQUIRIES.md on the schema.
73. [ ] Test: form field names == schema keys.
74. [ ] Honeypot field (no third party).
75. [ ] Tag site-leads.

### Phase 8: performance and accessibility (76-85)
76. [ ] perf_budget thresholds enforced.
77. [ ] CSS minify script (stdlib).
78. [ ] Defer all scripts; test.
79. [ ] Images within img_budget (owner resizes on phone; WebP optional later).
80. [ ] System font stack only.
81. [ ] check_a11y.py: contrast + focus order.
82. [ ] Keyboard test of the estimator.
83. [ ] Reduced motion everywhere.
84. [ ] Print stylesheet for the price sheet.
85. [ ] Tag site-perf.

### Phase 9: content cadence (86-93)
86. [ ] Monthly post slot from promo-calendar.json.
87. [ ] Sources-field lint for posts.
88. [ ] Owner review checklist.
89. [ ] Gallery pairs (owner photos).
90. [ ] Testimonials from sync_reviews.py only; test.
91. [ ] Social links verified by owner.
92. [ ] Newsletter NOT built until a consent flow is agreed.
93. [ ] Tag site-content.

### Phase 10: domain and launch review (94-100)
94. [ ] Owner domain decision.
95. [ ] If registered: CNAME, canonicalBase, Pages custom domain, HTTPS check.
96. [ ] Redirect map github.io -> domain.
97. [ ] Owner verifies Search Console (free, optional).
98. [ ] 30-day visit_report in STATUS.md.
99. [ ] Languages 3-5 from measured traffic.
100. [ ] Tick, date, roll forward.
