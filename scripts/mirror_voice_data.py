#!/usr/bin/env python3
"""mirror_voice_data.py — daily read-only mirror of the site's data/*.json into
~/.life/voice-data/, for the voice assistant (PLAN-VOICE-100 step 67 consumer;
this is PLAN-SITE-100 step 19, the counterpart of the dashboard's Voice tab
writing into ~/.life/voice-inbox).

Contract (hard rules):
  * Copies data/faq.json and data/area-pages.json VERBATIM (raw bytes) — the
    mirror NEVER rewords, summarizes, or re-serializes site copy, so any
    consumer (voice_facts.py) sees byte-identical q/a text.
  * Idempotent: safe to run daily via cron or by hand; overwrites in place,
    never appends.
  * Writes manifest.json alongside (source paths, sizes, sha256, UTC time) so
    the voice side can detect drift without parsing the copy itself.

Run:  python3 scripts/mirror_voice_data.py            (mirror into ~/.life/voice-data)
      python3 scripts/mirror_voice_data.py --out DIR  (mirror elsewhere; used by tests)
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
MIRROR_DIR = os.path.expanduser(os.path.join("~", ".life", "voice-data"))
FILES = ["faq.json", "area-pages.json"]  # voice steps 67 (FAQ) + 69 (areas)


def mirror(out_dir: str = MIRROR_DIR) -> dict:
    """Copy the voice-relevant data/*.json files verbatim into out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    sources = []
    for name in FILES:
        src = os.path.join(DATA_DIR, name)
        dst = os.path.join(out_dir, name)
        shutil.copyfile(src, dst)
        raw = open(src, "rb").read()
        sources.append(
            {"file": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    manifest = {
        "when_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": sources,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror site data/*.json into ~/.life/voice-data (verbatim).")
    ap.add_argument("--out", default=MIRROR_DIR, help="mirror target dir (default ~/.life/voice-data)")
    args = ap.parse_args()
    m = mirror(args.out)
    print("mirrored: " + ", ".join(s["file"] for s in m["sources"]) + " -> " + args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
