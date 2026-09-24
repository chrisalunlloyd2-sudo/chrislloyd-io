#!/usr/bin/env python3
"""Regenerate sitemap.xml from the real site structure.

Usage:
  python3 scripts/gen_sitemap.py

Lists index.html, blog.html, and every blog post view URL from
data/posts.json. Placeholder posts (excerpt contains "PLACEHOLDER") are
excluded so crawlers only ever see real content — they reappear
automatically once a real post replaces them. Run after add_post.py /
add_item.py, or just before you push; idempotent.

Canonical base URL is taken from data/site.json -> site.canonicalBase
(falls back to the GitHub Pages URL). Update that field when the custom
domain goes live.
"""
import json, os, sys, tempfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "data", "site.json")
POSTS = os.path.join(ROOT, "data", "posts.json")
SITEMAP = os.path.join(ROOT, "sitemap.xml")

DEFAULT_BASE = "https://chrisalunlloyd2-sudo.github.io/chrislloyd-io/"


def base_url():
    try:
        with open(SITE, encoding="utf-8") as f:
            base = (json.load(f).get("site") or {}).get("canonicalBase", "")
        if base:
            return base.rstrip("/") + "/"
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_BASE


def is_placeholder(post):
    blob = (post.get("excerpt", "") + " " + " ".join(post.get("body", [])))
    return "PLACEHOLDER" in blob.upper()


def load_posts():
    try:
        with open(POSTS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def write(path, content):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main():
    base = base_url()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [
        (base + "index.html", "1.0"),
        (base + "blog.html", "0.8"),
    ]
    for p in sorted(load_posts(), key=lambda x: x.get("date", ""), reverse=True):
        if is_placeholder(p):
            continue
        urls.append((base + "blog.html?post=" + p["id"], "0.6"))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, prio in urls:
        lines += [
            "  <url>",
            f"    <loc>{escape(loc)}</loc>",
            f"    <lastmod>{today}</lastmod>",
            "    <changefreq>monthly</changefreq>",
            f"    <priority>{prio}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    write(SITEMAP, "\n".join(lines) + "\n")
    print(f"sitemap.xml: {len(urls)} URLs (base {base})")


if __name__ == "__main__":
    sys.exit(main())