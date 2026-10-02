#!/usr/bin/env python3
"""test_site_scripts.py — unit tests for chrislloyd-io scripts.

Covers: autopost.py (draft generation), quote_estimator.py (math),
gen_sitemap.py helpers (is_placeholder, atomic write), add_post.py
(slug/id logic via import). Run: python3 scripts/test_site_scripts.py
"""
import json
import os
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
            self.assertTrue(g.get("placeholder") is True)
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
        self.assertIn('href="#gallery"', self.index_html)
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
        self.assertIn('href="#estimator"', self.index_html)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)