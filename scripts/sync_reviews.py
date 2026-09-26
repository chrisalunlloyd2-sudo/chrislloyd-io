#!/usr/bin/env python3
"""Sync raw review notes into data/reviews.json. Pure parsing, no model needed.

Inbox format (one entry per '## ' heading):

    ## Trade matt emulsion, 10L
    category: Paint
    rating: 4
    Goes on thick, covers in one coat, barely any smell.

'rating:' is optional and is omitted from output when absent -- a rating is
never inferred. Entries whose heading ends in '[synced]' are skipped.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

SYNCED = "[synced]"
META_RE = re.compile(r"^(category|rating)\s*:\s*(.+)$", re.IGNORECASE)


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def parse(inbox_text):
    """Return (entries, heading_line_numbers) for unsynced '## ' blocks."""
    entries, lines = [], inbox_text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("## ")]

    for n, start in enumerate(starts):
        heading = lines[start][3:].strip()
        if heading.endswith(SYNCED):
            continue
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)

        meta, body = {}, []
        for ln in lines[start + 1 : end]:
            stripped = ln.strip()
            if stripped.startswith("<!--") or stripped in ("", "---"):
                continue
            match = META_RE.match(stripped)
            if match and not body:
                meta[match.group(1).lower()] = match.group(2).strip()
            else:
                body.append(stripped)

        entries.append({"line": start, "title": heading, "meta": meta,
                        "desc": " ".join(body).strip()})
    return entries


def build(entry, existing_ids):
    title, meta = entry["title"], entry["meta"]
    if not entry["desc"]:
        sys.exit(f"error: '{title}' has no note text under it -- add a line "
                 f"describing the product, then re-run.")
    if "category" not in meta:
        sys.exit(f"error: '{title}' is missing a 'category:' line (e.g. "
                 f"'category: Paint' or 'category: Supplies').")

    out = {"id": slug(title), "title": title,
           "category": meta["category"], "desc": entry["desc"]}

    if "rating" in meta:
        try:
            rating = int(meta["rating"].split("/")[0].strip())
        except ValueError:
            sys.exit(f"error: '{title}' has a non-numeric rating "
                     f"({meta['rating']!r}). Use e.g. 'rating: 4'.")
        if not 1 <= rating <= 5:
            sys.exit(f"error: '{title}' rating must be 1-5, got {rating}.")
        out["rating"] = rating

    suffix = 2
    while out["id"] in existing_ids:
        out["id"] = f"{slug(title)}-{suffix}"
        suffix += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inbox", required=True, type=Path)
    ap.add_argument("--reviews", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    inbox_text = args.inbox.read_text(encoding="utf-8")
    entries = parse(inbox_text)
    if not entries:
        print("no unsynced entries -- nothing to do")
        return 0

    reviews = json.loads(args.reviews.read_text(encoding="utf-8"))
    ids = {r.get("id") for r in reviews}
    added = [build(e, ids) for e in entries]
    for item in added:
        ids.add(item["id"])

    # Real reviews supersede the shipped placeholder examples.
    kept = [r for r in reviews if not r.get("placeholder")]
    dropped = len(reviews) - len(kept)
    reviews = kept + added

    lines = inbox_text.splitlines()
    for entry in entries:
        lines[entry["line"]] = lines[entry["line"]].rstrip() + f" {SYNCED}"
    marked = "\n".join(lines) + "\n"

    if args.dry_run:
        print(json.dumps(added, indent=2))
        print(f"\n(dry run) would add {len(added)}, "
              f"drop {dropped} placeholder(s), mark {len(entries)} synced")
        return 0

    args.reviews.write_text(json.dumps(reviews, indent=2) + "\n", encoding="utf-8")
    args.inbox.write_text(marked, encoding="utf-8")
    print(f"added {len(added)}: {', '.join(r['id'] for r in added)}")
    if dropped:
        print(f"dropped {dropped} placeholder example(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
