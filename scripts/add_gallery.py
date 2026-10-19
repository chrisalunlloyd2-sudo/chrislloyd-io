#!/usr/bin/env python3
"""Add a real before/after pair to the site gallery (the helper Alice runs).

  python3 scripts/add_gallery.py --before b.jpg --after a.jpg \
      --title "Bedroom repaint" --caption "Walls and ceiling, two coats." \
      --alt-before "Bedroom walls before painting" --alt-after "Same bedroom after painting" \
      --client-ok [--location "Edmonton"] [--year 2026]

What it does: re-saves both photos as max-1200px JPEGs (this drops EXIF, including GPS
location), writes them to assets/gallery/, appends an entry to data/gallery.json with
placeholder=false, and un-hides the Before & After section with a nav link.
Nothing is invented: title, caption and both alt texts are required, and --client-ok
confirms Chris has the customer's OK to publish photos of their home.
Then run the tests, commit and push (see docs/PHOTOS.md). Does not git push itself.
"""
import argparse, json, os, re, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAL = os.path.join(ROOT, "data", "gallery.json")
INDEX = os.path.join(ROOT, "index.html")
MAXPX = 1200


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "job"


def save_jpeg(src, dest):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((MAXPX, MAXPX))
    clean = Image.new("RGB", im.size)
    clean.paste(im)
    clean.save(dest, "JPEG", quality=82, optimize=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("before", "after", "title", "caption", "alt-before", "alt-after"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--location", default="")
    ap.add_argument("--year", default="")
    ap.add_argument("--client-ok", action="store_true", help="customer has OK'd publishing")
    ap.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not a.client_ok:
        sys.exit("refused: pass --client-ok only after Chris confirms the customer agreed to photos of their home being public")
    if a.year and not a.year.isdigit():
        sys.exit("refused: --year must be digits")
    for p in (a.before, a.after):
        if not os.path.isfile(p):
            sys.exit("refused: no such file " + p)
    for t in (a.title, a.caption, a.alt_before, a.alt_after):
        if not t.strip() or "PLACEHOLDER" in t.upper():
            sys.exit("refused: title/caption/alt text must be real text")
    root = a.root
    gal, index = os.path.join(root, "data", "gallery.json"), os.path.join(root, "index.html")
    items = json.load(open(gal, encoding="utf-8"))
    base = slug(a.title)
    ids = {i.get("id") for i in items}
    n, eid = 1, base
    while eid in ids:
        n += 1
        eid = f"{base}-{n}"
    outdir = os.path.join(root, "assets", "gallery")
    os.makedirs(outdir, exist_ok=True)
    srcs = {}
    for side, p in (("before", a.before), ("after", a.after)):
        rel = f"assets/gallery/{eid}-{side}.jpg"
        save_jpeg(p, os.path.join(root, rel))
        srcs[side] = rel
    entry = {"id": eid, "title": a.title.strip(), "caption": a.caption.strip(),
             "before": {"src": srcs["before"], "alt": a.alt_before.strip()},
             "after": {"src": srcs["after"], "alt": a.alt_after.strip()},
             "location": a.location.strip(), "year": a.year, "placeholder": False}
    items = [i for i in items if not i.get("placeholder")] + [entry]
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(gal), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, gal)
    html = open(index, encoding="utf-8").read()
    html = html.replace('<section id="gallery" hidden ', '<section id="gallery" ', 1)
    if 'href="#gallery"' not in html:
        html = html.replace('<a href="#faq">FAQ</a>', '<a href="#gallery">Gallery</a><a href="#faq">FAQ</a>', 1)
    open(index, "w", encoding="utf-8").write(html)
    print("added", eid, "->", srcs["before"], srcs["after"])


if __name__ == "__main__":
    main()
