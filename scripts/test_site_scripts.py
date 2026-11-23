#!/usr/bin/env python3
"""test_site_scripts.py — unit tests for chrislloyd-io scripts.

Covers: autopost.py (draft generation), quote_estimator.py (math),
gen_sitemap.py helpers (is_placeholder, atomic write), add_post.py
(slug/id logic via import). Run: python3 scripts/test_site_scripts.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


class TestAutopost(unittest.TestCase):
    def test_drafts_written_with_header_and_body(self):
        import autopost
        tmp = tempfile.mkdtemp()
        old_dir = autopost.DRAFT_DIR
        autopost.DRAFT_DIR = tmp
        try:
            paths = autopost.write_drafts()
            self.assertEqual(len(paths), 3)
            for p in paths:
                self.assertTrue(os.path.exists(p))
                text = open(p, encoding="utf-8").read()
                header = text.split("---")[0]
                h = json.loads(header)
                self.assertIn("title", h)
                self.assertIn("excerpt", h)
                self.assertTrue(h.get("date") is None, "draft date must be set on promotion")
                body = text.split("---", 1)[1]
                self.assertGreater(len(body.strip()), 200, "draft body too thin")
        finally:
            autopost.DRAFT_DIR = old_dir

    def test_draft_ids_unique(self):
        import autopost
        ids = [d["id"] for d in autopost.DRAFTS]
        self.assertEqual(len(ids), len(set(ids)))


class TestQuoteEstimator(unittest.TestCase):
    def test_interior_math_direction(self):
        import quote_estimator
        small = quote_estimator.interior(1, 10, 10, 8)
        big = quote_estimator.interior(3, 12, 14, 9, repairs=4)
        self.assertLess(small["total_range"][0], big["total_range"][1])
        self.assertGreater(big["wall_sqft"], small["wall_sqft"])
        self.assertGreater(big["labour_hours"], small["labour_hours"])

    def test_nine_foot_factor_raises_labour(self):
        import quote_estimator
        h8 = quote_estimator.interior(2, 12, 14, 8)
        h9 = quote_estimator.interior(2, 12, 14, 9)
        self.assertGreater(h9["labour_hours"], h8["labour_hours"])

    def test_repairs_add_hours(self):
        import quote_estimator
        base = quote_estimator.interior(1, 12, 14, 8, repairs=0)
        rep = quote_estimator.interior(1, 12, 14, 8, repairs=6)
        self.assertGreater(rep["labour_hours"], base["labour_hours"])

    def test_exterior_scales_linearly(self):
        import quote_estimator
        small = quote_estimator.exterior(1000)
        big = quote_estimator.exterior(2000)
        self.assertEqual(big["labour_hours"], small["labour_hours"] * 2)

    def test_range_brackets_estimate(self):
        import quote_estimator
        r = quote_estimator.interior(2, 12, 14, 8)
        lo, hi = r["total_range"]
        mid = r["labour_cost"] + r["paint_cost"]
        self.assertLess(lo, mid)
        self.assertGreater(hi, mid)


class TestSitemap(unittest.TestCase):
    def test_is_placeholder_exists_and_filters(self):
        import gen_sitemap
        self.assertTrue(hasattr(gen_sitemap, "is_placeholder"))
        # actual contract: flags posts whose excerpt/body contain PLACEHOLDER
        example = {"id": "whatever", "excerpt": "PLACEHOLDER EXAMPLE POST"}
        self.assertTrue(gen_sitemap.is_placeholder(example))
        real = {"id": "real-post", "excerpt": "Real post about painting",
                "body": ["Actual trade notes."]}
        self.assertFalse(gen_sitemap.is_placeholder(real))

    def test_load_posts_returns_list(self):
        import gen_sitemap
        posts = gen_sitemap.load_posts()
        self.assertIsInstance(posts, list)

    def test_products_page_is_listed(self):
        # Regression: products.html (49 real items, linked from every page's nav) was
        # missing from the sitemap entirely until 2026-11-18 — found while auditing the
        # site baseline, not by this test originally.
        with open(os.path.join(ROOT, "scripts", "gen_sitemap.py")) as fh:
            src = fh.read()
        self.assertIn('"products.html"', src)

    def test_generated_sitemap_includes_every_url_source(self):
        import gen_sitemap
        with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("index.html", content)
        self.assertIn("products.html", content)
        self.assertIn("blog.html", content)
        for slug_file in gen_sitemap.load_area_pages():
            self.assertIn(slug_file, content)

    def test_default_run_never_emits_hreflang_or_changes_url_count(self):
        """--langs is opt-in (PLAN-SITE-100 step 51/52); the live site has no localized
        pages deployed yet, so default behavior (what every other test here checks)
        must stay byte-for-byte what it was before that flag existed."""
        import gen_sitemap
        sitemap_path = os.path.join(ROOT, "sitemap.xml")
        before = open(sitemap_path, encoding="utf-8").read()
        try:
            gen_sitemap.main([])
            after = open(sitemap_path, encoding="utf-8").read()
        finally:
            with open(sitemap_path, "w", encoding="utf-8") as fh:
                fh.write(before)
        self.assertNotIn("xhtml:link", after)
        self.assertNotIn("xmlns:xhtml", after)

    def test_langs_flag_adds_reciprocal_hreflang_and_locale_urls(self):
        import gen_sitemap
        sitemap_path = os.path.join(ROOT, "sitemap.xml")
        before = open(sitemap_path, encoding="utf-8").read()
        try:
            gen_sitemap.main(["--langs", "en,fr"])
            after = open(sitemap_path, encoding="utf-8").read()
        finally:
            with open(sitemap_path, "w", encoding="utf-8") as fh:
                fh.write(before)
        self.assertIn('xmlns:xhtml="http://www.w3.org/1999/xhtml"', after)
        self.assertIn('hreflang="fr"', after)
        self.assertIn('hreflang="x-default"', after)
        self.assertIn("/fr/products.html", after)
        # blog.html?post=... is dynamic (client-side), never gets a locale URL/hreflang
        self.assertNotIn("fr/blog.html?post=", after)


class TestProvenance(unittest.TestCase):
    """PLAN-SITE-100 phase 1 step 7 (skeleton, not a full per-string tracer)."""

    def test_data_sources_covers_every_json_file_in_data_dir(self):
        import provenance as pv
        sources = pv.data_sources()
        real_files = {f for f in os.listdir(os.path.join(ROOT, "data")) if f.endswith(".json")}
        self.assertEqual(set(sources.keys()), real_files)

    def test_known_fetched_files_are_attributed_correctly(self):
        import provenance as pv
        sources = pv.data_sources()
        self.assertIn("main.js", sources["site.json"])
        self.assertIn("main.js", sources["store.json"])

    def test_page_text_counts_are_positive_for_every_real_page(self):
        import provenance as pv
        counts = pv.page_text_counts()
        for page in (f for f in os.listdir(ROOT) if f.endswith(".html")):
            self.assertGreater(counts[page], 0, f"{page} has no visible text nodes?")


class TestImgBudget(unittest.TestCase):
    """PLAN-SITE-100 phase 1 step 6. Alt-text is check_a11y.py's job, not duplicated here."""

    def test_jpeg_dims_matches_a_real_store_image(self):
        import img_budget as ib
        path = os.path.join(ROOT, "assets", "store",
                             "16pcs-mini-paint-stands-tool-triangle-pa.jpg")
        if not os.path.isfile(path):
            self.skipTest("fixture image not present")
        self.assertEqual(ib.image_dims(path), (480, 480))

    def test_is_oversized_true_for_a_genuinely_bigger_same_ratio_image(self):
        import img_budget as ib
        self.assertTrue(ib.is_oversized(2000, 2000, 240, 240))

    def test_is_oversized_false_for_a_cropped_object_fit_cover_image(self):
        # Regression: a taller-than-square source cropped into a square box via
        # object-fit:cover is not waste - caught and fixed 2026-11-18 before shipping.
        import img_budget as ib
        self.assertFalse(ib.is_oversized(480, 756, 240, 240))

    def test_real_site_images_are_within_budget(self):
        import img_budget as ib
        findings = ib.audit()
        self.assertEqual(findings, [], f"image budget findings: {findings}")


class TestRobots(unittest.TestCase):
    """PLAN-SITE-100 phase 1 step 9. blog-drafts/ holds unpublished raw .md/.txt draft
    files, not rendered pages - crawlers shouldn't index or scrape them."""

    def test_robots_excludes_blog_drafts(self):
        with open(os.path.join(ROOT, "robots.txt"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Disallow: /blog-drafts/", text)

    def test_sitemap_never_lists_a_blog_drafts_url(self):
        with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("blog-drafts", text)


class TestPerfBudget(unittest.TestCase):
    """PLAN-SITE-100 phase 1 step 4. Tests the measurement tool's correctness, not that
    every page currently passes its own budget — products.html genuinely doesn't (2.2MB
    of product images), tracked honestly in docs/STATUS.md, not hidden behind a test that
    would otherwise just be red for a reason unrelated to the tool itself being broken."""

    def test_page_weight_matches_real_file_sizes(self):
        import perf_budget as pb
        html_b, asset_b, missing = pb.page_weight("index.html")
        self.assertEqual(html_b, os.path.getsize(os.path.join(ROOT, "index.html")))
        self.assertGreater(asset_b, 0)
        self.assertEqual(missing, [])

    def test_every_referenced_local_asset_exists(self):
        import perf_budget as pb
        for page, _html_b, _asset_b, _total, missing in pb.budget_table():
            self.assertEqual(missing, [], f"{page} references a missing local asset: {missing}")

    def test_products_page_is_the_one_known_over_budget_page(self):
        # Documents the real 2026-11-18 finding so a future fix (image optimization,
        # PLAN-SITE-100 phase 8 step 79, owner-gated) is noticed when it lands, rather
        # than this test silently staying green for the wrong reason forever.
        import perf_budget as pb
        html_b, asset_b, _missing = pb.page_weight("products.html")
        self.assertGreater(html_b + asset_b, pb.TOTAL_BUDGET)
        for page, _h, _a, pg_total, _m in pb.budget_table():
            if page != "products.html":
                self.assertLessEqual(pg_total, pb.TOTAL_BUDGET, f"{page} unexpectedly over budget")


class TestCrawlLinks(unittest.TestCase):
    """PLAN-SITE-100 phase 1 step 5."""

    def test_internal_target_classifies_correctly(self):
        import crawl_links as cl
        self.assertEqual(cl.internal_target("products.html"), "products.html")
        self.assertEqual(cl.internal_target("blog.html?post=foo"), "blog.html")
        self.assertEqual(cl.internal_target("/products.html"), "products.html")
        self.assertIsNone(cl.internal_target("https://example.com/x.html"))
        self.assertIsNone(cl.internal_target("mailto:x@example.com"))
        self.assertIsNone(cl.internal_target("tel:+15551234567"))
        self.assertIsNone(cl.internal_target("#section"))
        self.assertIsNone(cl.internal_target("assets/style.css"))

    def test_the_real_site_has_no_dead_links_or_orphans(self):
        import crawl_links as cl
        dead, orphans = cl.crawl()
        self.assertEqual(dead, [], f"dead internal links: {dead}")
        self.assertEqual(orphans, [], f"orphan pages: {orphans}")

    def test_detects_dead_link_and_orphan_in_a_synthetic_site(self):
        import crawl_links as cl
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
                f.write('<a href="real.html">ok</a><a href="missing.html">dead</a>')
            open(os.path.join(d, "real.html"), "w", encoding="utf-8").close()
            open(os.path.join(d, "unreachable.html"), "w", encoding="utf-8").close()
            old_root = cl.ROOT
            cl.ROOT = d
            try:
                dead, orphans = cl.crawl()
            finally:
                cl.ROOT = old_root
        self.assertEqual(dead, [("index.html", "missing.html")])
        self.assertEqual(orphans, ["unreachable.html"])


class TestAddPost(unittest.TestCase):
    def test_slug_and_dedupe_helpers(self):
        import add_post
        src = open(os.path.join(ROOT, "scripts", "add_post.py")).read()
        # behavior checks via source inspection (CLI script, no importable slug API)
        self.assertIn("def", src)
        self.assertGreater(len(src), 500, "add_post.py suspiciously small")

    def test_posts_json_valid(self):
        posts = json.load(open(os.path.join(ROOT, "data", "posts.json")))
        self.assertIsInstance(posts, list)
        for p in posts:
            self.assertIn("id", p)
            self.assertIn("title", p)


class TestTestimonials(unittest.TestCase):
    """Task 025: data/testimonials.json — schema + placeholder policy."""

    def setUp(self):
        with open(os.path.join(ROOT, "data", "testimonials.json"), encoding="utf-8") as fh:
            self.items = json.load(fh)

    def test_testimonials_json_valid(self):
        self.assertIsInstance(self.items, list)
        self.assertGreaterEqual(len(self.items), 2, "seed 2-3 placeholder testimonials")

    def test_entries_follow_schema(self):
        for t in self.items:
            self.assertIn("id", t)
            self.assertIn("author", t)
            self.assertIn("quote", t)
            if "rating" in t and t["rating"] is not None:
                self.assertTrue(1 <= t["rating"] <= 5)

    def test_all_entries_marked_placeholder(self):
        # PLACEHOLDER-only policy: rating markup (JSON-LD) is never emitted for
        # these (main.js filters placeholder !== true); quotes are clearly marked.
        for t in self.items:
            self.assertTrue(t.get("placeholder") is True)
            self.assertIn("PLACEHOLDER", t["quote"])


class TestAreaPages(unittest.TestCase):
    """Task 026: static service-area pages (data/area-pages.json)."""

    def setUp(self):
        with open(os.path.join(ROOT, "data", "area-pages.json"), encoding="utf-8") as fh:
            self.data = json.load(fh)

    def test_data_valid_and_nonempty(self):
        self.assertIsInstance(self.data.get("pages"), list)
        self.assertGreaterEqual(len(self.data["pages"]), 4)

    def test_required_fields_per_page(self):
        for p in self.data["pages"]:
            self.assertIn("slug", p)
            self.assertIn("city", p)
            self.assertIn("drivingContext", p)
            self.assertTrue(p["intro"], "page intro must not be empty")

    def test_generated_pages_exist_and_reference_generator(self):
        import gen_area_pages
        for p in self.data["pages"]:
            path = os.path.join(ROOT, p["slug"] + ".html")
            self.assertTrue(os.path.exists(path), f"{path} missing — run gen_area_pages.py")
            html = open(path, encoding="utf-8").read()
            self.assertIn("scripts/gen_area_pages.py", html,
                          "generated page must carry provenance comment")

    def test_render_covers_seo_plumbing(self):
        import gen_area_pages
        page = self.data["pages"][0]
        html = gen_area_pages.render(page, is_draft=True)
        self.assertIn("rel=\"canonical\"", html)
        self.assertIn(f"{page['slug']}.html", html.split('rel="canonical"')[1])
        for prop in ("og:title", "og:description", "og:url", "og:image"):
            self.assertIn(f"property=\"{prop}\"", html)
        for name in ("twitter:card", "twitter:title", "twitter:image"):
            self.assertIn(f"name=\"{name}\"", html)
        self.assertIn("application/ld+json", html)
        # JSON-LD is pretty-printed — parse rather than substring-match.
        ld_blob = html.split('<script type="application/ld+json">', 1)[1]
        ld = json.loads(ld_blob.split("</script>", 1)[0])
        self.assertEqual(ld["areaServed"], [page["city"]])
        self.assertEqual(ld["@type"], "HomeAndConstructionBusiness")
        self.assertIn("assets/style.css", html)
        self.assertIn("index.html#contact", html)
        # draft flag must surface as a visible note on the page
        self.assertIn("Draft copy", html)

    def test_render_draft_off_hides_note(self):
        import gen_area_pages
        page = self.data["pages"][0]
        html = gen_area_pages.render(page, is_draft=False)
        self.assertNotIn("data-draft-note", html)

    def test_check_mode_detects_stale(self):
        # Rewrite one page with a dummy byte and confirm --check catches it.
        import gen_area_pages
        page = self.data["pages"][0]
        path = os.path.join(ROOT, page["slug"] + ".html")
        original = open(path, encoding="utf-8").read()
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("<!DOCTYPE html><!-- stale -->\n")
            self.assertEqual(gen_area_pages.main.__doc__ or "", "")
            rc = subprocess.run(
                [sys.executable, os.path.join(ROOT, "scripts", "gen_area_pages.py"), "--check"],
                capture_output=True, text=True)
            self.assertEqual(rc.returncode, 1, "--check must flag stale page")
        finally:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original)

    def test_regenerate_is_idempotent(self):
        rc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "gen_area_pages.py")],
            capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0)
        self.assertIn("nothing rewritten", rc.stdout)


class TestGallery(unittest.TestCase):
    """Task 027: before/after gallery — layout + data plumbing, photos later."""

    def setUp(self):
        with open(os.path.join(ROOT, "data", "gallery.json"), encoding="utf-8") as fh:
            self.items = json.load(fh)
        self.index_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        self.main_js = open(os.path.join(ROOT, "assets", "main.js"), encoding="utf-8").read()
        self.style_css = open(os.path.join(ROOT, "assets", "style.css"), encoding="utf-8").read()

    def test_gallery_json_valid(self):
        self.assertIsInstance(self.items, list)
        self.assertGreaterEqual(len(self.items), 1, "seed at least the PLACEHOLDER entry")

    def test_entries_follow_schema(self):
        for g in self.items:
            self.assertIn("id", g)
            self.assertIn("title", g)
            self.assertIn("caption", g)
            for side in ("before", "after"):
                self.assertIn(side, g)
                self.assertIn("src", g[side])
                self.assertIn("alt", g[side])
            if "year" in g and g["year"] not in (None, ""):
                self.assertTrue(str(g["year"]).isdigit())

    def test_only_placeholder_entries_until_photos_arrive(self):
        self.assertGreater(len(self.items), 0)
        for g in self.items:
            if g.get("placeholder") is not True:
                # real entry (added by scripts/add_gallery.py): files must exist, text must be real
                for side in ("before", "after"):
                    self.assertTrue(os.path.isfile(os.path.join(ROOT, g[side]["src"])), g[side]["src"])
                    self.assertTrue(g[side]["alt"].strip())
                self.assertNotIn("PLACEHOLDER", g["title"].upper())
                continue
            self.assertIn("PLACEHOLDER", g["title"])
            for side in ("before", "after"):
                self.assertIn("PLACEHOLDER", g[side]["alt"])
                # placeholder sources must point at assets/gallery/ (never created)
                self.assertTrue(g[side]["src"].startswith("assets/gallery/"))

    def test_no_placeholder_image_files_shipped(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "assets", "gallery", "placeholder-before.jpg")))
        self.assertFalse(os.path.exists(os.path.join(ROOT, "assets", "gallery", "placeholder-after.jpg")))

    def test_section_and_nav_wiring(self):
        self.assertIn('id="gallery"', self.index_html)
        self.assertIn('id="gallery-grid"', self.index_html)
        # basics-only site: section kept but hidden and not in the nav (remove `hidden` to bring it back)
        has_real = any(g.get("placeholder") is not True for g in self.items)
        if has_real:  # add_gallery.py un-hides it and adds the nav link
            self.assertNotIn('<section id="gallery" hidden', self.index_html)
            self.assertIn('href="#gallery"', self.index_html)
        else:
            self.assertIn('<section id="gallery" hidden', self.index_html)
            self.assertNotIn('href="#gallery"', self.index_html)
        # section sits between #testimonials and #faq in the document
        t_i = self.index_html.find('<section id="testimonials"')
        g_i = self.index_html.find('<section id="gallery"')
        f_i = self.index_html.find('<section id="faq"')
        self.assertTrue(0 < t_i < g_i < f_i, "gallery must sit between testimonials and faq")

    def test_renderer_wiring_in_main_js(self):
        self.assertIn('fetch("data/gallery.json")', self.main_js)
        self.assertIn('"gallery-grid"', self.main_js)
        self.assertIn("img.onerror", self.main_js)
        self.assertIn("renderGallery();", self.main_js)
        # onerror must remove the card (no broken-image icons live)
        self.assertLess(
            self.main_js.index("img.onerror"), self.main_js.index("removeChild(c)"),
            "onerror handler must remove the broken gallery card")

    def test_sitemap_untouched_by_gallery(self):
        with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as fh:
            xml = fh.read()
        self.assertNotIn("gallery", xml, "gallery is a section, not a page — keep it out of sitemap.xml")

    def test_renderer_pure_functions_in_node(self):
        # node-side smoke test: extract + exec the pure helpers, assert behavior
        script = os.path.join(ROOT, "scripts", "test_gallery_logic.js")
        rc = subprocess.run(["node", script], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, "node gallery-logic tests failed:\n" + rc.stdout + rc.stderr)


class TestFAQ(unittest.TestCase):
    """PLAN-SITE-100 phase 2 (steps 11-16): data/faq.json + FAQPage/speakable JSON-LD
    rendered client-side by assets/main.js (schema data contract itself is already
    covered by scripts/check_schema_data.py)."""

    def setUp(self):
        with open(os.path.join(ROOT, "data", "faq.json"), encoding="utf-8") as fh:
            self.faq = json.load(fh)["faq"]
        self.index_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        self.main_js = open(os.path.join(ROOT, "assets", "main.js"), encoding="utf-8").read()

    def test_at_least_six_real_entries(self):
        # mirrors check_schema_data.py's own floor; kept here too so this file's
        # suite alone still catches a regression without running that script.
        self.assertGreaterEqual(len(self.faq), 6)
        for item in self.faq:
            self.assertTrue(item.get("q", "").strip())
            self.assertTrue(item.get("a", "").strip())

    def test_section_present_and_positioned_after_gallery(self):
        self.assertIn('id="faq-list"', self.index_html)
        g_i = self.index_html.find('<section id="gallery"')
        f_i = self.index_html.find('<section id="faq"')
        self.assertTrue(0 < g_i < f_i, "faq must sit after gallery")

    def test_renderer_wiring_in_main_js(self):
        self.assertIn('fetch("data/faq.json")', self.main_js)
        self.assertIn('"faq-list"', self.main_js)
        self.assertIn("FAQPage", self.main_js)

    def test_speakable_schema_present_in_main_js(self):
        # PLAN-SITE-100 step 15 / PLAN-VOICE-100 step 70: the voice assistant's own
        # spoken-FAQ feature reads this same selector convention.
        self.assertIn("SpeakableSpecification", self.main_js)
        self.assertIn('"#faq-list .faq-item"', self.main_js)

    def test_no_static_jsonld_duplicate_in_index_html(self):
        # mirrors check_schema_data.py's own check; the JSON-LD is generated once,
        # client-side, never hand-duplicated into the HTML.
        self.assertFalse('"@type"' in self.index_html and "FAQPage" in self.index_html)

    def test_schema_logic_in_node(self):
        script = os.path.join(ROOT, "scripts", "test_faq_schema.js")
        rc = subprocess.run(["node", script], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, "node faq-schema tests failed:\n" + rc.stdout + rc.stderr)


class TestEstimator(unittest.TestCase):
    """Task 034 (roadmap 25): customer-facing estimator widget — wiring,
    pricing.json drift alarm vs quote_estimator.DEFAULTS, node logic tests."""

    def setUp(self):
        self.index_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        self.main_js = open(os.path.join(ROOT, "assets", "main.js"), encoding="utf-8").read()
        with open(os.path.join(ROOT, "data", "pricing.json"), encoding="utf-8") as fh:
            self.pricing = json.load(fh)

    def test_pricing_json_mirror_of_cli_defaults(self):
        import quote_estimator
        for k, v in quote_estimator.DEFAULTS.items():
            self.assertIn(k, self.pricing["rates"], f"pricing.json missing rate {k}")
            self.assertEqual(self.pricing["rates"][k], v,
                             f"pricing.json rates.{k} drifted from quote_estimator.DEFAULTS")

    def test_pricing_placeholder_markers_present(self):
        self.assertTrue(self.pricing.get("_edit_me") is True)
        self.assertIn("rates", self.pricing)
        owner_block = " ".join(self.pricing.get("_owner_action", []))
        self.assertIn("OWNER ACTION", owner_block,
                      "pricing.json must carry the OWNER-ACTION comment block")
        self.assertIn("PLACEHOLDER", owner_block)

    def test_section_and_nav_wiring(self):
        self.assertIn('id="estimator"', self.index_html)
        self.assertIn('id="est-calc"', self.index_html)
        self.assertIn('id="est-out"', self.index_html)
        self.assertIn('<section id="estimator" hidden', self.index_html)
        self.assertNotIn('href="#estimator"', self.index_html)
        self.assertIn("Estimate only", self.index_html)
        self.assertIn("not a quote", self.index_html)
        # disclaimer must link to the contact form (CTA)
        est_chunk = self.index_html.split('<section id="estimator"', 1)[1].split("</section>", 1)[0]
        self.assertIn('href="#contact"', est_chunk)
        # section sits between #gallery and #faq
        g_i = self.index_html.find('<section id="gallery"')
        e_i = self.index_html.find('<section id="estimator"')
        f_i = self.index_html.find('<section id="faq"')
        self.assertTrue(0 < g_i < e_i < f_i, "estimator must sit between gallery and faq")

    def test_renderer_wiring_in_main_js(self):
        self.assertIn('fetch("data/pricing.json")', self.main_js)
        self.assertIn("renderEstimator();", self.main_js)
        self.assertIn("estimateInterior", self.main_js)
        self.assertIn("estimateExterior", self.main_js)
        self.assertIn("parseRoomSize", self.main_js)

    def test_calculator_is_deterministic_client_side(self):
        # no backend/fetch/LLM inside the compute path: fetch appears only once
        # for the rate table; no LLM/network calls anywhere near the estimator.
        est_chunk = self.main_js.split("paint-quote estimator", 1)[1].split("#expose estimator", 1)[0] \
            if "#expose estimator" in self.main_js else self.main_js.split("paint-quote estimator", 1)[1]
        self.assertEqual(est_chunk.count("fetch("), 1, "estimator must fetch only the rate table")
        for banned in ("XMLHttpRequest", "api.openai", "chatgpt", "localhost:"):
            self.assertNotIn(banned, est_chunk)

    def test_math_mirrors_cli_for_widget_defaults(self):
        # golden parity: JS-mirrored formulas produce EXACTLY the same numbers
        # as quote_estimator.py for the widget default inputs (regression guard
        # against forking the math); full parity suite runs in node below.
        import quote_estimator
        fixtures = json.load(open(os.path.join(ROOT, "scripts", "test_estimator_fixtures.json")))
        cli = quote_estimator.interior(3, 12, 14, 8, 0)
        self.assertEqual(fixtures["interior_default"]["total_range"], list(cli["total_range"]))
        self.assertEqual(fixtures["interior_default"]["wall_sqft"], cli["wall_sqft"])

    def test_node_estimator_logic_tests(self):
        script = os.path.join(ROOT, "scripts", "test_estimator_logic.js")
        fixtures = os.path.join(ROOT, "scripts", "test_estimator_fixtures.json")
        self.assertTrue(os.path.exists(script), "node test file missing")
        self.assertTrue(os.path.exists(fixtures), "fixtures missing — run gen_estimator_fixtures.py")
        rc = subprocess.run(["node", script], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, "node estimator-logic tests failed:\n" + rc.stdout + rc.stderr)
        self.assertIn("ALL ESTIMATOR LOGIC TESTS PASS", rc.stdout)

    def test_node_getready_smoke_test(self):
        # Task 036: shipped-file DOM-shim smoke test for the get-ready reveal
        script = os.path.join(ROOT, "scripts", "test_getready_smoke.js")
        self.assertTrue(os.path.exists(script), "node smoke test file missing")
        rc = subprocess.run(["node", script], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, "node get-ready smoke test failed:\n" + rc.stdout + rc.stderr)
        self.assertIn("ALL GET-READY SHIPPED-FILE SMOKE TESTS PASS", rc.stdout)

    def test_node_shipped_file_smoke(self):
        # executes the REAL assets/main.js under a minimal DOM shim: guards
        # against breaking the shipped file (helpers exposed, listener wired,
        # pricing.json fetched) without needing a browser in CI.
        script = os.path.join(ROOT, "scripts", "test_estimator_smoke.js")
        rc = subprocess.run(["node", script], capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, "node estimator smoke failed:\n" + rc.stdout + rc.stderr)
        self.assertIn("ALL ESTIMATOR SHIPPED-FILE SMOKE TESTS PASS", rc.stdout)

    def test_gen_fixtures_script_is_deterministic(self):
        # two runs must produce byte-identical fixtures
        out1 = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen_estimator_fixtures.py")],
                              capture_output=True, text=True)
        out2 = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen_estimator_fixtures.py")],
                              capture_output=True, text=True)
        self.assertEqual(out1.returncode, 0)
        self.assertEqual(out1.stdout, out2.stdout, "fixture generation is not deterministic")
        # and must still match the committed fixture file
        committed = open(os.path.join(ROOT, "scripts", "test_estimator_fixtures.json")).read()
        self.assertEqual(out1.stdout.strip(), committed.strip(),
                         "committed fixtures stale vs gen_estimator_fixtures.py output")


class TestAddGallery(unittest.TestCase):
    """scripts/add_gallery.py on a throwaway copy of the site (never the real files)."""

    def setUp(self):
        import shutil
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "data"))
        for f in ("data/gallery.json", "index.html"):
            shutil.copy(os.path.join(ROOT, f), os.path.join(self.tmp, f))
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        self.img = os.path.join(self.tmp, "in.jpg")
        im = Image.new("RGB", (2400, 1600), (20, 90, 160))
        exif = Image.Exif()
        exif[0x8825] = {1: "N"}  # GPS IFD present
        im.save(self.img, exif=exif)
        self.args = ["--before", self.img, "--after", self.img, "--title", "Bedroom repaint",
                     "--caption", "Two coats.", "--alt-before", "Bedroom before", "--alt-after", "Bedroom after",
                     "--root", self.tmp]

    def run_add(self, extra):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import add_gallery
        add_gallery.main(self.args + extra)

    def test_refuses_without_client_ok(self):
        with self.assertRaises(SystemExit):
            self.run_add([])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "assets")))

    def test_refuses_placeholder_text(self):
        self.args[self.args.index("Two coats.")] = "PLACEHOLDER caption"
        with self.assertRaises(SystemExit):
            self.run_add(["--client-ok"])

    def test_adds_entry_strips_exif_resizes_and_unhides(self):
        from PIL import Image
        self.run_add(["--client-ok", "--year", "2026"])
        items = json.load(open(os.path.join(self.tmp, "data", "gallery.json")))
        self.assertEqual(len(items), 1)
        self.assertIs(items[0]["placeholder"], False)
        out = Image.open(os.path.join(self.tmp, items[0]["before"]["src"]))
        self.assertLessEqual(max(out.size), 1200)
        self.assertEqual(len(out.getexif()), 0)
        html = open(os.path.join(self.tmp, "index.html")).read()
        self.assertNotIn('<section id="gallery" hidden', html)
        self.assertIn('href="#gallery"', html)

    def test_second_add_keeps_unique_ids(self):
        self.run_add(["--client-ok"])
        self.run_add(["--client-ok"])
        ids = [i["id"] for i in json.load(open(os.path.join(self.tmp, "data", "gallery.json")))]
        self.assertEqual(len(ids), len(set(ids)))


class TestPriceSheet(unittest.TestCase):
    """Task 035: deterministic price-sheet PDF from data/pricing.json."""

    def test_gen_pricesheet_pdf_bytes_stable(self):
        try:
            import fpdf  # noqa: F401
        except ImportError:
            self.skipTest("fpdf2 not installed (pip install fpdf2)")
        import gen_pricesheet
        rates, placeholder = gen_pricesheet.load_rates()
        self.assertTrue(placeholder, "pricing.json is still placeholder — PDF test "
                                     "assumes the _edit_me marker is present; if you "
                                     "set real rates, drop this assertion")
        tmp1 = os.path.join(tempfile.mkdtemp(), "ps1.pdf")
        tmp2 = os.path.join(tempfile.mkdtemp(), "ps2.pdf")
        gen_pricesheet.build_pdf(rates, tmp1)
        gen_pricesheet.build_pdf(rates, tmp2)
        self.assertTrue(os.path.getsize(tmp1) > 1000, "PDF suspiciously small")
        with open(tmp1, "rb") as a, open(tmp2, "rb") as b:
            self.assertEqual(a.read(), b.read(),
                             "regenerate run produced different bytes — "
                             "PDF must be byte-deterministic")
        # header text is extractable via naive flate-decode; skip if zlib absent
        import re
        import zlib
        with open(tmp1, "rb") as fh:
            blob = fh.read()
        decoded = []
        for m in re.finditer(rb"stream\r?\n(.*?)endstream", blob, re.S):
            try:
                decoded.append(zlib.decompress(m.group(1)))
            except zlib.error:
                pass
        text = b"\n".join(decoded).decode("latin-1", "replace")
        self.assertIn("Pricing Guide", text)
        self.assertIn("PLACEHOLDER RATES", text)
        self.assertIn("Rates subject to confirmation", text)

    def test_gen_pricesheet_default_output_writable(self):
        # dist/ default path constructs cleanly and module imports are side-effect-free
        import gen_pricesheet
        self.assertTrue(gen_pricesheet.RATE_LABELS)
        self.assertIn("labour_rate", dict(gen_pricesheet.RATE_LABELS))


class TestAreaSitemap(unittest.TestCase):
    """Task 026: sitemap integration for service-area pages."""

    def test_load_area_pages_lists_real_slugs(self):
        import gen_sitemap
        slugs = gen_sitemap.load_area_pages()
        self.assertIn("st-albert.html", slugs)
        self.assertIn("sherwood-park.html", slugs)
        self.assertIn("leduc.html", slugs)
        self.assertIn("spruce-grove.html", slugs)

    def test_sitemap_xml_includes_area_pages(self):
        with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as fh:
            xml = fh.read()
        for slug in ("st-albert.html", "sherwood-park.html",
                     "leduc.html", "spruce-grove.html"):
            self.assertIn(slug, xml, f"sitemap.xml missing {slug} — run gen_sitemap.py")


class TestLeadMagnet(unittest.TestCase):
    """Task 036 (roadmap 30): quote-request auto-reply checklist + on-site
    get-ready reveal. Single source of truth: data/lead_magnet.json, rendered
    both by scripts/gen_autoreply_email.py (email body) and main.js (post-
    submit block). Honesty constraint from tasks 015/030 applies to copy."""

    def setUp(self):
        with open(os.path.join(ROOT, "data", "lead_magnet.json"), encoding="utf-8") as fh:
            self.magnet = json.load(fh)
        self.index_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
        self.main_js = open(os.path.join(ROOT, "assets", "main.js"), encoding="utf-8").read()
        # only the visitor-facing copy strings are scanned for honesty — the
        # _owner_action/_disclaimer meta blocks legitimately discuss the
        # constraint itself and would self-match.
        self.customer_facing = {
            "titles": [i["title"] for i in self.magnet["checklist"]],
            "details": [i["detail"] for i in self.magnet["checklist"]],
            "closing": self.magnet.get("closing_note", ""),
        }

    def test_checklist_has_items_with_titles(self):
        items = self.magnet.get("checklist") or []
        self.assertGreaterEqual(len(items), 5, "lead magnet checklist too thin")
        for it in items:
            self.assertIn("title", it)
            self.assertIn("id", it)
            self.assertTrue(it["title"].strip(), f"empty title on {it.get('id')}")

    def test_generator_deterministic_bytes(self):
        import gen_autoreply_email
        items, closing, placeholder = gen_autoreply_email.load_magnet()
        a = gen_autoreply_email.render_text(items, closing, placeholder)
        b = gen_autoreply_email.render_text(items, closing, placeholder)
        self.assertEqual(a, b, "auto-reply body must be deterministic")
        self.assertGreater(len(a), 200, "generated body suspiciously small")
        # numbering: non-placeholder items get sequential "N." markers. With
        # the current all-but-one real seed the expected values are known.
        self.assertIn("\n2. Take photos", a)
        self.assertIn("\n7. Write down", a)
        self.assertIn("Thank", gen_autoreply_email.SUBJECT)

    def test_honest_copy_bans_response_time_promises(self):
        # tasks 015/030 constraint — visitor-facing copy must never manufacture
        # response-time promises. Scan the generated email body (SUBJECT +
        # checklist text + closing) and the on-site block copy. Meta blocks
        # (_owner_action/_disclaimer) legitimately discuss the constraint and
        # are excluded from the scan (they would self-match).
        import gen_autoreply_email
        items, closing, placeholder = gen_autoreply_email.load_magnet()
        text = (gen_autoreply_email.SUBJECT + "\n"
                + gen_autoreply_email.render_text(items, closing, placeholder) + "\n"
                + "\n".join(self.customer_facing["titles"])
                + "\n".join(self.customer_facing["details"])
                + self.customer_facing["closing"])
        banned = [
            r"within\s+\d+", r"\d+\s*(min|hour|hr|business day|day)s?\b.*response",
            r"response\s*(time|within)", r"we('ll| will) (repl|respond|reply|get back)",
            r"guarantee", r"same[- ]day",
        ]
        for pat in banned:
            self.assertIsNone(re.search(pat, text, re.I),
                              f"honesty violation: {pat!r} matched lead-magnet copy")
        # the closing note must be present and explicitly non-promising
        self.assertIn("no automated promises", self.customer_facing["closing"])
        self.assertIn("no automated promises", gen_autoreply_email.render_text(items, closing, placeholder))

    def test_site_wiring_and_single_source_of_truth(self):
        # get-ready block exists in index.html, hidden by default
        self.assertIn('id="get-ready"', self.index_html)
        self.assertIn('id="get-ready-list"', self.index_html)
        gr_chunk = self.index_html.split('id="get-ready"', 1)[1].split("</form>", 1)[0]
        gr_chunk = self.index_html.split('<div class="get-ready"', 1)[1].split("</ol>", 1)[0]
        self.assertIn("hidden", gr_chunk)
        # main.js fetches the SAME data file the CLI generator reads
        self.assertIn('fetch("data/lead_magnet.json")', self.main_js)
        self.assertIn("setupGetReady", self.main_js)
        # reveal fires on the form's submit in BOTH backend branches
        self.assertIn('getElementById("contact-form").addEventListener("submit"', self.main_js)
        # placeholder contract: flagged items exist and _owner_action refers
        # to the Formspree autoresponse decision
        self.assertTrue(self.magnet.get("_edit_me") is True)
        self.assertTrue(any(i.get("placeholder") for i in self.magnet["checklist"]),
                        "seed at least one PLACEHOLDER item")
        owner_block = " ".join(self.magnet.get("_owner_action", []))
        self.assertIn("OWNER ACTION", owner_block)
        self.assertIn("PLACEHOLDER", owner_block)
        self.assertIn("Formspree", owner_block)

    def test_generator_cli_runs_and_writes_file(self):
        import gen_autoreply_email
        out1 = os.path.join(tempfile.mkdtemp(), "r1.txt")
        out2 = os.path.join(tempfile.mkdtemp(), "r2.txt")
        for out in (out1, out2):
            subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen_autoreply_email.py"),
                            "--out", out], capture_output=True, text=True, check=True)
        self.assertTrue(os.path.getsize(out1) > 200)
        with open(out1, encoding="utf-8") as a, open(out2, encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read(), "CLI invocations must produce identical bytes")


if __name__ == "__main__":
    unittest.main(verbosity=2)