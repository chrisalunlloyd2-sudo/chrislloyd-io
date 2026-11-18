#!/usr/bin/env python3
"""provenance.py — skeleton (PLAN-SITE-100 phase 1 step 7, deliberately scoped as a
skeleton per the plan, not a full per-string tracer).

Two things, both static analysis, no browser, no JS execution:
  1. Which data/*.json files exist and which assets/*.js file(s) fetch() each one -
     the traceable, JSON-sourced content.
  2. Per top-level HTML page, a count of literal text nodes (visible text that is NOT
     inside <script>/<style> and not just whitespace) - a proxy for hand-authored prose
     that isn't backed by a data file, and so is exactly the content a human needs to
     check against [[feedback-never-fabricate-content]] (no invented ratings/stats/
     business details) rather than something this script can verify on its own.

Not built (future, non-skeleton work): mapping one specific rendered string to the one
JSON field that produced it. That needs either JS execution tracing or a much stricter
templating convention than this site currently has, and isn't needed yet to get value
out of knowing "data-driven" vs "hand-authored, verify by eye" at the page level.

Run: python3 scripts/provenance.py
"""
import html.parser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FETCH_RE = re.compile(r'fetch\(["\']data/([^"\']+\.json)["\']\)')


class TextCounter(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_skip = 0
        self.count = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.in_skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.in_skip:
            self.in_skip -= 1

    def handle_data(self, data):
        if self.in_skip:
            return
        if data.strip():
            self.count += 1


def data_sources():
    """{json_filename: [js files that fetch it]}."""
    sources = {f: [] for f in sorted(os.listdir(os.path.join(ROOT, "data")))
               if f.endswith(".json")}
    assets_dir = os.path.join(ROOT, "assets")
    for js in sorted(f for f in os.listdir(assets_dir) if f.endswith(".js")):
        with open(os.path.join(assets_dir, js), encoding="utf-8") as fh:
            text = fh.read()
        for m in FETCH_RE.finditer(text):
            sources.setdefault(m.group(1), []).append(js)
    return sources


def page_text_counts():
    out = {}
    for page in sorted(f for f in os.listdir(ROOT) if f.endswith(".html")):
        with open(os.path.join(ROOT, page), encoding="utf-8") as fh:
            text = fh.read()
        p = TextCounter()
        p.feed(text)
        out[page] = p.count
    return out


def main():
    print("== data/*.json -> fetched by ==")
    sources = data_sources()
    for name, by in sources.items():
        label = ", ".join(by) if by else "(not fetched by any assets/*.js — check if still used)"
        print(f"  {name}: {label}")

    print("\n== hand-authored text nodes per page (verify-by-eye content) ==")
    for page, count in page_text_counts().items():
        print(f"  {page}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
