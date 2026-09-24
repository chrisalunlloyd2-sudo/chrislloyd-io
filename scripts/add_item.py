#!/usr/bin/env python3
"""Append an entry to one of /data/*.json in this repo — the "easy to automate" helper.

Usage:
  python3 scripts/add_item.py services --title "Decking build" --desc "Garden decking." --icon tools --category labour
  python3 scripts/add_item.py shop --title "Trade roller set" --url "https://amzn.to/xxx" --category Paint
  python3 scripts/add_item.py opensource --title "my-repo" --desc "..." --url https://github.com/me/my-repo --tags cli,tcp
  python3 scripts/add_item.py reviews --title "Trade matt 10L" --desc "..." --category Paint --rating 4
  python3 scripts/add_item.py site --field tagline --value "New tagline"

JSON-encodes unknown extra keys; validates the result; writes atomically.
"""
import argparse, json, os, sys, tempfile

VALID = ("services", "shop", "opensource", "reviews", "site")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allowed keys per collection (site uses --field/--value instead).
SCHEMA = {
    "services":   ["id", "title", "desc", "icon", "category", "placeholder"],
    "shop":       ["id", "title", "desc", "category", "url", "url_label", "placeholder"],
    "opensource": ["id", "title", "desc", "url", "tags"],
    "reviews":    ["id", "title", "desc", "category", "rating", "placeholder"],
}

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save(path, data):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise

def slug(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:60] or "item"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="collection", required=True)
    for name in VALID:
        sp = sub.add_parser(name)
        if name == "site":
            sp.add_argument("--field", required=True)
            sp.add_argument("--value", required=True)
        else:
            for key in SCHEMA[name]:
                if key == "tags":
                    continue  # --tags added once below for opensource
                sp.add_argument("--" + key)
            if name == "opensource":
                sp.add_argument("--tags", help="comma-separated")
    args = ap.parse_args()

    path = os.path.join(ROOT, "data", f"{args.collection}.json")

    if args.collection == "site":
        data = load(path)
        data["site"][args.field] = args.value
        save(path, data)
        print(f"site.{args.field} = {args.value!r} -> {path}")
        return

    items = load(path)
    entry = {k: v for k, v in vars(args).items()
             if k in SCHEMA[args.collection] and v is not None}
    if args.collection == "opensource" and args.tags:
        entry["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if not entry:
        sys.exit("error: nothing to add")
    if "id" not in entry:
        entry["id"] = slug(entry.get("title", "item"))
    if "title" not in entry and "id" in entry:
        entry["title"] = entry["id"].replace("-", " ").title()
    if args.collection == "shop" and "placeholder" not in entry and not entry.get("url"):
        entry["placeholder"] = True
    if args.collection == "reviews" and "rating" in entry:
        try:
            entry["rating"] = max(1, min(5, int(entry["rating"])))
        except ValueError:
            entry.pop("rating", None)
    if args.collection in ("services", "reviews") and "placeholder" not in entry:
        entry["placeholder"] = False if entry.get("desc") and "PLACEHOLDER" not in entry.get("desc", "") else True

    items.append(entry)
    save(path, items)
    print(f"added to {args.collection}: {entry.get('id')} -> {path}")

if __name__ == "__main__":
    main()