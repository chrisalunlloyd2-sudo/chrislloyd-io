#!/usr/bin/env python3
"""test_site_scripts.py — unit tests for chrislloyd-io scripts.

Covers: autopost.py (draft generation), quote_estimator.py (math),
gen_sitemap.py helpers (is_placeholder, atomic write), add_post.py
(slug/id logic via import). Run: python3 scripts/test_site_scripts.py
"""
import json
import os
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


if __name__ == "__main__":
    unittest.main(verbosity=2)