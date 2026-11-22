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
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "i18n", "source.json")

SKIP_TAGS = {"script", "style", "noscript", "textarea", "svg"}
ATTRS = ("placeholder", "aria-label", "title", "alt")
META_KEYS = {("name", "description"), ("property", "og:title"), ("property", "og:description"),
             ("name", "twitter:title"), ("name", "twitter:description")}
LETTER = re.compile(r"[A-Za-zÀ-ÿ]")

# Minimal HTML5 tree builder (stdlib html.parser only, no bs4/html5lib). Replaces an
# external-dependency DOM with just enough structure for walk()/is_rich() below: an
# element node (tag, ordered attrs, children) and plain str for text. Comments are
# dropped by never overriding handle_comment (same effect as bs4's Comment filtering).
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class _El:
    __slots__ = ("name", "attrs", "attr_order", "children")

    def __init__(self, name, attrs):
        self.name = name
        self.attrs = dict(attrs)
        self.attr_order = attrs
        self.children = []

    def has_attr(self, key):
        return key in self.attrs

    def get(self, key, default=None):
        return self.attrs.get(key, default)

    def __getitem__(self, key):
        return self.attrs[key]


class _DomBuilder(HTMLParser):
    """Builds an _El tree; unmatched/misnested close tags are recovered like a browser would
    (pop up to the nearest matching open ancestor; a stray close tag with no open match is
    ignored), since these are hand-authored static pages, not an adversarial input."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _El("#root", [])
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = _El(tag, attrs)
        self.stack[-1].children.append(el)
        if tag not in VOID_TAGS:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_El(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].name == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _iter_descendants(el):
    for c in el.children:
        if isinstance(c, _El):
            yield c
            for d in _iter_descendants(c):
                yield d


def _esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _serialize_children(children):
    out = []
    for c in children:
        if isinstance(c, str):
            out.append(_esc_text(c))
        else:
            out.append(_serialize_el(c))
    return "".join(out)


def _serialize_el(el):
    attrs = "".join(
        ' {}="{}"'.format(k, _esc_attr(v)) if v is not None else " " + k
        for k, v in el.attr_order
    )
    if el.name in VOID_TAGS:
        # self-closed to match the exact byte output the old bs4/html5lib stack produced
        # (data/i18n/fr.json's existing rich entries were translated against that form).
        return "<{}{}/>".format(el.name, attrs)
    return "<{0}{1}>{2}</{0}>".format(el.name, attrs, _serialize_children(el.children))


def get_text(el):
    """bs4 Tag.get_text() equivalent: all descendant text, no separator."""
    out = []

    def rec(node):
        for c in node.children:
            if isinstance(c, str):
                out.append(c)
            else:
                rec(c)

    rec(el)
    return "".join(out)


def decode_contents(el):
    return _serialize_children(el.children)


def parse_html(text):
    b = _DomBuilder()
    b.feed(text)
    b.close()
    for c in b.root.children:
        if isinstance(c, _El) and c.name == "html":
            return c
    return b.root


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
    text = " ".join(c for c in tag.children if isinstance(c, str))
    return len(WORD.findall(text))


def is_rich(tag):
    if direct_words(tag) < 3:
        return False
    if not any(isinstance(c, _El) and c.name != "svg" for c in tag.children):
        return False
    return not any(d.name in UNSAFE or d.has_attr("id") for d in _iter_descendants(tag))


def walk(node, src, col):
    if isinstance(node, str):
        col.add(node, src)
        return
    if not isinstance(node, _El):
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
        col.add(get_text(node), src, rich=True, html=decode_contents(node))
        return
    for c in list(node.children):
        walk(c, src, col)


def from_html(col):
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        with open(path, encoding="utf-8") as f:
            root = parse_html(f.read())
        walk(root, os.path.basename(path), col)


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
