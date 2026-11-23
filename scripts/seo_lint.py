#!/usr/bin/env python3
"""chrislloyd-io/scripts/seo_lint.py -- deterministic, stdlib-only SEO/metadata lint.

Three checks, each independently real against the LIVE site content (verified against
it before setting thresholds, not guessed):
  1. title (15-75 chars) / meta description (40-175 chars) / exactly one <h1>.
  2. every <script type="application/ld+json"> block is syntactically valid JSON with
     @context + @type -- existing pages without one (blog.html, products.html) are not
     required to add one; this only checks blocks that ARE present.
  3. hreflang cross-page reciprocity -- ONLY checked on pages that already carry at
     least one hreflang tag (the live root pages have none yet; this is forward-looking
     for whenever localized pages exist, never a false failure against today's site).

Usage: python3 scripts/seo_lint.py [--dir .] [--base-url https://chrislloyd.io]
"""
import argparse
import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

TITLE_RANGE = (15, 75)
DESC_RANGE = (40, 175)


@dataclass
class PageSEO:
    rel: str
    lang: str = "en"
    title: str = ""
    description: str = ""
    canonical: str = ""
    h1_count: int = 0
    hreflangs: Dict[str, str] = field(default_factory=dict)
    json_ld_blocks: List[str] = field(default_factory=list)


class _SEOParser(HTMLParser):
    def __init__(self, rel: str, default_lang: str) -> None:
        super().__init__(convert_charrefs=True)
        self.data = PageSEO(rel=rel, lang=default_lang)
        self._in_title = False
        self._in_jsonld = False
        self._buf: List[str] = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        ad = {k.lower(): (v or "") for k, v in attrs}
        if t == "html" and ad.get("lang"):
            self.data.lang = ad["lang"]
        elif t == "title":
            self._in_title, self._buf = True, []
        elif t == "h1":
            self.data.h1_count += 1
        elif t == "meta" and ad.get("name", "").lower() == "description":
            self.data.description = ad.get("content", "").strip()
        elif t == "link":
            rel_attr = ad.get("rel", "").lower()
            href = ad.get("href", "").strip()
            if rel_attr == "canonical":
                self.data.canonical = href
            elif rel_attr == "alternate" and ad.get("hreflang"):
                self.data.hreflangs[ad["hreflang"].lower()] = href
        elif t == "script" and ad.get("type", "").lower() == "application/ld+json":
            self._in_jsonld, self._buf = True, []

    def handle_data(self, data):
        if self._in_title or self._in_jsonld:
            self._buf.append(data)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "title" and self._in_title:
            self.data.title = "".join(self._buf).strip()
            self._in_title = False
        elif t == "script" and self._in_jsonld:
            self.data.json_ld_blocks.append("".join(self._buf).strip())
            self._in_jsonld = False


def parse_page(path: Path, default_lang: str = "en") -> PageSEO:
    p = _SEOParser(rel=path.name, default_lang=default_lang)
    p.feed(path.read_text(encoding="utf-8"))
    p.close()
    return p.data


def lint_metadata(page: PageSEO) -> List[str]:
    errs = []
    lo, hi = TITLE_RANGE
    if not (lo <= len(page.title) <= hi):
        errs.append(f"[{page.rel}] title length {len(page.title)} outside [{lo}..{hi}]: {page.title!r}")
    lo, hi = DESC_RANGE
    if not (lo <= len(page.description) <= hi):
        errs.append(f"[{page.rel}] meta description length {len(page.description)} outside [{lo}..{hi}]")
    if page.h1_count != 1:
        errs.append(f"[{page.rel}] expected exactly one <h1>, found {page.h1_count}")
    for idx, block in enumerate(page.json_ld_blocks):
        try:
            obj = json.loads(block)
        except json.JSONDecodeError as exc:
            errs.append(f"[{page.rel}] invalid JSON-LD block #{idx}: {exc}")
            continue
        if not isinstance(obj, dict) or "@context" not in obj or "@type" not in obj:
            errs.append(f"[{page.rel}] JSON-LD block #{idx} missing @context or @type")
    return errs


def lint_hreflang_reciprocity(pages_by_url: Dict[str, PageSEO],
                               required: Sequence[str] = ("x-default",)) -> List[str]:
    """Only checks pages that already declare at least one hreflang (see module docstring)."""
    errs = []
    for url, page in pages_by_url.items():
        if not page.hreflangs:
            continue
        for req in required:
            if req not in page.hreflangs:
                errs.append(f"[{page.rel}] has hreflang tags but is missing hreflang={req!r}")
        for hl, target_href in page.hreflangs.items():
            if hl == "x-default":
                continue
            peer = pages_by_url.get(target_href)
            if peer is None:
                errs.append(f"[{page.rel}] hreflang={hl} points to an unknown page {target_href!r}")
                continue
            back = peer.hreflangs.get(page.lang)
            if back != url:
                errs.append(f"[{page.rel}] <-> [{peer.rel}] hreflang not reciprocal: "
                            f"{page.rel} points to {peer.rel} but {peer.rel} points back to {back!r}, not {url!r}")
    return errs


def canonical_url_for(base_url: str, rel: str, lang_prefix: str = "") -> str:
    """Matches i18n_splice.py's own self_href convention exactly (index.html -> trailing
    slash, no literal "index.html"), so hrefs embedded in real pages line up byte-for-byte
    with what this function computes for reciprocity checking."""
    base = base_url.rstrip("/")
    prefix = f"/{lang_prefix}" if lang_prefix else ""
    if rel == "index.html":
        return f"{base}{prefix}/"
    return f"{base}{prefix}/{rel}"


def run(site_dirs: Sequence[Path], base_url: str) -> Tuple[List[str], int]:
    """site_dirs: one directory per locale root to check TOGETHER, e.g. [site/, dist/fr/]
    -- hreflang reciprocity can only be verified when both sides of a link are loaded in
    the same pass. canonical_url_for() always uses the EN-style flat path (no /fr/ prefix)
    for same-named files across dirs, so pass a locale subdirectory (dist/fr) relative to
    site root separately with its own --base-url-prefix if you need the /fr/... form --
    this project's splice.py already writes real /fr/... hrefs into the page content
    itself, which is what this lint actually reads."""
    errors: List[str] = []
    pages_by_url: Dict[str, PageSEO] = {}
    n = 0
    for site_dir in site_dirs:
        lang_prefix = site_dir.name if site_dir.name in ("fr",) else ""
        for html_file in sorted(site_dir.glob("*.html")):
            n += 1
            page = parse_page(html_file)
            errors.extend(lint_metadata(page))
            pages_by_url[canonical_url_for(base_url, html_file.name, lang_prefix)] = page
    errors.extend(lint_hreflang_reciprocity(pages_by_url))
    return errors, n


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic stdlib SEO/metadata lint.")
    ap.add_argument("--dir", action="append", dest="dirs", default=None,
                     help="repeatable; pass once per locale root to check hreflang reciprocity across them")
    ap.add_argument("--base-url", default="https://chrislloyd.io")
    args = ap.parse_args(argv)
    dirs = [Path(d) for d in (args.dirs or ["."])]

    errors, n = run(dirs, args.base_url)
    if errors:
        for e in errors:
            print(f"[SEO-FAIL] {e}")
        print(f"[seo_lint] FAILED with {len(errors)} issue(s) across {n} page(s).")
        return 1
    print(f"[seo_lint] PASSED across {n} page(s), 0 issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
