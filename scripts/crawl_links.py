#!/usr/bin/env python3
"""crawl_links.py — internal link graph for chrislloyd-io (PLAN-SITE-100 phase 1 step 5).

Deterministic, stdlib HTMLParser, no browser, no network. Reads every top-level *.html
page, follows every <a href> that points at another local page, and reports two failure
classes:
  dead    - an internal link whose target file doesn't exist on disk.
  orphan  - a real top-level page that nothing else on the site links to.

query-string "routes" into the same file (blog.html?post=X) are treated as the file
blog.html, not a separate target - this site has no server-side routing.
External links (http(s) to another host), mailto:, tel:, and #anchor-only links are
never checked - they're out of scope for an internal link audit.

Run: python3 scripts/crawl_links.py   (exit 0 = clean, 1 = findings printed to stdout)
"""
import html.parser
import os
import sys
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "javascript:")


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)


def local_pages():
    """Every top-level *.html file this site actually serves."""
    return sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))


def internal_target(href):
    """Return the local filename a link resolves to, or None if out of scope
    (external, anchor-only, mailto/tel, or a non-.html asset)."""
    href = href.strip()
    if not href or href.startswith(SKIP_PREFIXES) or href.startswith("#"):
        return None
    path = urlsplit(href).path  # drops ?query and #fragment
    if not path:
        return None  # pure "#frag" or "?query" on the current page
    name = os.path.basename(path)
    if not name.endswith(".html"):
        return None
    return name


def crawl():
    pages = local_pages()
    page_set = set(pages)
    linked_to = set()
    dead = []  # (source_page, target, line)
    for page in pages:
        with open(os.path.join(ROOT, page), encoding="utf-8") as fh:
            text = fh.read()
        p = LinkParser()
        p.feed(text)
        for href in p.hrefs:
            target = internal_target(href)
            if target is None:
                continue
            linked_to.add(target)
            if target not in page_set:
                dead.append((page, target))
    # index.html is the entry point and never needs an inbound link; everything else
    # should be reachable from somewhere, or it's effectively invisible to users/crawlers.
    orphans = sorted(page_set - linked_to - {"index.html"})
    return dead, orphans


def main():
    dead, orphans = crawl()
    if not dead and not orphans:
        print("crawl_links: clean —", len(local_pages()), "pages, all internal links resolve")
        return 0
    for page, target in dead:
        print(f"DEAD LINK: {page} -> {target} (file does not exist)")
    for page in orphans:
        print(f"ORPHAN: {page} (no other page links to it)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
