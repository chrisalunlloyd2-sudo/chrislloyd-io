#!/usr/bin/env python3
"""check_testimonials.py — deterministic task-025 smoke test (no LLM reasoning).

Verifies the data-driven contract end to end WITHOUT a browser:
 1. data/testimonials.json parses, follows the documented schema.
 2. All seeded entries are placeholders (JSON-LD Review policy: emit nothing).
 3. index.html contains the #testimonials section shell + nav anchor.
 4. assets/main.js wires renderTestimonials to the #testimonials-grid id.

Run: python3 scripts/check_testimonials.py   (exit 0 = pass)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + ((" — " + detail) if detail else ""))
    if not cond:
        failures.append(label)


data_path = os.path.join(ROOT, "data", "testimonials.json")
items = json.load(open(data_path, encoding="utf-8"))
check("testimonials.json parses to a list", isinstance(items, list))
check("2-3 placeholder entries", 2 <= len(items) <= 3, str(len(items)))
for t in items:
    check("[" + str(t.get("id")) + "] has id/author/quote",
          all(k in t for k in ("id", "author", "quote")))
    check("[" + str(t.get("id")) + "] marked placeholder", t.get("placeholder") is True)
    check("[" + str(t.get("id")) + "] quote flagged PLACEHOLDER", "PLACEHOLDER" in t.get("quote", ""))
    if t.get("rating") is not None:
        check("[" + str(t.get("id")) + "] rating in 1..5", 1 <= t["rating"] <= 5)

html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
check("index.html has #testimonials section", 'id="testimonials"' in html)
check("index.html has testimonials-grid mount", 'id="testimonials-grid"' in html)
check("nav links to #testimonials", 'href="#testimonials"' in html)
# placeholder-styled markup parity: main.js must not emit JSON-LD script inline with ratings
check("no inline review JSON-LD in static html", "testimonials-jsonld" not in html)

mainjs = open(os.path.join(ROOT, "assets", "main.js"), encoding="utf-8").read()
check("main.js mounts testimonials-grid", '"testimonials-grid"' in mainjs)
check("main.js defines renderTestimonials", "function renderTestimonials" in mainjs)
check("main.js JSON-LD filters placeholders", "placeholder !== true" in mainjs)

css = open(os.path.join(ROOT, "assets", "style.css"), encoding="utf-8").read()
check("style.css styles .testimonial", ".testimonial" in css)

sys.exit(1 if failures else 0)