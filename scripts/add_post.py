#!/usr/bin/env python3
"""Add a blog post to data/posts.json — the easy-to-automate blog helper.

SEO note (task 017): long-tail, question-style titles are the intended blog
strategy going forward — e.g. "how much does it cost to paint a house
Edmonton", "best time to paint exterior Alberta", "how to prep walls before
painting", "interior vs exterior paint Alberta winters". Informational
shop/dropship angles like "best paint for Alberta winters" also fit the blog;
avoid generic transactional titles ("buy paint online") — they can't compete.

Usage:
  python3 scripts/add_post.py --title "Week on the scaffolds" --date 2026-10-01 \
      --excerpt "One-line summary for the index." \
      --body "First paragraph." --body "Second paragraph."
  python3 scripts/add_post.py --title "From a file" --date 2026-10-01 \
      --excerpt "..." --body-file post.md

Posts are inserted newest-first by date. IDs are slugged from the title and
deduplicated. Writes atomically; validates JSON before saving.
"""
import argparse, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "data", "posts.json")


def load():
    if not os.path.exists(POSTS):
        return []
    with open(POSTS, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    d = os.path.dirname(POSTS)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, POSTS)
    except BaseException:
        os.unlink(tmp)
        raise


def slug(s, taken):
    base = "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:60] or "post"
    cand, n = base, 2
    while cand in taken:
        cand = f"{base}-{n}"
        n += 1
    return cand


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--excerpt", required=True, help="one-liner shown on the index")
    ap.add_argument("--body", action="append", default=[],
                    help="body paragraph (repeatable, in order)")
    ap.add_argument("--body-file", help="read body paragraphs from a text/markdown file "
                                        "(blank lines split paragraphs)")
    args = ap.parse_args()

    body = list(args.body)
    if args.body_file:
        with open(args.body_file, encoding="utf-8") as f:
            paras = [p.strip() for p in re.split(r"\n\s*\n", f.read()) if p.strip()]
        body.extend(paras)
    if not body:
        sys.exit("error: no body — pass --body and/or --body-file")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        sys.exit("error: --date must be YYYY-MM-DD")

    posts = load()
    taken = {p.get("id") for p in posts}
    entry = {
        "id": slug(args.title, taken),
        "title": args.title,
        "date": args.date,
        "excerpt": args.excerpt,
        "body": body,
    }
    posts.append(entry)
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    save(posts)
    # Keep sitemap.xml in sync — placeholder posts are skipped by the generator.
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen_sitemap.py")])
    print(f"added post: {entry['id']} ({entry['date']}) -> {POSTS}")


if __name__ == "__main__":
    main()