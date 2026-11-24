#!/usr/bin/env python3
"""test_mirror_voice_data.py — tests for mirror_voice_data.py (PLAN-SITE-100 step 20).

The contract under test (step 19): the daily mirror in ~/.life/voice-data must
hold byte-identical copies of data/faq.json + data/area-pages.json — no
paraphrasing, re-serialization, or appends.

Run: python3 scripts/test_mirror_voice_data.py   (unittest, exits non-zero on fail)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "mirror_voice_data.py")


class TestMirrorVoiceData(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def mirror(self, out=None):
        out = out or self.tmp
        r = subprocess.run(
            [sys.executable, SCRIPT, "--out", out],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return out

    def test_files_copied_byte_identical(self):
        out = self.mirror()
        for name in ("faq.json", "area-pages.json"):
            with open(os.path.join(ROOT, "data", name), "rb") as f:
                src = f.read()
            with open(os.path.join(out, name), "rb") as f:
                dst = f.read()
            self.assertEqual(src, dst, "%s must be copied verbatim" % name)

    def test_step20_faq_qa_byte_identical(self):
        """Step 20: every faq.json q/a string appears byte-identical in the mirror."""
        out = self.mirror()
        src = json.load(open(os.path.join(ROOT, "data", "faq.json"), encoding="utf-8"))
        mir = json.load(open(os.path.join(out, "faq.json"), encoding="utf-8"))
        self.assertEqual(src, mir, "mirror faq.json must equal source faq.json")
        src_entries = src["faq"] if isinstance(src, dict) else src
        mir_entries = mir["faq"] if isinstance(mir, dict) else mir
        self.assertEqual(src_entries, mir_entries)
        for e in src_entries:
            self.assertGreater(len(e["q"]) > 0 and len(e["a"]) > 0, 0)
            # exact strings appear in the mirrored file's raw text
            with open(os.path.join(out, "faq.json"), encoding="utf-8") as f:
                raw = f.read()
            self.assertIn(e["q"], raw)
            self.assertIn(e["a"], raw)
        self.assertTrue(src_entries, "expected >=1 FAQ entry")

    def test_idempotent_overwrite_never_appends(self):
        out1 = os.path.join(self.tmp, "r1")
        out2 = os.path.join(self.tmp, "r2")
        self.mirror(out1)
        self.mirror(out1)  # second daily run
        self.mirror(out2)  # reference run in a fresh dir
        for name in ("faq.json", "area-pages.json"):
            with open(os.path.join(out1, name), "rb") as a, open(os.path.join(out2, name), "rb") as b:
                self.assertEqual(a.read(), b.read(), "%s should be overwrite-stable" % name)
        # manifest is overwrite-in-place too; only its run timestamp may differ
        m1 = json.load(open(os.path.join(out1, "manifest.json"), encoding="utf-8"))
        m2 = json.load(open(os.path.join(out2, "manifest.json"), encoding="utf-8"))
        self.assertEqual({k: v for k, v in m1.items() if k != "when_utc"},
                         {k: v for k, v in m2.items() if k != "when_utc"})
        self.assertEqual(sorted(os.listdir(out1)),
                         ["area-pages.json", "faq.json", "manifest.json"])

    def test_manifest_records_sources_and_creates_dir(self):
        out = os.path.join(self.tmp, "deep", "newdir")
        self.mirror(out)
        m = json.load(open(os.path.join(out, "manifest.json"), encoding="utf-8"))
        self.assertEqual([s["file"] for s in m["sources"]],
                         ["faq.json", "area-pages.json"])
        self.assertTrue(m["when_utc"].endswith("Z"))
        self.assertTrue(all(len(s["sha256"]) == 64 and s["bytes"] > 0 for s in m["sources"]))


if __name__ == "__main__":
    unittest.main()
