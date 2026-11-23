"""chrislloyd-io/scripts/_i18n_common.py -- shared stdlib helpers for the Phase 5 i18n
pipeline (seek/seed/shape/splice/sift), built against the REAL on-disk schema:

  data/i18n/source.json  -- list of {"key": <english text>, "rich": bool, "src": [...],
                             "html"?: <inner HTML, rich only>} (written by i18n_extract.py)
  data/i18n/<lang>.json  -- {"p": {english_key: translation}, "r": {english_key: html}}
  data/i18n/keep.json    -- list of english_keys deliberately left identical (cognates,
                             proper nouns); test_i18n.py already enforces this allowlist.

data/i18n/<lang>.json's values are always plain strings -- NEVER {"target":..., "hash":...}
dicts -- by Chris's explicit decision (2026-11-23): the live, already-approved catalog's
shape never changes. Per-entry staleness/provenance metadata lives in a separate sidecar,
data/i18n/.meta_<lang>.json, keyed the same way ({"r": {key: {"html_hash":..., "origin":...}}}
-- "p" entries need no hash: a plain key IS its own source text, so a source edit shows up
as a missing key + an orphan, never a same-key content drift. Only rich entries can drift
(key = collapsed text stays put while the html markup around it changes), so only "r" is
hashed.
"""
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i18n_extract import VOID_TAGS as VOID_ELEMENTS  # noqa: E402  (keep one void-tag list)

PLACEHOLDER_RE = re.compile(
    r"(\{[A-Za-z0-9_.-]+\}|\{\{[A-Za-z0-9_.\s-]+\}\}|%(?:\([A-Za-z0-9_]+\))?[sdif])"
)
INLINE_TAG_RE = re.compile(r"(<[^>]+>)")


def sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_source(path) -> List[Dict[str, Any]]:
    """The real source.json: a list of {"key", "rich", "src", "html"?} items, unchanged."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def match_text(item: Dict[str, Any]) -> str:
    """The text a rich item's html must agree with for staleness hashing / DOM matching;
    for a plain item this is just its key (key IS the content)."""
    return item["html"] if item.get("rich") else item["key"]


def load_target(path) -> Dict[str, Dict[str, str]]:
    """The real <lang>.json: {"p": {key: str}, "r": {key: str}}. Missing file -> empty
    catalog (nothing translated yet), not an error."""
    p = Path(path)
    if not p.exists():
        return {"p": {}, "r": {}}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return {"p": dict(data.get("p", {})), "r": dict(data.get("r", {}))}


def save_target(path, data: Dict[str, Dict[str, str]]) -> None:
    """Same formatting AND key order i18n_extract.py's own sync_catalog() already writes
    (insertion order, NOT sorted -- only fr-archive.json gets sort_keys=True there), so a
    real commit's diff shows only the genuinely new/changed entries, not a whole-file
    reshuffle. Caller is responsible for building `data` by mutating a loaded dict in
    place (existing keys keep their position; only brand-new keys append at the end)."""
    payload = {"p": dict(data.get("p", {})), "r": dict(data.get("r", {}))}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)  # no trailing \n: matches sync_catalog()


def load_keep(path) -> set:
    p = Path(path)
    if not p.exists():
        return set()
    with open(p, encoding="utf-8") as f:
        return set(json.load(f))


def load_meta(path) -> Dict[str, Dict[str, Dict[str, str]]]:
    """The sidecar: data/i18n/.meta_<lang>.json. Never required for the site to render or
    for sync_store.py's daily job -- missing/corrupt is just 'no provenance recorded yet'."""
    p = Path(path)
    if not p.exists():
        return {"r": {}}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"r": {}}
    return {"r": dict(data.get("r", {}))}


def save_meta(path, meta: Dict[str, Dict[str, Dict[str, str]]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"r": dict(sorted(meta.get("r", {}).items()))}, f, ensure_ascii=False, indent=1)
        f.write("\n")


def shield_tags_and_vars(text: str) -> Tuple[str, Dict[str, str]]:
    """Replaces inline <tags> and {vars}/%s with XKEEP0X-style sentinels safe to carry
    through life.xlate (which would otherwise see a bare '<' as an unknown/garbage token)."""
    mapping: Dict[str, str] = {}
    counter = 0

    def _sub(match: "re.Match[str]") -> str:
        nonlocal counter
        sentinel = f"XKEEP{counter}X"
        mapping[sentinel] = match.group(0)
        counter += 1
        return sentinel

    step1 = INLINE_TAG_RE.sub(_sub, text)
    step2 = PLACEHOLDER_RE.sub(_sub, step1)
    return step2, mapping


def unshield_tags_and_vars(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for sentinel, orig in mapping.items():
        out = out.replace(sentinel, orig)
    return out


class TagSignatureExtractor(HTMLParser):
    """Extracts an ordered list of (tag, sorted_key_attrs) for a rich entry's tag-parity
    check -- source item['html'] vs its fr['r'][key] translation must open/close the same
    structural tags (href, src, id, class, target, rel), ignoring translatable attrs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.open_tags: List[Tuple[str, Tuple[Tuple[str, Optional[str]], ...]]] = []
        self.close_tags: List[str] = []

    def _structural(self, attrs):
        return tuple(sorted((k, v) for k, v in attrs if k not in ("title", "alt", "aria-label")))

    def handle_starttag(self, tag, attrs):
        self.open_tags.append((tag.lower(), self._structural(attrs)))

    def handle_startendtag(self, tag, attrs):
        self.open_tags.append((tag.lower(), self._structural(attrs)))

    def handle_endtag(self, tag):
        t = tag.lower()
        if t not in VOID_ELEMENTS:
            self.close_tags.append(t)
