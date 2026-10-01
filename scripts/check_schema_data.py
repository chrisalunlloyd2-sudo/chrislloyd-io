#!/usr/bin/env python3
"""check_schema_data.py — deterministic task-029 structured-data validator (no LLM).

Asserts the JSON-LD contracts WITHOUT a browser:
  1. index.html #local-business-jsonld parses and its NAP triple (name,
     telephone, streetAddress/postalCode) matches data/site.json.
  2. Index block carries url/image/logo/sameAs; placeholder socials are absent.
  3. Area pages (st-albert, sherwood-park, leduc, spruce-grove) each carry a
     JSON-LD block that parses and matches the same NAP.
  4. data/faq.json: 6 entries, each with non-empty q and a (FAQPage contract
     served by assets/main.js renderFAQ — no static duplicate in the HTML).

Run: python3 scripts/check_schema_data.py   (exit 0 = pass, 1 = failures)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []

AREA_SLUGS = ["st-albert", "sherwood-park", "leduc", "spruce-grove"]
PAGES_BASE = "https://chrisalunlloyd2-sudo.github.io/chrislloyd-io/"
GITHUB_URL = "https://github.com/chrisalunlloyd2-sudo"

# site.json phone is display-formatted; the JSON-LD wire format is E.164-style.
EXPECT_NAP = {
    "name": "Chris Alun Lloyd Ltd",
    "telephone": "+1-587-926-4323",
    "streetAddress": "10412 66 Ave NW",
    "postalCode": "T6H 1V9",
}


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + ((" — " + detail) if detail else ""))
    if not cond:
        failures.append(label)


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def jsonld_blocks(html):
    out = []
    for m in re.finditer(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL,
    ):
        try:
            out.append(json.loads(m.group(1)))
        except json.JSONDecodeError as exc:
            out.append({"__parse_error__": str(exc)})
    return out


def nap_ok(biz, where):
    addr = biz.get("address") or {}
    for key, want in EXPECT_NAP.items():
        got = biz.get(key) if key != "streetAddress" and key != "postalCode" else addr.get(key)
        check(f"[{where}] NAP {key} matches site.json", got == want, f"got {got!r}")


def biz_blocks(where, blocks):
    biz = [b for b in blocks if b.get("@type") == "HomeAndConstructionBusiness" and "__parse_error__" not in b]
    return biz[0] if biz else None


# --- 1+2: index.html LocalBusiness -------------------------------------------
index_html = read("index.html")
site = json.loads(read("data/site.json")).get("site", {})
blocks = jsonld_blocks(index_html)
check("index.html JSON-LD blocks all parse as JSON",
      all("__parse_error__" not in b for b in blocks),
      "; ".join(b["__parse_error__"] for b in blocks if "__parse_error__" in b))
biz = biz_blocks("index", blocks)
check("index.html has LocalBusiness JSON-LD", biz is not None)
if biz:
    nap_ok(biz, "index")
    check("[index] url is the Pages URL", biz.get("url") == PAGES_BASE, f"got {biz.get('url')!r}")
    og = PAGES_BASE + "assets/og-image.png"
    check("[index] image absolute og-image", biz.get("image") == og, f"got {biz.get('image')!r}")
    check("[index] logo absolute og-image", biz.get("logo") == og, f"got {biz.get('logo')!r}")
    check("[index] sameAs is GitHub only", biz.get("sameAs") == [GITHUB_URL],
          f"got {biz.get('sameAs')!r}")
    same_as = biz.get("sameAs") or []
    site_socials = {s.get("url") for s in json.loads(read("data/site.json")).get("socials", [])
                    if s.get("placeholder") is True}
    check("[index] no placeholder socials in sameAs", not (set(same_as) & site_socials))

# --- 3: area pages ------------------------------------------------------------
for slug in AREA_SLUGS:
    ablocks = jsonld_blocks(read(slug + ".html"))
    check(f"[{slug}] JSON-LD blocks all parse",
          all("__parse_error__" not in b for b in ablocks),
          "; ".join(b["__parse_error__"] for b in ablocks if "__parse_error__" in b))
    abiz = biz_blocks(slug, ablocks)
    check(f"[{slug}] has LocalBusiness JSON-LD", abiz is not None)
    if abiz:
        nap_ok(abiz, slug)
        check(f"[{slug}] url is the per-page Pages URL",
              abiz.get("url") == PAGES_BASE + slug + ".html", f"got {abiz.get('url')!r}")
        check(f"[{slug}] sameAs GitHub only", abiz.get("sameAs") == [GITHUB_URL],
              f"got {abiz.get('sameAs')!r}")

# --- 4: FAQ data contract ------------------------------------------------------
faq = json.loads(read("data/faq.json")).get("faq", [])
check("faq.json has 6 entries", len(faq) == 6, f"got {len(faq)}")
for i, item in enumerate(faq):
    check(f"faq[{i}] non-empty q/a",
          isinstance(item.get("q"), str) and item["q"].strip()
          and isinstance(item.get("a"), str) and item["a"].strip())
check("no static FAQPage JSON-LD duplicate in index.html",
      '"@type"' not in index_html or "FAQPage" not in index_html)

# --- generator parity guard ----------------------------------------------------
gen = read("scripts/gen_area_pages.py")
for field in ('"image"', '"logo"', '"sameAs"'):
    check(f"gen_area_pages.py emits {field}", field in gen)

sys.exit(1 if failures else 0)