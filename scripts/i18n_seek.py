#!/usr/bin/env python3
"""chrislloyd-io/scripts/i18n_seek.py -- Phase 5.1: discover missing & stale strings.

Against the REAL schema: a "p" (plain) entry's key IS its source text, so there is no
such thing as a same-key content drift for plain strings -- an edit always produces a
different key, which just shows up as newly-untranslated (and the dropped old key is
already handled by i18n_extract.py's own --sync, which archives/restores it; not
duplicated here). Only "r" (rich) entries can go stale: the collapsed key can stay the
same while the html around it changes, so staleness is tracked there via a sidecar hash
(data/i18n/.meta_<lang>.json) -- never inside fr.json itself.

Read-only against fr.json: writes only work_<lang>.json (the todo manifest) and, when a
rich entry is translated but has no sidecar hash yet (true for every entry that predates
this pipeline), backfills that hash so it isn't misreported as stale on some later run
once this script starts being run regularly.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_common import load_keep, load_meta, load_source, load_target, match_text, save_meta, sha256_short  # noqa: E402


def seek_catalog_diff(source_items: List[Dict], target: Dict[str, Dict[str, str]],
                       keep: set, meta: Dict[str, Dict[str, Dict[str, str]]]):
    untranslated: Dict[str, Dict] = {}   # key -> source item (needs its section too)
    stale: Dict[str, Dict] = {}          # key -> {"old_hash", "new_hash"} (rich only)
    up_to_date: List[str] = []
    meta_backfill: Dict[str, Dict[str, str]] = {}

    want = {(bool(i["rich"]), i["key"]): i for i in source_items}
    for (rich, key), item in sorted(want.items(), key=lambda kv: kv[0][1]):
        section = "r" if rich else "p"
        existing = target.get(section, {}).get(key)
        if not existing:
            untranslated[key] = {"section": section, "item": item}
            continue
        if existing == key and key not in keep:
            # identical to English, not on the owner's explicit keep-list: most likely
            # just never translated (shown in English), same signal test_i18n.py uses.
            untranslated[key] = {"section": section, "item": item}
            continue
        if not rich:
            up_to_date.append(key)
            continue
        # rich: compare against the sidecar hash of the SOURCE html (not the translation).
        cur_hash = sha256_short(match_text(item))
        recorded = meta.get("r", {}).get(key, {}).get("html_hash")
        if recorded is None:
            meta_backfill[key] = {"html_hash": cur_hash, "origin": "backfill"}
            up_to_date.append(key)
        elif recorded != cur_hash:
            stale[key] = {"old_hash": recorded, "new_hash": cur_hash, "item": item}
        else:
            up_to_date.append(key)

    orphaned = sorted(
        k for section in ("p", "r") for k in target.get(section, {})
        if (section == "r", k) not in want
    )
    return untranslated, stale, up_to_date, orphaned, meta_backfill


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seek untranslated and stale i18n keys.")
    ap.add_argument("--source", default="data/i18n/source.json")
    ap.add_argument("--target", default="data/i18n/fr.json")
    ap.add_argument("--keep", default="data/i18n/keep.json")
    ap.add_argument("--meta", default="data/i18n/.meta_fr.json")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--out", default="data/i18n/work_fr.json")
    args = ap.parse_args(argv)

    source = load_source(args.source)
    target = load_target(args.target)
    keep = load_keep(args.keep)
    meta = load_meta(args.meta)

    untranslated, stale, up_to_date, orphaned, meta_backfill = seek_catalog_diff(
        source, target, keep, meta)

    if meta_backfill:
        meta.setdefault("r", {}).update(meta_backfill)
        save_meta(args.meta, meta)

    todo = {k: v["item"].get("html", v["item"]["key"]) if v["section"] == "r" else v["item"]["key"]
            for k, v in untranslated.items()}
    for k, v in stale.items():
        todo[k] = v["item"].get("html", v["item"]["key"])

    work_payload = {
        "lang": args.lang,
        "summary": {
            "total_source_units": len(source),
            "up_to_date": len(up_to_date),
            "untranslated": len(untranslated),
            "stale": len(stale),
            "orphaned": len(orphaned),
            "meta_backfilled": len(meta_backfill),
        },
        "todo": todo,
        "todo_sections": {k: v["section"] for k, v in untranslated.items()},
        "stale_context": {k: {"old_hash": v["old_hash"], "new_hash": v["new_hash"]} for k, v in stale.items()},
        "orphaned_keys": orphaned,
    }
    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(work_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[seek:{args.lang}] ok={len(up_to_date)} missing={len(untranslated)} "
          f"stale={len(stale)} orphaned={len(orphaned)} meta_backfilled={len(meta_backfill)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
