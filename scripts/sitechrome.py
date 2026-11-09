"""Shared page chrome (nav, mobile action bar, footer note) for the generated pages and blog.html.

index.html carries its own copy (its links are in-page anchors). Keep the two in step: tests/
test_store.py checks every page has the nav, the mobile bar and the ping disclosure.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPQ = "10412+66+Ave+NW+Edmonton+AB+T6H+1V9"
MAPS = "https://www.google.com/maps/search/?api=1&amp;query=" + MAPQ

PING_NOTE = ('<p class="section-note ping-note">This site sends me a simple notification when a page is opened: '
             'the page, the referring site, your time zone, language and device type. It does not include your '
             'name or IP address, and your browser&rsquo;s Do Not Track setting turns it off.</p>')


def phone_digits():
    try:
        site = json.load(open(os.path.join(ROOT, "data", "site.json"), encoding="utf-8")).get("site", {})
        return re.sub(r"[^+\d]", "", site.get("phone", ""))
    except (OSError, ValueError):
        return ""


def nav(current=""):
    def a(href, label, key):
        cur = ' aria-current="page"' if key == current else ""
        return f'<a href="{href}"{cur}>{label}</a>'
    links = "".join([
        a("index.html#services", "Services", "services"),
        a("index.html#about", "About", "about"),
        a("products.html", "Store", "store"),
        a("blog.html", "Blog", "blog"),
        a("index.html#faq", "FAQ", "faq"),
        a("index.html#find", "Find us", "find"),
    ])
    return ('<nav class="nav" aria-label="Main">\n  <div class="wrap nav-in">\n'
            '    <a class="brand" href="index.html">Chris Lloyd <span>Painting</span></a>\n'
            f'    <div class="nav-links">{links}</div>\n'
            '    <a class="btn btn-sm nav-cta" href="index.html#contact">Free quote</a>\n  </div>\n</nav>\n')


def mbar():
    sms = phone_digits()
    text = f'<a href="sms:{sms}">Text</a>' if sms else ""
    cols = "" if text else ' style="grid-template-columns:repeat(2,1fr)"'
    return (f'<div class="mbar" aria-label="Quick contact"{cols}>\n'
            '  <a href="index.html#contact" class="primary">Free quote</a>\n'
            f'  {text}\n'
            f'  <a href="{MAPS}" target="_blank" rel="noopener noreferrer">Map</a>\n</div>\n')
