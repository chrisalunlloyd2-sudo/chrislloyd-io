#!/usr/bin/env python3
"""chrislloyd-io/scripts/i18n_seed.py -- Phase 5.2: deterministic seeding via life.xlate.

Writes new translations into fr.json using its EXISTING shape only (fr[section][key] =
plain string) -- never a {"target":...} wrapper. Provenance/hash bookkeeping goes in the
sidecar (data/i18n/.meta_<lang>.json), never inside fr.json. An ABSTAIN never touches
fr.json at all; it's recorded in a review file for a human (or a richer glossary) later.
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

LIFE_DIR = os.environ.get("CLAUDE_LIFE_DIR", "/root/Claude/life")
if LIFE_DIR not in sys.path:
    sys.path.insert(0, LIFE_DIR)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from xlate.gate import TranslationCombiningGate  # noqa: E402
from xlate.phrases import PhraseTable  # noqa: E402
from _i18n_common import load_meta, load_target, save_meta, save_target, sha256_short, shield_tags_and_vars, unshield_tags_and_vars  # noqa: E402


def seed_translations(todo: dict, todo_sections: dict, target: dict, table: PhraseTable):
    """todo: key -> source text to translate (plain key, or rich item's html).
    todo_sections: key -> "p"|"r". Mutates nothing; returns (updated_target, updated_meta_r, review)."""
    updated = {"p": dict(target.get("p", {})), "r": dict(target.get("r", {}))}
    meta_r_updates = {}
    review = {}
    committed = 0
    oov_counter = Counter()

    for key in sorted(todo):
        section = todo_sections.get(key, "p")
        src_text = todo[key]
        shielded, sentinel_map = shield_tags_and_vars(src_text)

        local_table = PhraseTable(keep_terms=list(sentinel_map.keys()))
        for entry in table.entries:
            local_table.add_entry(entry)
        gate = TranslationCombiningGate(local_table, nbsp_punctuation=True)
        decision = gate.translate(shielded)

        if decision.decision == "COMMIT":
            restored = unshield_tags_and_vars(decision.target_text, sentinel_map)
            updated[section][key] = restored
            if section == "r":
                meta_r_updates[key] = {"html_hash": sha256_short(src_text), "origin": "xlate"}
            committed += 1
        else:
            for tok in decision.unknown_source_tokens:
                oov_counter[tok.lower()] += 1
            review[key] = {
                "section": section,
                "source": src_text,
                "confidence": decision.confidence,
                "unknown_tokens": list(decision.unknown_source_tokens),
                "reasons": list(decision.reasons),
            }

    review_report = {
        "committed_count": committed,
        "abstained_count": len(review),
        "top_missing_glossary_words": [{"word": w, "occurrences": c} for w, c in oov_counter.most_common(50)],
        "queue": review,
    }
    return updated, meta_r_updates, review_report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seed deterministic translations via life.xlate.")
    ap.add_argument("--work", default="data/i18n/work_fr.json")
    ap.add_argument("--target", default="data/i18n/fr.json")
    ap.add_argument("--meta", default="data/i18n/.meta_fr.json")
    ap.add_argument("--glossary", default=os.path.join(LIFE_DIR, "xlate", "data", "en-fr.json"))
    ap.add_argument("--phrases", default="data/i18n/phrases_en_fr.json")
    ap.add_argument("--keep", default="data/i18n/keep.json")
    ap.add_argument("--review-out", default="data/i18n/review_fr.json")
    ap.add_argument("--lang", default="fr")
    ap.add_argument("--dry-run", action="store_true", help="compute but never write target/meta")
    args = ap.parse_args(argv)

    work = json.loads(Path(args.work).read_text(encoding="utf-8"))
    target = load_target(args.target)
    meta = load_meta(args.meta)

    table = PhraseTable.from_json_files(
        phrases_path=args.phrases if Path(args.phrases).exists() else None,
        glossary_path=args.glossary if Path(args.glossary).exists() else None,
        keep_path=args.keep if Path(args.keep).exists() else None,
    )

    updated, meta_r_updates, review_rep = seed_translations(
        work.get("todo", {}), work.get("todo_sections", {}), target, table)

    if not args.dry_run:
        save_target(args.target, updated)
        if meta_r_updates:
            meta.setdefault("r", {}).update(meta_r_updates)
            save_meta(args.meta, meta)

    rev_p = Path(args.review_out)
    rev_p.parent.mkdir(parents=True, exist_ok=True)
    rev_p.write_text(json.dumps(review_rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[seed:{args.lang}] committed={review_rep['committed_count']} "
          f"abstained={review_rep['abstained_count']}" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
