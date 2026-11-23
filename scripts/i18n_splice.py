#!/usr/bin/env python3
"""chrislloyd-io/scripts/i18n_splice.py -- Phase 5.4: stdlib DOM splicer & SEO hreflang
emitter. Builds localized HTML pages from the site's real templates + source.json/fr.json,
using the exact same void-tag-aware stdlib DOM approach as i18n_extract.py (no bs4).

Match key is always the real on-disk content: a plain item's `key` (key IS the text) or a
rich item's `html` (the exact inner markup i18n_extract.py extracted) -- never a synthetic
id or a data-i18n attribute (the site doesn't use those).
"""
import argparse
import html
from html.parser import HTMLParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_common import VOID_ELEMENTS, load_source, load_target, match_text  # noqa: E402

TRANSLATABLE_ATTRS = ("title", "alt", "placeholder", "aria-label")
META_CONTENT_KEYS = {("name", "description"), ("property", "og:title"), ("property", "og:description"),
                     ("name", "twitter:title"), ("name", "twitter:description")}


@dataclass
class _Node:
    kind: str  # root | el | text | comment | decl
    tag: str = ""
    attrs: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    text: str = ""
    children: List["_Node"] = field(default_factory=list)

    def inner_html(self) -> str:
        return "".join(c.to_html() for c in self.children)

    def to_html(self) -> str:
        if self.kind == "root":
            return self.inner_html()
        if self.kind == "text":
            return self.text
        if self.kind == "comment":
            return f"<!--{self.text}-->"
        if self.kind == "decl":
            return f"<!{self.text}>"
        attrs = "".join(
            f' {k}="{html.escape(v, quote=True)}"' if v is not None else f" {k}"
            for k, v in self.attrs
        )
        if self.tag in VOID_ELEMENTS:
            return f"<{self.tag}{attrs}/>"
        return f"<{self.tag}{attrs}>{self.inner_html()}</{self.tag}>"


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = _Node(kind="root")
        self._stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(kind="el", tag=tag.lower(), attrs=list(attrs))
        self._stack[-1].children.append(node)
        if node.tag not in VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._stack[-1].children.append(_Node(kind="el", tag=tag.lower(), attrs=list(attrs)))

    def handle_endtag(self, tag):
        t = tag.lower()
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == t:
                del self._stack[i:]
                return

    def handle_data(self, data):
        self._stack[-1].children.append(_Node(kind="text", text=data))

    def handle_entityref(self, name):
        self._stack[-1].children.append(_Node(kind="text", text=f"&{name};"))

    def handle_charref(self, name):
        self._stack[-1].children.append(_Node(kind="text", text=f"&#{name};"))

    def handle_comment(self, data):
        self._stack[-1].children.append(_Node(kind="comment", text=data))

    def handle_decl(self, decl):
        self._stack[-1].children.append(_Node(kind="decl", text=decl))


def parse_fragment(raw_html: str) -> List[_Node]:
    b = _TreeBuilder()
    b.feed(raw_html)
    b.close()
    return b.root.children


def splice_html_document(template_html: str, source_items: List[Dict], target: Dict[str, Dict[str, str]],
                          lang: str, base_url: str, rel_page_path: str,
                          all_langs: Tuple[str, ...] = ("en", "fr")) -> str:
    """lang="en" is a no-op splice (used to emit the canonical/hreflang block on the
    existing English pages without changing their visible text)."""
    match_to_target: Dict[str, str] = {}
    for item in source_items:
        section = "r" if item.get("rich") else "p"
        repl = target.get(section, {}).get(item["key"])
        if repl:
            match_to_target[match_text(item).strip()] = repl

    plain_attr_target = target.get("p", {})

    builder = _TreeBuilder()
    builder.feed(template_html)
    builder.close()

    clean_rel = "" if rel_page_path in ("", "index.html") else rel_page_path.lstrip("/")

    def walk(node: _Node) -> None:
        if node.kind != "el":
            return
        attr_dict = dict(node.attrs)

        if node.tag == "html" and lang != "en":
            node.attrs = [("lang", lang) if k.lower() == "lang" else (k, v) for k, v in node.attrs]
            if not any(k.lower() == "lang" for k, _ in node.attrs):
                node.attrs.insert(0, ("lang", lang))

        if node.tag == "meta" and lang != "en":
            key = ((attr_dict.get("name") or "").lower(), (attr_dict.get("property") or "").lower())
            name_key = ("name", key[0])
            prop_key = ("property", key[1])
            if name_key in META_CONTENT_KEYS or prop_key in META_CONTENT_KEYS:
                cur = (attr_dict.get("content") or "").strip()
                if cur in plain_attr_target:
                    node.attrs = [(k, plain_attr_target[cur] if k.lower() == "content" else v)
                                  for k, v in node.attrs]

        if lang != "en":
            node.attrs = [
                (k, plain_attr_target[v.strip()]) if k.lower() in TRANSLATABLE_ATTRS and v and v.strip() in plain_attr_target
                else (k, v)
                for k, v in node.attrs
            ]

        if node.tag == "head":
            for c in list(node.children):
                walk(c)
            node.children = [
                c for c in node.children
                if not (c.kind == "el" and c.tag == "link"
                        and dict(c.attrs).get("rel") in ("canonical", "alternate"))
            ]
            base = base_url.rstrip("/")
            self_prefix = "" if lang == "en" else f"/{lang}"
            self_href = f"{base}{self_prefix}/{clean_rel}" if clean_rel else f"{base}{self_prefix}/"
            seo = [_Node(kind="el", tag="link", attrs=[("rel", "canonical"), ("href", self_href)])]
            for alt_l in all_langs:
                p = "" if alt_l == "en" else f"/{alt_l}"
                href = f"{base}{p}/{clean_rel}" if clean_rel else f"{base}{p}/"
                seo.append(_Node(kind="el", tag="link", attrs=[("rel", "alternate"), ("hreflang", alt_l), ("href", href)]))
            seo.append(_Node(kind="el", tag="link",
                              attrs=[("rel", "alternate"), ("hreflang", "x-default"),
                                     ("href", f"{base}/{clean_rel}" if clean_rel else f"{base}/")]))
            for sn in seo:
                node.children.append(_Node(kind="text", text="\n  "))
                node.children.append(sn)
            node.children.append(_Node(kind="text", text="\n"))
            return

        if lang != "en" and node.tag not in ("script", "style", "code", "pre"):
            raw_inner = node.inner_html()
            trimmed = raw_inner.strip()
            if trimmed and trimmed in match_to_target:
                lead = raw_inner[: len(raw_inner) - len(raw_inner.lstrip())]
                trail = raw_inner[len(raw_inner.rstrip()):]
                node.children = parse_fragment(f"{lead}{match_to_target[trimmed]}{trail}")
                return

        for c in node.children:
            walk(c)

    for top in builder.root.children:
        walk(top)
    return builder.root.to_html()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Splice translated catalog into localized HTML.")
    ap.add_argument("--src-dir", default=".")
    ap.add_argument("--out-dir", default="dist/fr")
    ap.add_argument("--source", default="data/i18n/source.json")
    ap.add_argument("--target", default="data/i18n/fr.json")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--base-url", default="https://chrislloyd.io")
    args = ap.parse_args(argv)

    source = load_source(args.source)
    target = load_target(args.target)

    src_root = Path(args.src_dir)
    out_root = Path(args.out_dir)
    count = 0
    for html_file in sorted(src_root.glob("*.html")):
        rel = html_file.relative_to(src_root)
        rendered = splice_html_document(
            html_file.read_text(encoding="utf-8"), source, target, args.lang,
            args.base_url, rel.as_posix(),
        )
        dest = out_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        count += 1
    print(f"[splice:{args.lang}] built {count} localized page(s) in {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
