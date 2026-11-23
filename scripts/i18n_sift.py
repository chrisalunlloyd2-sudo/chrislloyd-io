#!/usr/bin/env python3
"""chrislloyd-io/scripts/i18n_sift.py -- Phase 5.5: pre-deploy structural & SEO QA gate.
Checks the real source.json/fr.json pair plus any rendered dist/<lang> HTML. Exit 1 on
any defect: placeholder mismatch, HTML tag/attribute mismatch (rich entries), NBSP
leaked into a URL attribute, or missing hreflang/canonical on a rendered page.
"""
import argparse
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_common import PLACEHOLDER_RE, TagSignatureExtractor, load_source, load_target, match_text  # noqa: E402


@dataclass(frozen=True)
class SiftViolation:
    category: str
    location: str
    detail: str


class _PageAuditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: Optional[str] = None
        self.canonical_href: Optional[str] = None
        self.hreflangs: Dict[str, str] = {}
        self.corrupt_urls: List[str] = []

    def _inspect(self, tag, ad):
        if tag == "html":
            self.html_lang = ad.get("lang")
        if tag == "link":
            rel = (ad.get("rel") or "").lower()
            href = ad.get("href") or ""
            if rel == "canonical":
                self.canonical_href = href
            elif rel == "alternate" and ad.get("hreflang"):
                self.hreflangs[str(ad["hreflang"])] = href
        for url_attr in ("href", "src", "action"):
            v = ad.get(url_attr)
            if v and " " in v:
                self.corrupt_urls.append(f"{tag}[{url_attr}]={v!r}")

    def handle_starttag(self, tag, attrs):
        self._inspect(tag.lower(), dict(attrs))

    def handle_startendtag(self, tag, attrs):
        self._inspect(tag.lower(), dict(attrs))


def sift_catalog(source_items: List[Dict], target: Dict[str, Dict[str, str]],
                  require_complete: bool = True) -> List[SiftViolation]:
    violations: List[SiftViolation] = []
    for item in sorted(source_items, key=lambda i: i["key"]):
        section = "r" if item.get("rich") else "p"
        key = item["key"]
        label = key[:60]
        tgt = target.get(section, {}).get(key)
        if not tgt:
            if require_complete:
                violations.append(SiftViolation("MISSING_TRANSLATION", label, section))
            continue
        src_text = match_text(item)
        src_vars = sorted(PLACEHOLDER_RE.findall(src_text))
        tgt_vars = sorted(PLACEHOLDER_RE.findall(tgt))
        if src_vars != tgt_vars:
            violations.append(SiftViolation("PLACEHOLDER_MISMATCH", label, f"{src_vars} vs {tgt_vars}"))
        if section == "r":
            s_sig, t_sig = TagSignatureExtractor(), TagSignatureExtractor()
            s_sig.feed(src_text)
            t_sig.feed(tgt)
            if s_sig.open_tags != t_sig.open_tags or s_sig.close_tags != t_sig.close_tags:
                violations.append(SiftViolation(
                    "TAG_MISMATCH", label,
                    f"open:{s_sig.open_tags}!={t_sig.open_tags} close:{s_sig.close_tags}!={t_sig.close_tags}"))
    return violations


def sift_rendered_html(html_text: str, expected_lang: str, page_name: str,
                        required_hreflangs: Sequence[str] = ("en", "fr", "x-default")) -> List[SiftViolation]:
    a = _PageAuditor()
    a.feed(html_text)
    a.close()
    issues: List[SiftViolation] = []
    if a.html_lang != expected_lang:
        issues.append(SiftViolation("SEO_HEAD", page_name, f"<html lang={a.html_lang!r}> != {expected_lang!r}"))
    if not a.canonical_href:
        issues.append(SiftViolation("SEO_HEAD", page_name, "missing <link rel=canonical>"))
    for hl in required_hreflangs:
        if hl not in a.hreflangs:
            issues.append(SiftViolation("SEO_HEAD", page_name, f"missing hreflang={hl!r}"))
    for bad in a.corrupt_urls:
        issues.append(SiftViolation("CORRUPT_URL", page_name, f"NBSP leaked into URL: {bad}"))
    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sift localized catalog and HTML for QA defects.")
    ap.add_argument("--source", default="data/i18n/source.json")
    ap.add_argument("--target", default="data/i18n/fr.json")
    ap.add_argument("--html-dir", default="dist/fr")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--allow-partial", action="store_true")
    args = ap.parse_args(argv)

    source = load_source(args.source)
    target = load_target(args.target)
    violations = sift_catalog(source, target, require_complete=not args.allow_partial)

    html_root = Path(args.html_dir)
    if html_root.exists():
        for page in sorted(html_root.rglob("*.html")):
            violations.extend(sift_rendered_html(
                page.read_text(encoding="utf-8"), expected_lang=args.lang,
                page_name=page.relative_to(html_root).as_posix()))

    if violations:
        for v in violations:
            print(f"[FAIL:{v.category}] {v.location}: {v.detail}")
        print(f"[sift:{args.lang}] FAILED with {len(violations)} violation(s).")
        return 1
    print(f"[sift:{args.lang}] PASSED (0 violations across {len(source)} strings).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
