#!/usr/bin/env python3
"""Build data/i18n/source.json: every English string a visitor can see, so the
French catalog (data/i18n/fr.json) can be checked for completeness.

Mirrors assets/i18n.js exactly:
  * plain unit  = one text node, key = whitespace-collapsed text
  * rich unit   = an element with a non-svg child element, no form control / id inside, and at
                  least 3 words of its own text (a sentence with inline <a>/<strong>);
                  key = collapsed textContent, value carries the inline HTML
  * attributes  = placeholder, aria-label, title, alt, button value, SEO meta content
  * data files  = the visitor-visible fields listed in JSON_FIELDS (rendered by main.js/blog.js)
  * t("...")    = literal strings passed to t() in assets/*.js

Usage: python3 scripts/i18n_extract.py          (rewrite data/i18n/source.json)
       python3 scripts/i18n_extract.py --check  (exit 1 if source.json is stale)
"""
import glob
import json
import os
import re
import sys

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "i18n", "source.json")

SKIP_TAGS = {"script", "style", "noscript", "textarea", "svg"}
ATTRS = ("placeholder", "aria-label", "title", "alt")
META_KEYS = {("name", "description"), ("property", "og:title"), ("property", "og:description"),
             ("name", "twitter:title"), ("name", "twitter:description")}
LETTER = re.compile(r"[A-Za-zÀ-ÿ]")


def norm(s):
    return " ".join(s.split())


def keep(s):
    return bool(s) and bool(LETTER.search(s))


class Collector:
    def __init__(self):
        self.items = {}  # key -> {"rich": bool, "html": str, "src": [..]}

    def add(self, text, src, rich=False, html=""):
        key = norm(text)
        if not keep(key):
            return
        it = self.items.get((rich, key))
        if it is None:
            it = self.items[(rich, key)] = {"key": key, "rich": rich, "src": []}
            if rich:
                it["html"] = norm(html)
        if src not in it["src"]:
            it["src"].append(src)


WORD = re.compile(r"[A-Za-z\u00C0-\u00FF]+")
UNSAFE = {"input", "select", "textarea", "button"}


def direct_words(tag):
    text = " ".join(str(c) for c in tag.children if isinstance(c, NavigableString) and not isinstance(c, Comment))
    return len(WORD.findall(text))


def is_rich(tag):
    if direct_words(tag) < 3:
        return False
    if not any(isinstance(c, Tag) and c.name != "svg" for c in tag.children):
        return False
    return not tag.find(lambda t: t.name in UNSAFE or t.has_attr("id"))


def walk(node, src, col):
    if isinstance(node, Comment):
        return
    if isinstance(node, NavigableString):
        col.add(str(node), src)
        return
    if not isinstance(node, Tag):
        return
    if node.name in SKIP_TAGS or node.has_attr("data-no-i18n"):
        return
    for a in ATTRS:
        if node.has_attr(a):
            col.add(node[a], src + " @" + a)
    if node.name == "input" and node.get("type") in ("submit", "button", "reset") and node.has_attr("value"):
        col.add(node["value"], src + " @value")
    if node.name == "meta" and node.has_attr("content"):
        for k in ("name", "property"):
            if node.has_attr(k) and (k, node[k]) in META_KEYS:
                col.add(node["content"], src + " @meta")
    if is_rich(node):
        col.add(node.get_text(), src, rich=True, html=node.decode_contents())
        return
    for c in list(node.children):
        walk(c, src, col)


def from_html(col):
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html5lib")
        walk(soup.html, os.path.basename(path), col)


def load(name):
    return json.load(open(os.path.join(ROOT, "data", name), encoding="utf-8"))


def from_json(col):
    def s(src, *vals):
        for v in vals:
            if isinstance(v, str):
                col.add(v, src)

    for f in load("services.json"):
        s("services.json", f.get("title"), f.get("desc"))
    a = load("about.json")["about"]
    s("about.json", a.get("photoAlt"), *a.get("paragraphs", []))
    for q in load("faq.json")["faq"]:
        s("faq.json", q.get("q"), q.get("a"))
    for t in load("testimonials.json"):
        s("testimonials.json", t.get("quote"), t.get("author") if t.get("placeholder") else None)
    for g in load("gallery.json"):
        s("gallery.json", g.get("title"), g.get("caption"), g["before"].get("alt"), g["after"].get("alt"))
    for sn in load("promo-calendar.json")["seasons"]:
        s("promo-calendar.json", sn.get("promo_copy"))
    lm = load("lead_magnet.json")
    for c in lm["checklist"]:
        if not c.get("placeholder"):
            s("lead_magnet.json", c.get("title"), c.get("detail"))
    s("lead_magnet.json", lm.get("closing_note"))
    for p in load("posts.json"):
        body = p.get("body", [])
        s("posts.json", p.get("title"), p.get("excerpt"), *([body] if isinstance(body, str) else body))
    site = load("site.json")["site"]
    s("site.json", site.get("tagline"), site.get("blurb"), site.get("phoneNote"), site.get("metaDescription"))
    for f in ("shop.json", "lidar.json", "voice.json", "reviews.json"):
        for it in load(f):
            s(f, it.get("title"), it.get("desc"), it.get("category"), it.get("url_label"))
    for it in load("opensource.json"):
        s("opensource.json", it.get("desc"), *it.get("tags", []))
    st = load("store.json")
    for c in st["categories"]:
        s("store.json", c)
    for it in st["items"]:
        s("store.json", it.get("title"), it.get("desc"), *it.get("features", []))


TCALL = re.compile(r'(?:\bt\(|\bfailNote\(\w+,)\s*"((?:[^"\\]|\\.)*)"')


def from_js(col):
    for path in sorted(glob.glob(os.path.join(ROOT, "assets", "*.js"))):
        text = open(path, encoding="utf-8").read()
        for m in TCALL.finditer(text):
            col.add(json.loads('"' + m.group(1) + '"'), "assets/" + os.path.basename(path))


def build():
    col = Collector()
    from_html(col)
    from_json(col)
    from_js(col)
    return list(col.items.values())


def sync_catalog(items):
    """Keep fr.json exactly in step with the source: stale entries move to fr-archive.json, returning ones come back."""
    d = os.path.join(ROOT, "data", "i18n")
    fr = json.load(open(os.path.join(d, "fr.json"), encoding="utf-8"))
    ap = os.path.join(d, "fr-archive.json")
    arch = json.load(open(ap, encoding="utf-8")) if os.path.exists(ap) else {"p": {}, "r": {}}
    want = {(bool(i["rich"]), i["key"]) for i in items}
    for sect, rich in (("p", False), ("r", True)):
        for k in list(fr[sect]):
            if (rich, k) not in want:
                arch[sect][k] = fr[sect].pop(k)
        for k in list(arch[sect]):
            if (rich, k) in want and k not in fr[sect]:
                fr[sect][k] = arch[sect].pop(k)
    json.dump(fr, open(os.path.join(d, "fr.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(arch, open(ap, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    return sum(1 for i in items if i["key"] not in fr["r" if i["rich"] else "p"])


def main():
    items = build()
    text = json.dumps(items, indent=1, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if cur != text:
            print("data/i18n/source.json is stale: run python3 scripts/i18n_extract.py", file=sys.stderr)
            sys.exit(1)
        print("source.json up to date,", len(items), "strings")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(text)
    if "--sync" in sys.argv:
        print(sync_catalog(items), "strings still without French (shown in English)")
    rich = sum(1 for i in items if i["rich"])
    print(len(items), "strings (", rich, "rich ),", sum(len(i["key"]) for i in items), "chars")


if __name__ == "__main__":
    main()
