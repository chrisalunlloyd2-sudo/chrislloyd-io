#!/usr/bin/env python3
"""perf_budget.py — page-weight table + thresholds for chrislloyd-io (PLAN-SITE-100 phase 1
step 4). Deterministic, stdlib HTMLParser, no browser, no network.

Per page: HTML document size + every local asset (assets/*.css|js|png|jpg|webp|svg) it
references via src=/href=, each counted once. External (http/https) assets aren't
downloaded or counted - this measures what *this repo* ships, not third-party weight.

Run: python3 scripts/perf_budget.py   (exit 0 = all pages within budget, 1 = over budget)
"""
import html.parser
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HTML_BUDGET = 150_000     # bytes, the page's own markup
TOTAL_BUDGET = 1_000_000  # bytes, markup + every local asset it references

ASSET_ATTRS = {"src", "href"}


class AssetParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ASSET_ATTRS and value and value.startswith("assets/"):
                self.refs.append(value)


def local_pages():
    return sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))


def page_weight(page):
    """Return (html_bytes, asset_bytes, missing_assets) for one top-level page."""
    path = os.path.join(ROOT, page)
    html_bytes = os.path.getsize(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    p = AssetParser()
    p.feed(text)
    asset_bytes = 0
    missing = []
    for ref in sorted(set(p.refs)):
        apath = os.path.join(ROOT, ref)
        if os.path.isfile(apath):
            asset_bytes += os.path.getsize(apath)
        else:
            missing.append(ref)
    return html_bytes, asset_bytes, missing


def budget_table():
    rows = []
    for page in local_pages():
        html_b, asset_b, missing = page_weight(page)
        rows.append((page, html_b, asset_b, html_b + asset_b, missing))
    return rows


def main():
    rows = budget_table()
    over = []
    print(f"{'page':<22}{'html':>10}{'assets':>12}{'total':>12}  status")
    for page, html_b, asset_b, total, missing in rows:
        status = "ok"
        if html_b > HTML_BUDGET:
            status = f"OVER html budget ({HTML_BUDGET:,})"
        elif total > TOTAL_BUDGET:
            status = f"OVER total budget ({TOTAL_BUDGET:,})"
        if missing:
            status += f"; missing: {', '.join(missing)}"
        if status != "ok":
            over.append(page)
        print(f"{page:<22}{html_b:>10,}{asset_b:>12,}{total:>12,}  {status}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
