#!/usr/bin/env python3
"""test_area_faq.py — task 106: area-filtered FAQ blocks on generated area pages.

Covers scripts/gen_area_pages.py (faq_for / static FAQ section / FAQPage JSON-LD)
and the two area-FAQ checks added to scripts/check_schema_data.py. Tests 1-3 are
pure/fixture-based; tests 4-6 verify the regenerated repo pages.

Run: python3 scripts/test_area_faq.py
"""
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gen_area_pages

ENTRIES = [
    {"q": "Q tagged for one page?", "a": "A one.", "areas": ["st-albert"]},
    {"q": "Q tagged for all pages?", "a": "A all.", "areas": ["all"]},
    {"q": "Q untagged?", "a": "A none."},
]

# The pre-FAQ area-page chrome: FAQ step must add zero new JS to these pages.
CHROME_SCRIPT_SRC = {"assets/i18n.js", "assets/fx.js", "assets/visit-ping.js"}


def area_slugs():
    with open(os.path.join(ROOT, "data", "area-pages.json"), encoding="utf-8") as fh:
        return [p["slug"] for p in json.load(fh)["pages"]]


def ld_blocks(html):
    out = []
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                         html, re.DOTALL):
        out.append(json.loads(m.group(1)))
    return out


class TestAreaFAQ(unittest.TestCase):
    """Task 106: static, no-JS FAQ blocks on the four generated area pages."""

    def test_faq_for_filters_by_slug(self):
        got = gen_area_pages.faq_for("st-albert", ENTRIES)
        self.assertEqual([e["q"] for e in got],
                         ["Q tagged for one page?", "Q tagged for all pages?"])
        got = gen_area_pages.faq_for("leduc", ENTRIES)
        self.assertEqual([e["q"] for e in got], ["Q tagged for all pages?"])
        # entries without "areas" never match anywhere, even for a real slug
        self.assertNotIn("Q untagged?", [e["q"] for e in got])
        # unknown slug -> [] (fixture without any "all"-tagged entry)
        self.assertEqual(
            gen_area_pages.faq_for("bonnyville", [ENTRIES[0], ENTRIES[2]]), [])

    def test_faq_for_matches_all(self):
        for slug in area_slugs():
            got = gen_area_pages.faq_for(slug, ENTRIES)
            self.assertIn("Q tagged for all pages?", [e["q"] for e in got],
                          f'alias "all" must surface for real slug {slug}')

    def test_gen_writes_faq_section_only_when_entries(self):
        page = {"slug": "st-albert", "city": "St. Albert", "region": "AB",
                "drivingContext": "northwest of Edmonton",
                "intro": ["Intro line for the fixture page."]}
        html = gen_area_pages.render(page, is_draft=False, faq_entries=ENTRIES)
        self.assertIn('class="wrap section section-alt area-faq"', html)
        self.assertEqual(html.count('<details class="faq-item"'), 2,
                         "section must show exactly the matching entries")
        faq_i = html.find('<section id="faq"')
        contact_i = html.find('<section id="contact"')
        self.assertTrue(0 < faq_i < contact_i, "FAQ section must precede the CTA")
        self.assertIn('"@type": "FAQPage"', html)
        self.assertLess(html.find('"@type": "FAQPage"'), html.find("</head>"))
        # a slug with no matches gets no section and no FAQPage JSON-LD
        # (fixture without the "all"-tagged entry, so nothing can match)
        html2 = gen_area_pages.render(dict(page, slug="bonnyville", city="Bonnyville"),
                                      is_draft=False, faq_entries=[ENTRIES[0], ENTRIES[2]])
        self.assertNotIn("area-faq", html2)
        self.assertNotIn('<section id="faq"', html2)
        self.assertNotIn("FAQPage", html2)

    def test_area_page_faqpage_jsonld_matches_section(self):
        for slug in area_slugs():
            html = open(os.path.join(ROOT, slug + ".html"), encoding="utf-8").read()
            fpage = [b for b in ld_blocks(html) if b.get("@type") == "FAQPage"]
            if not fpage:
                self.assertNotIn('<section id="faq"', html,
                                 f"[{slug}] section without matching FAQPage JSON-LD")
                continue
            faq_i = html.find('<section id="faq"')
            chunk = html[faq_i:html.find("</section>", faq_i)]
            ld_qs = [q["name"] for q in fpage[0]["mainEntity"]]
            ld_as = [q["acceptedAnswer"]["text"] for q in fpage[0]["mainEntity"]]
            sec_qs = re.findall(r"<summary>(.*?)</summary>", chunk, re.DOTALL)
            sec_as = re.findall(r"</summary><p>(.*?)</p></details>", chunk, re.DOTALL)
            self.assertEqual(ld_qs, sec_qs, f"[{slug}] questions")
            self.assertEqual(ld_as, sec_as, f"[{slug}] answers")

    def test_area_pages_stay_no_js(self):
        # FAQ feature adds zero JavaScript: area pages keep exactly the pre-FAQ
        # chrome scripts (i18n/fx/visit-ping, the year bootstrap) — no new <script
        # src>, no new inline script, and a purely static details/summary section.
        for slug in area_slugs():
            html = open(os.path.join(ROOT, slug + ".html"), encoding="utf-8").read()
            srcs = set(re.findall(r'<script[^>]*\bsrc="([^"]+)"', html))
            self.assertEqual(srcs, CHROME_SCRIPT_SRC, f"[{slug}] script src set changed")
            self.assertEqual(len(re.findall(r"<script\b", html)), 6,
                             f"[{slug}] script-tag count changed (3 src + 2 ld+json + year)")
            tags = re.findall(r"<script\b([^>]*)>", html)
            plain = [t for t in tags
                     if "src=" not in t and "application/ld+json" not in t]
            self.assertEqual(len(plain), 1)
            self.assertEqual({b.get("@type") for b in ld_blocks(html)},
                             {"HomeAndConstructionBusiness", "FAQPage"})
            faq_i = html.find('<section id="faq"')
            chunk = html[faq_i:html.find("</section>", faq_i)]
            self.assertNotIn("<script", chunk)
            self.assertNotIn("onclick", chunk)

    def test_check_schema_data_passes(self):
        rc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "scripts", "check_schema_data.py")],
            capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, rc.stdout + rc.stderr)
        self.assertIn('PASS faq.json areas reference real page slugs or "all"', rc.stdout)
        self.assertIn("PASS area pages: static FAQPage JSON-LD matches shown entries",
                      rc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
