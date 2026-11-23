#!/usr/bin/env python3
"""scripts/test_phase5_site_i18n.py -- end-to-end tests for seek/seed/shape/splice/sift
against the REAL on-disk schema (list source.json, {"p","r"} fr.json, keep.json
allowlist, a separate .meta_<lang>.json sidecar for rich-entry staleness/provenance --
never inside fr.json itself). Synthetic fixtures only; never touches the live catalog.

  python3 -m unittest scripts.test_phase5_site_i18n
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("CLAUDE_LIFE_DIR", "/root/Claude/life")
sys.path.insert(0, os.environ["CLAUDE_LIFE_DIR"])

import _i18n_common as common  # noqa: E402
import i18n_seed as seed_mod  # noqa: E402
import i18n_seek as seek_mod  # noqa: E402
import i18n_shape as shape_mod  # noqa: E402
import i18n_sift as sift_mod  # noqa: E402
import i18n_splice as splice_mod  # noqa: E402

# Written to a real glossary JSON file (not an in-memory PhraseTable) because seed_mod.main()
# builds its own PhraseTable from --glossary/--phrases/--keep file paths, matching exactly how
# the real CLI is invoked -- the point of testing main() rather than seed_translations() is to
# cover that file-loading plumbing too.
_FIXTURE_GLOSSARY = {
    "the": {"target": "le", "pos": "DET"},
    "open": {"target": "ouvrez", "pos": "VERB"},
    "active": {"target": "actif", "pos": "ADJ", "target_fem": "active"},
    "page": {"target": "page", "pos": "NOUN", "gender": "f", "number": "s"},
    "on": {"target": "sur", "pos": "PREP"},
    "your": {"target": "votre", "pos": "DET"},
    "source code": {"target": "code source", "pos": "NOUN", "gender": "m", "number": "s"},
    "see": {"target": "voir", "pos": "VERB"},
    "for": {"target": "pour", "pos": "PREP"},
    "details": {"target": "détails", "pos": "NOUN", "gender": "m", "number": "p"},
}


class Phase5Pipeline(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.p = lambda name: os.path.join(self.d.name, name)

    def tearDown(self):
        self.d.cleanup()

    def _write(self, name, obj):
        Path(self.p(name)).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return self.p(name)

    def test_full_pipeline_seek_seed_shape_splice_sift(self):
        source = [
            {"key": "The active page", "rich": False, "src": ["a.html"]},
            {"key": "Open your source code!", "rich": False, "src": ["a.html"]},
            {"key": "Quantum hypervisor spline", "rich": False, "src": ["a.html"]},
            {"key": "Welcome, {user}!", "rich": False, "src": ["a.html"]},
            {"key": "See GitHub for details.", "rich": True, "src": ["a.html"],
             "html": 'See <a href="https://github.com/chris">GitHub</a> for details.'},
        ]
        fr_existing = {
            "p": {"Welcome, {user}!": "Bienvenue, {user} !"},
            "r": {},
        }
        src_p = self._write("source.json", source)
        fr_p = self._write("fr.json", fr_existing)
        keep_p = self._write("keep.json", [])
        meta_p = self.p(".meta_fr.json")
        work_p = self.p("work_fr.json")
        review_p = self.p("review_fr.json")

        # 1. SEEK
        rc = seek_mod.main(["--source", src_p, "--target", fr_p, "--keep", keep_p,
                             "--meta", meta_p, "--out", work_p])
        self.assertEqual(rc, 0)
        work = json.loads(Path(work_p).read_text())
        self.assertEqual(work["summary"]["untranslated"], 4)
        self.assertEqual(work["summary"]["up_to_date"], 1)
        # fr.json must still be untouched after seek (seek never writes it)
        self.assertEqual(json.loads(Path(fr_p).read_text()), fr_existing)

        # 2. SEED (via life.xlate, real gate -- no lint_fn here, matches production default)
        glossary_p = self._write("glossary.json", _FIXTURE_GLOSSARY)
        keep_p = self._write("keep.json", ["GitHub", "Chris"])  # KEEP terms, re-written over the empty one above
        phrases_p = self.p("phrases.json")  # absent on purpose
        rc = seed_mod.main(["--work", work_p, "--target", fr_p, "--meta", meta_p,
                             "--glossary", glossary_p, "--phrases", phrases_p, "--keep", keep_p,
                             "--review-out", review_p])
        self.assertEqual(rc, 0)
        fr_after_seed = json.loads(Path(fr_p).read_text())
        self.assertEqual(fr_after_seed["p"]["The active page"], "La page active")
        self.assertEqual(fr_after_seed["p"]["Open your source code!"], "Ouvrez votre code source !")
        review = json.loads(Path(review_p).read_text())
        self.assertIn("Quantum hypervisor spline", review["queue"])
        self.assertEqual(review["queue"]["Quantum hypervisor spline"]["unknown_tokens"],
                          ["Quantum", "hypervisor", "spline"])
        # human translation must be untouched by seed
        self.assertEqual(fr_after_seed["p"]["Welcome, {user}!"], "Bienvenue, {user} !")

        # A rich entry with real glossary coverage (See/GitHub/for/details + KEEP) commits
        # and gets a sidecar hash -- never a hash field inside fr.json itself.
        if "See GitHub for details." in fr_after_seed["r"]:
            meta = json.loads(Path(meta_p).read_text())
            self.assertIn("See GitHub for details.", meta["r"])
            self.assertIn("html_hash", meta["r"]["See GitHub for details."])

        # 3. SHAPE (typography) -- must never touch the href inside the rich entry
        rc = shape_mod.main(["--target", fr_p])
        self.assertEqual(rc, 0)
        fr_after_shape = json.loads(Path(fr_p).read_text())
        self.assertEqual(fr_after_shape["p"]["Open your source code!"], "Ouvrez votre code source !")
        if "See GitHub for details." in fr_after_shape["r"]:
            self.assertIn('href="https://github.com/chris"', fr_after_shape["r"]["See GitHub for details."])

        # 4. SPLICE into a real template
        template = (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n<title>The active page</title>\n</head>\n"
            "<body>\n<h1>The active page</h1>\n"
            "<p>See <a href=\"https://github.com/chris\">GitHub</a> for details.</p>\n"
            "<br>\n</body>\n</html>\n"
        )
        out_html = splice_mod.splice_html_document(
            template, source, fr_after_shape, "fr", "https://chrislloyd.io", "about/index.html",
        )
        self.assertIn('<html lang="fr">', out_html)
        self.assertIn("<h1>La page active</h1>", out_html)
        self.assertIn('<link rel="canonical" href="https://chrislloyd.io/fr/about/index.html"/>', out_html)
        self.assertIn('<link rel="alternate" hreflang="en" href="https://chrislloyd.io/about/index.html"/>', out_html)
        self.assertIn('<link rel="alternate" hreflang="x-default" href="https://chrislloyd.io/about/index.html"/>', out_html)
        self.assertIn("<br/>", out_html)  # void-tag convention matches i18n_extract.py

        # 5. SIFT: catalog + rendered page, partial allowed (not every key translated)
        cat_issues = sift_mod.sift_catalog(source, fr_after_shape, require_complete=False)
        self.assertEqual(cat_issues, [])
        html_issues = sift_mod.sift_rendered_html(out_html, expected_lang="fr", page_name="about/index.html")
        self.assertEqual(html_issues, [])

    def test_sift_catches_broken_placeholder_and_tag_mismatch(self):
        source = [{"key": "Click here, {name}", "rich": False, "src": ["a.html"]},
                  {"key": "See GitHub.", "rich": True, "src": ["a.html"],
                   "html": 'See <a href="/docs">GitHub</a>.'}]
        bad_fr = {"p": {"Click here, {name}": "Cliquez ici, {nom}"},
                  "r": {"See GitHub.": "Voir GitHub."}}  # dropped the <a> entirely
        issues = sift_mod.sift_catalog(source, bad_fr, require_complete=True)
        cats = {v.category for v in issues}
        self.assertIn("PLACEHOLDER_MISMATCH", cats)
        self.assertIn("TAG_MISMATCH", cats)

    def test_seek_never_writes_fr_json_only_the_work_file_and_meta_sidecar(self):
        source = [{"key": "Hello", "rich": False, "src": ["a.html"]}]
        fr_before = {"p": {}, "r": {}}
        src_p = self._write("source.json", source)
        fr_p = self._write("fr.json", fr_before)
        keep_p = self._write("keep.json", [])
        before_bytes = Path(fr_p).read_bytes()
        seek_mod.main(["--source", src_p, "--target", fr_p, "--keep", keep_p,
                       "--meta", self.p(".meta_fr.json"), "--out", self.p("work_fr.json")])
        self.assertEqual(Path(fr_p).read_bytes(), before_bytes)

    def test_identical_to_english_not_in_keep_counts_as_untranslated(self):
        source = [{"key": "Services", "rich": False, "src": ["a.html"]}]
        fr = {"p": {"Services": "Services"}, "r": {}}  # looks translated, isn't (no keep entry)
        src_p = self._write("source.json", source)
        fr_p = self._write("fr.json", fr)
        keep_p = self._write("keep.json", [])  # "Services" NOT listed
        seek_mod.main(["--source", src_p, "--target", fr_p, "--keep", keep_p,
                       "--meta", self.p(".meta_fr.json"), "--out", self.p("work_fr.json")])
        work = json.loads(Path(self.p("work_fr.json")).read_text())
        self.assertIn("Services", work["todo"])

    def test_identical_to_english_IN_keep_counts_as_up_to_date(self):
        source = [{"key": "Services", "rich": False, "src": ["a.html"]}]
        fr = {"p": {"Services": "Services"}, "r": {}}
        src_p = self._write("source.json", source)
        fr_p = self._write("fr.json", fr)
        keep_p = self._write("keep.json", ["Services"])
        seek_mod.main(["--source", src_p, "--target", fr_p, "--keep", keep_p,
                       "--meta", self.p(".meta_fr.json"), "--out", self.p("work_fr.json")])
        work = json.loads(Path(self.p("work_fr.json")).read_text())
        self.assertNotIn("Services", work["todo"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
