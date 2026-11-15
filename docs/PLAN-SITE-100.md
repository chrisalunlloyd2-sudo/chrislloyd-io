# chrislloyd-io: 30 improvements + 100-step plan (2026-11-15)

Goal: a local-SEO-first business site for Chris Alun Lloyd Ltd (painting, Edmonton and area), with the
store page mirroring Shopify daily, and a voice-assistant/translator link (see
/root/Claude/docs/PLAN-VOICE-100.md). Static HTML + JSON data, no build step, no frameworks.

Facts carried from memory: custom domain NOT registered (canonical left empty on purpose); GBP account
not created (owner); Formspree form live; Pages deploy is "from branch", no GitHub Actions; never
fabricate reviews/ratings/business details; no paid services without asking; CASL consent for email.
Owner-only items: domain, GBP, photos, client reviews, Instagram/Facebook, gist PAT.

## Where it stands today (verified in repo, 2026-11-15)
- DONE: area pages (Leduc, Sherwood Park, Spruce Grove, St Albert), store sync (54 products), i18n
  catalog scaffold (French), estimator, lead-tier form, sitemap, robots, schema checks, a11y check,
  blog drafts (owner review), promo calendar, GBP draft copy, citation sweep notes.
- PART: French site-wide (catalog exists; coverage unknown), testimonials (placeholders), gallery (placeholders).
- NEW: speakable/FAQ schema, hreflang, multilingual FAQ pages, voice-lead bridge, performance budget.

## 30 improvements

Local SEO
1. FAQ page from data/faq.json with FAQPage schema; one question per real customer question (owner supplies).
2. Speakable schema on FAQ answers (same JSON the voice assistant reads).
3. Service x area matrix pages only where there is real content (no doorway pages): limit to 4 areas x 3 services.
4. NAP block (name, address, phone) rendered from site.json once real details exist; LocalBusiness schema only then.
5. hreflang tags for every translated page; language sitemap.
6. Internal link lint: every page reachable in <= 2 clicks from home; test fails otherwise.
7. Image alt text lint and WebP conversion script (stdlib + optional Pillow, verify install).
8. Core Web Vitals budget: HTML < 60 KB, no render-blocking scripts; a size test in test_site_scripts.py.
9. Review request flow: SMS template is done; add a /review page that explains how to leave one (link filled by owner).
10. Seasonal content: promo-calendar.json drives the banner; add the matching blog post slot per month (owner review).

Content without invention
11. Testimonials section hidden until reviews.json has one real entry (test enforces).
12. Gallery hidden until gallery.json has one real pair with owner photo.
13. Blog post template with a "sources" field; posts without sources stay in blog-drafts.
14. Pricing page explains the estimator's assumptions in plain words; no numbers not in pricing.json.
15. "How we work" page: prep, paint, clean-up, warranty text written by owner, not generated.

Translation (deterministic pipeline, Five-S)
16. SEEK/SEED/SHAPE/SPLICE/SIFT scripts under scripts/i18n/, each a pure function with fixtures.
17. Glossary per language of painting terms, owner-checked.
18. Gate: Hunspell + glossary + length ratio; failing strings keep English with lang attribute.
19. Language selector that remembers choice in localStorage; default by Accept-Language.
20. Cap at 5 languages chosen from census data for Edmonton; expand only on measured traffic.

Store page
21. Disclosure lint (affiliate disclosure present on every store page).
22. No-invention lint: card text must be a substring of the Shopify listing.
23. "Sold out / removed" guard already planned; add a journal line in data-exports.
24. Click counter via a redirect page (no third-party analytics, no cookies).
25. Monthly cycle-out of the bottom 3 by clicks.

Conversion and leads
26. Lead form fields mirror the voice "quote request" intent (same JSON shape).
27. Thank-you page with next steps and a calendar link (owner chooses tool; no paid).
28. Estimator result -> "email me this" uses Formspree, consent checkbox (CASL).
29. Visit ping endpoint already tested; add a weekly summary chore to data-exports (counts only).
30. Lead-tier rules documented on the site in one sentence so customers know why they are asked.

## 100-step plan in 10 phases

### Phase 1: baseline and hygiene (1-10)
1. Run all scripts/test_*.py and .js; record pass counts in docs/STATUS.md.
2. Add docs/STATUS.md (dated numbers: pages, languages, products, tests).
3. Remove stray pip wheels from the repo root (already ignored; delete files, commit).
4. Page size table for every HTML file.
5. Lighthouse-style checklist run by hand on the S9 browser; note the scores.
6. Internal link crawler script (stdlib) with a failing-test mode.
7. Alt-text lint.
8. Sitemap regenerated and verified against the crawler.
9. robots.txt check for the blog-drafts folder (must be excluded).
10. Tag site-baseline-2026-11.

### Phase 2: FAQ and speakable (11-20)
11. data/faq.json schema (question, answer, area, service, language).
12. Owner supplies 10 real questions.
13. FAQ page generator script.
14. FAQPage schema JSON-LD.
15. speakable JSON-LD on each answer.
16. check_schema_data.py extended for FAQ.
17. FAQ block on home (top 3).
18. FAQ blocks on area pages (filtered by area).
19. Voice assistant reads the same file (voice plan step 65).
20. Test: voice answer text == site FAQ text.

### Phase 3: local pages that earn their place (21-30)
21. Decide the service x area matrix (owner picks 3 services).
22. Area page template gains a service section with real photos only.
23. Generate pages only where content fields are non-empty.
24. Area map embed check (no third-party script unless already present).
25. "Service area" page listing all areas with travel notes (owner text).
26. Breadcrumb schema.
27. Internal links from blog posts to area pages by tag.
28. Crawler test for the new pages.
29. Sitemap update.
30. Tag site-local-pages.

### Phase 4: NAP, GBP, citations (31-40) [owner-gated]
31. site.json fields for address, phone, hours (empty until owner fills).
32. NAP component renders only when all fields exist.
33. LocalBusiness schema only when NAP exists (test).
34. GBP account created by owner; paste gbp-draft.json copy.
35. Review short link into review-sms-template.
36. /review page.
37. Citation list (citation-targets.json) with status per directory.
38. Manual citation submissions by owner (Yelp, HomeStars walls are human-only).
39. Consistency test: NAP on site == NAP in gbp-draft.json.
40. Tag site-nap.

### Phase 5: translation pipeline (41-55)
41. scripts/i18n/seek.py: pick template + glossary from page type.
42. seed.py: emit skeleton with slot ids.
43. shape.py: fill slots from the English source via Apertium (verify packages) or marked draft.
44. splice.py: single-writer merge into data/i18n/<lang>.json.
45. sift.py: Hunspell + glossary + ratio gate; bounded retry 2.
46. Fixtures for each stage; test_i18n.py extended.
47. Glossary files for the first 2 languages (owner checks terms).
48. Language choice: census data for Edmonton (owner verifies the numbers before use).
49. Build French fully through the pipeline; compare with the existing catalog.
50. Language 2 through the pipeline.
51. hreflang tags.
52. Language sitemap.
53. Language selector with localStorage.
54. Gate report in docs/STATUS.md (pass rate per language).
55. Tag site-i18n-2.

### Phase 6: store page (56-65)
56. Disclosure lint test.
57. No-invention lint test.
58. Removed-handle journal line.
59. Redirect click counter (local JSON, no cookies).
60. Weekly counts to data-exports.
61. Monthly cycle-out chore script (proposes; owner approves).
62. Low-stock link from the dashboard stock to store handle (dashboard plan step 31).
63. Store page i18n via the same pipeline (titles only; descriptions stay source).
64. Store sync daily log check in the housekeeper.
65. Tag site-store-hardened.

### Phase 7: leads and conversion (66-75)
66. Lead JSON shape shared with the voice intent (one schema file).
67. Form fields aligned to the schema.
68. Thank-you page.
69. Estimator "email me this" with consent checkbox.
70. Lead-tier sentence on the form.
71. Weekly visit-ping summary chore.
72. Enquiry log template in docs/ENQUIRIES.md updated to the schema.
73. Test: form field names == schema keys.
74. Spam honeypot field (no third-party).
75. Tag site-leads.

### Phase 8: performance and accessibility (76-85)
76. HTML size budget test.
77. CSS single file, minified by script (stdlib).
78. Defer all scripts; test no render-blocking.
79. WebP images with fallback.
80. Font: system stack only (no external fonts).
81. check_a11y.py extended for contrast and focus order.
82. Keyboard test of the estimator.
83. Reduced-motion respected everywhere.
84. Print stylesheet for the price sheet.
85. Tag site-perf.

### Phase 9: content cadence (86-93)
86. Monthly post slot from promo-calendar.json.
87. Posts need a sources field; lint.
88. Owner review checklist for drafts.
89. Before/after gallery pairs (owner photos).
90. Testimonials from real reviews only (sync_reviews.py; test).
91. Social links verified live by owner.
92. Newsletter: NOT built unless consent flow is agreed (CASL).
93. Tag site-content.

### Phase 10: domain and launch review (94-100)
94. Domain decision by owner (register or not).
95. If registered: CNAME, canonicalBase, Pages custom domain, HTTPS check.
96. Redirect map from github.io to the domain.
97. Search Console verification (free) by owner.
98. 30-day traffic read (counts only) in STATUS.md.
99. Decide languages 3-5 from measured traffic.
100. Update this file: tick, date, roll open items forward.

## Risks named plainly
- Doorway or thin pages (service x area, machine translation) can lower ranking; every generated page needs real content.
- LocalBusiness schema with a missing address is worse than none; keep it gated.
- The domain is still unregistered; canonical stays empty until it resolves.
- No invented reviews, photos, prices, or hours. Hidden sections until real data exists.
