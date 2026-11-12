#!/usr/bin/env python3
"""Checks for the French catalog (data/i18n/fr.json) and the language/currency script.

  python3 -m unittest scripts.test_i18n          full test run
  python3 scripts/test_i18n.py --chunk SRC OUT   check one translated chunk against its source chunk
"""
import json
import os
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import i18n_extract  # noqa: E402

PLACEHOLDER = re.compile(r"\{[a-z]+\}")
DIGITS = re.compile(r"\d+")


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        self.out.append(("<" + tag, tuple(sorted(attrs))))

    def handle_startendtag(self, tag, attrs):
        self.out.append(("<" + tag, tuple(sorted(attrs))))

    def handle_endtag(self, tag):
        self.out.append(("</" + tag, ()))


def tags(markup):
    p = _Tags()
    p.feed(markup)
    return p.out


def problems(source, catalog, keep):
    """source: list of {key, rich, html?}; catalog: {p, r}; keep: set of keys left identical on purpose."""
    out = []
    want = {(bool(i["rich"]), i["key"]): i for i in source}
    for (rich, key), item in want.items():
        sect = catalog.get("r" if rich else "p", {})
        label = ("rich " if rich else "") + repr(key[:60])
        if key not in sect:
            if not set(item.get("src", [])) <= {"store.json", "products.html"}:
                out.append("missing: " + label)
            continue
        fr = sect[key]
        if not isinstance(fr, str) or not fr.strip():
            out.append("empty: " + label)
            continue
        if fr == (item["html"] if rich else key) and key not in keep:
            out.append("identical to English but not listed in keep: " + label)
        if PLACEHOLDER.findall(key) != PLACEHOLDER.findall(fr):
            out.append("placeholders differ: " + label)
        if sorted(DIGITS.findall(key)) != sorted(DIGITS.findall(fr)):
            out.append("numbers differ (nothing may be added or dropped): " + label)
        if rich:
            if tags(item["html"]) != tags(fr):
                out.append("HTML tags/attributes differ: " + label)
        elif ("<" in fr) != ("<" in key):
            out.append("markup appeared or vanished in plain text: " + label)
        if len(fr) > 3 * len(key) + 20:
            out.append("suspiciously long: " + label)
    for sect, rich in (("p", False), ("r", True)):
        for key in catalog.get(sect, {}):
            if (rich, key) not in want:
                out.append("not in source: " + repr(key[:60]))
    return out


def load(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


class Catalog(unittest.TestCase):
    def test_source_is_current(self):
        cur = open(i18n_extract.OUT, encoding="utf-8").read()
        want = json.dumps(i18n_extract.build(), indent=1, ensure_ascii=False) + "\n"
        self.assertEqual(cur, want, "run: python3 scripts/i18n_extract.py")

    def test_french_covers_every_string(self):
        cat = load("data/i18n/fr.json")
        keep = set(load("data/i18n/keep.json"))
        probs = problems(load("data/i18n/source.json"), cat, keep)
        self.assertEqual(probs[:15], [], f"{len(probs)} problems")

    def test_keep_entries_exist(self):
        src = {i["key"] for i in load("data/i18n/source.json")}
        for k in load("data/i18n/keep.json"):
            self.assertIn(k, src)

    def test_fx_fallback(self):
        fx = load("data/fx.json")
        self.assertGreater(fx["rate"], 0.5)
        self.assertLess(fx["rate"], 3)
        self.assertTrue(fx["date"] and fx["source"])

    def test_store_prices_are_from_the_feed(self):
        for it in load("data/store.json")["items"]:
            self.assertRegex(it.get("price", ""), r"^\d+\.\d\d$", it["id"])

    def test_shopify_handoff_off_by_default(self):
        cfg = load("data/config.json")
        self.assertIs(cfg["shopifyCountryParam"], False)
        self.assertEqual(cfg["shopifyLocales"], [])


class Script(unittest.TestCase):
    def test_node_logic(self):
        r = subprocess.run(["node", os.path.join(ROOT, "scripts", "test_i18n.js")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


def main_chunk(src_path, out_path):
    src = json.load(open(src_path, encoding="utf-8"))
    out = json.load(open(out_path, encoding="utf-8"))
    probs = problems(src, out, set(out.get("keep", [])))
    for p in probs:
        print(p)
    print(len(probs), "problems;", len(src), "strings in chunk")
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--chunk":
        main_chunk(sys.argv[2], sys.argv[3])
    unittest.main()
