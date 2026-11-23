#!/usr/bin/env python3
"""chrislloyd-io/scripts/i18n_shape.py -- Phase 5.3: HTML-safe French typographic shaper.

Normalizes French orthography/typography (NBSP before high punctuation, guillemets,
curly apostrophes) on fr.json's own "p" and "r" sections directly -- "p" values are
shaped as plain text, "r" values as HTML fragments (never touching attributes/URLs
inside inline tags). Writes back in fr.json's real shape only.
"""
import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_common import INLINE_TAG_RE, load_target, save_target  # noqa: E402

NBSP = " "
_MULTI_SPACE_RE = re.compile(r" {2,}")
_STRAIGHT_APOS_RE = re.compile(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])'(?=[A-Za-zÀ-ÖØ-öø-ÿ])")
_DOUBLE_QUOTE_RE = re.compile(r'"([^"]+)"')


def shape_french_text_segment(segment: str, curly_apostrophes: bool = True) -> str:
    """Shapes a plain-text segment (guaranteed outside any <tag> markup)."""
    if not segment:
        return segment
    s = segment
    s = _DOUBLE_QUOTE_RE.sub(lambda m: f"«{NBSP}{m.group(1).strip()}{NBSP}»", s)
    s = re.sub(r"«[ \t ]*", f"«{NBSP}", s)
    s = re.sub(r"[ \t ]*»", f"{NBSP}»", s)
    # Python's re needs a fixed-width lookbehind, so a variable-length "don't NBSP a URL
    # scheme colon" guard isn't expressible that way; the real protection (hrefs, inline
    # style attrs) comes from shape_html_fragment only ever handing this function a text
    # node, never tag markup -- the colon branch's (?!//) alone handles "https://" in
    # visible text.
    s = re.sub(r"[ \t ]*([;!?]|:(?!//))", lambda m: f"{NBSP}{m.group(1)}", s)
    if curly_apostrophes:
        s = _STRAIGHT_APOS_RE.sub("’", s)
    s = _MULTI_SPACE_RE.sub(" ", s)
    return s


def shape_html_fragment(html_frag: str, curly_apostrophes: bool = True) -> str:
    """Splits on <...> tags so attributes/URLs inside them are never touched."""
    if not html_frag:
        return html_frag
    parts = INLINE_TAG_RE.split(html_frag)
    out: List[str] = []
    for idx, part in enumerate(parts):
        out.append(part if idx % 2 == 1 else shape_french_text_segment(part, curly_apostrophes))
    return "".join(out)


def shape_catalog(target: Dict[str, Dict[str, str]], curly_apostrophes: bool = True) -> Tuple[Dict, int]:
    changed = 0
    out = {"p": {}, "r": {}}
    for key, val in target.get("p", {}).items():
        shaped = shape_french_text_segment(val, curly_apostrophes)
        out["p"][key] = shaped
        changed += shaped != val
    for key, val in target.get("r", {}).items():
        shaped = shape_html_fragment(val, curly_apostrophes)
        out["r"][key] = shaped
        changed += shaped != val
    return out, changed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Shape target locale typography safely.")
    ap.add_argument("--target", default="data/i18n/fr.json")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--straight-apos", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    target = load_target(args.target)
    shaped, n_changed = shape_catalog(target, curly_apostrophes=not args.straight_apos)
    if not args.dry_run and n_changed:
        save_target(args.target, shaped)
    print(f"[shape:{args.lang}] {n_changed}/{len(shaped['p']) + len(shaped['r'])} entries would change"
          + ("" if args.dry_run else " (written)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
