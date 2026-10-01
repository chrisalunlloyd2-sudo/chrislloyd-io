#!/usr/bin/env python3
"""Generate flat service-area landing pages from data/area-pages.json.

Usage:
  python3 scripts/gen_area_pages.py            # generate all pages
  python3 scripts/gen_area_pages.py --check    # exits 1 if pages are stale

One HTML file per entry in data/area-pages.json -> pages[].slug (st-albert.html,
sherwood-park.html, leduc.html, spruce-grove.html), written beside index.html
in the repo root. Pages are fully static (no JS deps), reuse assets/style.css,
carry per-page canonical/OG/Twitter meta plus LocalBusiness JSON-LD with
areaServed limited to that city, and link to the main site's contact section.

Copy in data/area-pages.json is marked \"draft\": true — the pages therefore
include a visible draft note until the owner flips the top-level flag to false.
Idempotent: re-running rewrites the same files. Run scripts/gen_sitemap.py
afterwards so the sitemap picks the pages up.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "area-pages.json")
SITE = os.path.join(ROOT, "data", "site.json")

DEFAULT_BASE = "https://chrisalunlloyd2-sudo.github.io/chrislloyd-io/"

SERVICES = [
    ("Interior Painting",
     "<p>{city} interior painting: walls, ceilings, trim and woodwork, "
     "with tidy prep and clean lines. Furniture and floors are masked and "
     "protected; dust is minimised rather than swept under the drop sheet.</p>"),
    ("Exterior Painting",
     "<p>{city} exterior work: fascias, soffits, doors, garage siding and "
     "masonry accents, prepped and coated to hold up to an Alberta winter. "
     "Repairs and rot checks are flagged before the first brush stroke.</p>"),
    ("Renovation &amp; Touch-Ups",
     "<p>{city} renovation support: drywall repair and painting, "
     "small refreshes, and finishing touch-ups around the rest of the job. "
     "Handover-ready rather than almost-finished.</p>"),
]

NAV = [
    ("<a href=\"index.html\">Home</a>"),
    ("<a href=\"index.html#services\">Services</a>"),
    ("<a href=\"blog.html\">Blog</a>"),
    ("<a href=\"index.html#contact\">Contact</a>"),
]

FAVICON = ("<link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg "
           "xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
           "%3Cpolygon points='50,4 88,27 88,73 50,96 12,73 12,27' "
           "fill='%23c86e3c'/%3E%3C/svg%3E>")


def base_url():
    try:
        with open(SITE, encoding="utf-8") as f:
            base = (json.load(f).get("site") or {}).get("canonicalBase", "")
        if base:
            return base.rstrip("/") + "/"
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_BASE


def load_data():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def jsonld_for(page):
    biz = {
        "@context": "https://schema.org",
        "@type": "HomeAndConstructionBusiness",
        "name": "Chris Alun Lloyd Ltd",
        "email": "chrisalunlloyd2@gmail.com",
        "telephone": "+1-587-926-4323",
        "url": base_url() + page["slug"] + ".html",
        "image": base_url() + "assets/og-image.png",
        "logo": base_url() + "assets/og-image.png",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "10412 66 Ave NW",
            "addressLocality": "Edmonton",
            "addressRegion": "AB",
            "postalCode": "T6H 1V9",
            "addressCountry": "CA",
        },
        "areaServed": [page["city"]],
        "serviceType": "Residential painting and home renovation",
        "sameAs": ["https://github.com/chrisalunlloyd2-sudo"],
    }
    return json.dumps(biz, indent=2, ensure_ascii=False)


def render(page, is_draft):
    city = page["city"]
    base = base_url()
    page_url = base + page["slug"] + ".html"
    title = f"House Painters &amp; Renovation — {city}, AB | Chris Lloyd Ltd"
    desc = (f"Interior &amp; exterior house painting in {city}, Alberta, "
            f"plus drywall repair and small renovation work. "
            f"Based in nearby Edmonton — tidy prep, honest quotes.")
    canonical = f"<link rel=\"canonical\" href=\"{page_url}\" id=\"canonical-link\">"
    og_image = base + "assets/og-image.png"
    style_href = base + "assets/style.css"
    hero_kicker = f"Service area — {city}, Alberta"
    hero_h1 = f"House painting &amp; renovation in {city}"
    hero_blurb = (
        f"Interior and exterior painting, drywall repair and small "
        f"renovation work for {city} homes — based nearby in Edmonton "
        f"and working around the region.")
    city_attr = city.replace("&amp;", "&")
    draft_note = ""
    if is_draft:
        draft_note = ("        <aside class=\"section-note\" data-draft-note>"
                      "<strong>Draft copy</strong> — pending the owner's review; "
                      "wording and distances are approximate.</aside>\n")
    intro_html = "\n".join(f"      <p>{p}</p>" for p in page["intro"])
    drive = page["drivingContext"][0].upper() + page["drivingContext"][1:]
    services_html = "\n".join(
        f"      <div class=\"stack\">\n          <h3 class=\"col-title\">{t}</h3>\n"
        f"          {b.format(city=city)}\n        </div>"
        for t, b in SERVICES)
    jsonld = jsonld_for(page)
    nav_html = "".join(NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<!-- Static service-area page: generated by scripts/gen_area_pages.py from data/area-pages.json — edit the JSON, not this HTML. -->
{canonical}
<meta property="og:title" content="House Painters &amp; Renovation — {city}, AB | Chris Lloyd Ltd">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="House Painters &amp; Renovation — {city}, AB | Chris Lloyd Ltd">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og_image}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;1,500&family=Space+Grotesk:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{style_href}">
{FAVICON}
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<header class="hero">
  <div class="rosette rosette-hero" aria-hidden="true"></div>
  <div class="wrap">
    <p class="kicker" id="site-kicker">Chris Alun Lloyd Ltd</p>
    <h1 id="site-tagline">{hero_h1}</h1>
    <p class="blurb" id="site-blurb">{hero_blurb}</p>
    <p class="hero-links"><a class="btn" href="index.html#contact">Get a quote</a> <a class="btn btn-outline" href="index.html">Main site</a></p>
  </div>
</header>

<nav class="nav wrap">
  {nav_html}
</nav>

<main>
  <section id="about" class="wrap section">
    <h2>About the {city} service area</h2>
{draft_note}
    <div class="about-copy">
{intro_html}
      <p><strong>Where we're coming from:</strong> the shop is at 10412 66 Ave NW in west Edmonton; {city} is {page["drivingContext"]}.</p>
    </div>
  </section>

  <section id="services" class="wrap section section-alt">
    <h2>Painting &amp; renovation services in {city}</h2>
    <p class="section-note">The same interior, exterior and renovation work the main site describes, phrased for {city} homes.</p>
    <div class="services-cols">
{services_html}
    </div>
  </section>

  <section id="contact" class="wrap section">
    <h2>Get a quote for work in {city}</h2>
    <p class="section-note">Quotes and scheduling are handled centrally from the main site — the contact form below is one click away.</p>
    <div class="stack">
          <p>Ready to talk about your {city_attr} project? The full contact form — photos, budget, timing and the works — lives at <a href="index.html#contact">index.html#contact</a> on the main site, along with direct email and a phone/text number.</p>
          <p class="hero-links"><a class="btn" href="index.html#contact">Contact on the main site</a> <a class="btn btn-outline" href="index.html">Back to chrislloyd.io</a></p>
        </div>
  </section>
</main>

<footer class="wrap">
  <p>© <span id="year"></span> <span id="footer-name"></span> Chris Alun Lloyd Ltd. All rights reserved.</p>
  <p><a href="index.html">Edmonton painting &amp; renovation</a> · <a href="blog.html">Blog</a> · {city} service area</p>
</footer>

<script>
  document.getElementById("year").textContent = new Date().getFullYear();
  document.getElementById("footer-name").textContent = "Chris Alun Lloyd Ltd";
</script>
</body>
</html>
"""


def write(path, content):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def build_all():
    data = load_data()
    is_draft = bool(data.get("draft", False))
    out = []
    for page in data["pages"]:
        out.append((os.path.join(ROOT, page["slug"] + ".html"),
                    page, render(page, is_draft)))
    return out, is_draft


def main():
    argv = sys.argv[1:]
    check = "--check" in argv
    specs, is_draft = build_all()
    changed = []
    for path, page, content in specs:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                existing = f.read()
            if existing == content:
                continue
        changed.append((path, page["slug"]))
        if not check:
            write(path, content)
    if check:
        if changed:
            print("stale:", ", ".join(s for _, s in changed))
            return 1
        print("area pages up to date")
        return 0
    for path, slug in changed:
        print(f"wrote {os.path.basename(path)} (draft copy: {'on' if is_draft else 'off'})")
    if not changed:
        print("area pages already current — nothing rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())