#!/usr/bin/env python3
"""scripts/test_seo_lint.py -- seo_lint.py: metadata, JSON-LD, hreflang reciprocity.

  python3 -m unittest scripts.test_seo_lint
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo_lint  # noqa: E402

GOOD_TITLE = "Chris Lloyd Ltd — House Painters, Edmonton AB"
GOOD_DESC = "Edmonton house painters for interior and exterior residential work, plus honest supply reviews."


def _page(title=GOOD_TITLE, desc=GOOD_DESC, h1="<h1>Chris Lloyd Ltd</h1>", extra_head="", lang="en"):
    return (
        f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">'
        f'<title>{title}</title>'
        f'<meta name="description" content="{desc}">'
        f"{extra_head}</head><body>{h1}</body></html>"
    )


class MetadataLint(unittest.TestCase):
    def test_clean_page_has_no_issues(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page())
        page.close()
        self.assertEqual(seo_lint.lint_metadata(page.data), [])

    def test_title_too_short_flagged(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(title="Hi"))
        page.close()
        errs = seo_lint.lint_metadata(page.data)
        self.assertTrue(any("title length" in e for e in errs))

    def test_title_too_long_flagged(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(title="A" * 80))
        page.close()
        errs = seo_lint.lint_metadata(page.data)
        self.assertTrue(any("title length" in e for e in errs))

    def test_missing_h1_flagged(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(h1=""))
        page.close()
        errs = seo_lint.lint_metadata(page.data)
        self.assertTrue(any("exactly one <h1>" in e for e in errs))

    def test_two_h1_flagged(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(h1="<h1>A</h1><h1>B</h1>"))
        page.close()
        errs = seo_lint.lint_metadata(page.data)
        self.assertTrue(any("exactly one <h1>" in e for e in errs))

    def test_valid_json_ld_passes(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(extra_head='<script type="application/ld+json">{"@context":"https://schema.org","@type":"LocalBusiness"}</script>'))
        page.close()
        self.assertEqual(seo_lint.lint_metadata(page.data), [])

    def test_broken_json_ld_flagged(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(extra_head='<script type="application/ld+json">{not json}</script>'))
        page.close()
        errs = seo_lint.lint_metadata(page.data)
        self.assertTrue(any("invalid JSON-LD" in e for e in errs))

    def test_json_ld_missing_type_flagged(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page(extra_head='<script type="application/ld+json">{"@context":"https://schema.org"}</script>'))
        page.close()
        errs = seo_lint.lint_metadata(page.data)
        self.assertTrue(any("missing @context or @type" in e for e in errs))

    def test_page_with_no_json_ld_is_not_required_to_have_one(self):
        page = seo_lint._SEOParser("x.html", "en")
        page.feed(_page())
        page.close()
        self.assertEqual(page.data.json_ld_blocks, [])
        self.assertEqual(seo_lint.lint_metadata(page.data), [])


class HreflangReciprocity(unittest.TestCase):
    def test_page_without_any_hreflang_is_never_flagged(self):
        """Today's live root pages have zero hreflang tags -- must never be a false failure."""
        page = seo_lint._SEOParser("index.html", "en")
        page.feed(_page())
        page.close()
        errs = seo_lint.lint_hreflang_reciprocity({"https://x/index.html": page.data})
        self.assertEqual(errs, [])

    def test_reciprocal_pair_passes(self):
        en = seo_lint._SEOParser("index.html", "en")
        en.feed(_page(extra_head=(
            '<link rel="alternate" hreflang="en" href="https://x/">'
            '<link rel="alternate" hreflang="fr" href="https://x/fr/">'
            '<link rel="alternate" hreflang="x-default" href="https://x/">'
        )))
        en.close()
        fr = seo_lint._SEOParser("fr/index.html", "fr")
        fr.feed(_page(lang="fr", extra_head=(
            '<link rel="alternate" hreflang="en" href="https://x/">'
            '<link rel="alternate" hreflang="fr" href="https://x/fr/">'
            '<link rel="alternate" hreflang="x-default" href="https://x/">'
        )))
        fr.close()
        errs = seo_lint.lint_hreflang_reciprocity({"https://x/": en.data, "https://x/fr/": fr.data})
        self.assertEqual(errs, [])

    def test_one_sided_hreflang_is_flagged(self):
        en = seo_lint._SEOParser("index.html", "en")
        en.feed(_page(extra_head='<link rel="alternate" hreflang="fr" href="https://x/fr/">'))
        en.close()
        fr = seo_lint._SEOParser("fr/index.html", "fr")
        fr.feed(_page(lang="fr"))  # fr page has no hreflang back -> skipped as a page, but...
        fr.close()
        errs = seo_lint.lint_hreflang_reciprocity({"https://x/": en.data, "https://x/fr/": fr.data})
        self.assertTrue(any("not reciprocal" in e or "missing hreflang" in e for e in errs))

    def test_hreflang_target_not_found_is_flagged(self):
        en = seo_lint._SEOParser("index.html", "en")
        en.feed(_page(extra_head='<link rel="alternate" hreflang="fr" href="https://x/fr/">'))
        en.close()
        errs = seo_lint.lint_hreflang_reciprocity({"https://x/": en.data})
        self.assertTrue(any("unknown page" in e for e in errs))


class CanonicalUrl(unittest.TestCase):
    def test_index_html_collapses_to_trailing_slash(self):
        self.assertEqual(seo_lint.canonical_url_for("https://x", "index.html"), "https://x/")
        self.assertEqual(seo_lint.canonical_url_for("https://x", "index.html", "fr"), "https://x/fr/")

    def test_other_pages_keep_their_filename(self):
        self.assertEqual(seo_lint.canonical_url_for("https://x", "leduc.html"), "https://x/leduc.html")
        self.assertEqual(seo_lint.canonical_url_for("https://x", "leduc.html", "fr"), "https://x/fr/leduc.html")


class RunAgainstRealSite(unittest.TestCase):
    def test_the_real_live_site_passes_clean(self):
        root = Path(__file__).resolve().parent.parent
        errors, n = seo_lint.run([root], "https://chrisalunlloyd2-sudo.github.io/chrislloyd-io")
        self.assertEqual(errors, [])
        self.assertEqual(n, 7)

    def test_two_pages_with_a_broken_reciprocal_link_fail(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.html").write_text(_page(extra_head=(
                '<link rel="alternate" hreflang="en" href="https://x/a.html">'
                '<link rel="alternate" hreflang="fr" href="https://x/wrong.html">'
                '<link rel="alternate" hreflang="x-default" href="https://x/a.html">'
            )), encoding="utf-8")
            errors, n = seo_lint.run([Path(d)], "https://x")
            self.assertEqual(n, 1)
            self.assertTrue(any("unknown page" in e for e in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
