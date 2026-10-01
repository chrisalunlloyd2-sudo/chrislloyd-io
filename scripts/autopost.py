#!/usr/bin/env python3
"""autopost.py — draft 3 real blog posts from the trade-knowledge base.

Drafts (not auto-published) are written to blog-drafts/ as markdown files
with a JSON header — the owner reviews them, edits as he likes, then a
follow-up scripts/import_draft.py (or manual add_post.py calls) promotes
them. Doctrine: ADD-only, no auto-promotion without owner proof-review.

Usage:
    python3 scripts/autopost.py            # writes drafts, reports paths
    python3 scripts/autopost.py --list     # just show draft filenames
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFT_DIR = os.path.join(ROOT, "blog-drafts")

DRAFTS = [
    {
        "id": "wall-prep-checklist",
        "filename": "how-to-prep-walls-before-painting-edmonton.md",
        "title": "How to prep walls before painting (Edmonton checklist)",
        "seo_title": "How to Prep Walls Before Painting — Edmonton Painter's Checklist",
        "excerpt": ("The ninety-percent rule: prep is most of the job. A room-by-room "
                    "checklist I actually use on Edmonton repaints — patch, sand, wash, "
                    "tape, prime — and why skipping steps shows up a month later."),
        "tags": ["prep", "interior", "checklist", "edmonton"],
        "body": [
            ("Most of a repaint is not painting. On an average bedroom repaint I spend "
             "more time prepping than rolling — and it is the difference between a "
             "finish that looks good for a decade and one that telegraphs every patch "
             "by month three."),
            ("Step 1 — Patch and fill. Run a putty knife over every wall slowly with "
             "the light raking across the surface. Fill dents, nail pops and screw "
             "dimples with a lightweight filler. Second coat on anything that shrank."),
            ("Step 2 — Sand. Sand every patch flush with 120 then 150 grit, feathered "
             "at least a hand-width past the edge of the repair. Dust after with a "
             "slightly damp cloth, not a shop towel that leaves lint."),
            ("Step 3 — Wash. Kitchen and hallway walls collect an invisible film that "
             "paint will not stick to. A quick wash with TSP substitute, rinse, and "
             "full dry before any primer."),
            ("Step 4 — Tape and cut-in strategy. Tape only where lines are hard "
             "(baseboards, casings, ceiling if you are not confident on the cut-in). "
             "Pressed-on tape is what stops bleed; a lazy stick is worse than no tape."),
            ("Step 5 — Prime the patches. Spot-primer on every filled area, or the "
             "patch drinks the topcoat at a different rate and flashes as a dull "
             "ghost. High-hide primer on any smoke or water stains."),
            ("Edmonton note: dry winter air makes patches cure fast but shrink more — "
             "plan for a second fill pass in heating season. Humidity from a "
             "shower-run helps larger drywall repairs set without cracking."),
        ],
    },
    {
        "id": "interior-vs-exterior-alberta-winters",
        "filename": "interior-vs-exterior-painting-alberta-winters.md",
        "title": "Interior vs exterior painting through Alberta winters",
        "seo_title": "Interior vs Exterior Painting in Alberta Winters — What Works, What Waits",
        "excerpt": ("Edmonton's shoulder seasons are short. What can realistically be "
                    "painted outside in October, what should wait for spring, and why "
                    "winter is actually the best time for interior work."),
        "tags": ["exterior", "seasonal", "alberta", "planning"],
        "body": [
            ("Exterior paint needs both surface and air temperatures inside the "
             "manufacturer's window, and in Edmonton that window shuts hard in "
             "October. The paint can surviving 5°C does not mean the surface does — "
             "north-facing siding can be a frost degree colder than the air."),
            ("What exterior work still counts in late season: doors and storm doors "
             "(taken off and painted warm indoors), fascia on the sunny side during a "
             "dry afternoon stretch, and any masonry priming under a heat tent for a "
             "day-plus window. Everything else waits."),
            ("Interior winter work is the opposite story. Heating season means low "
             "humidity and fast, even curing — which is good for paint films but hard "
             "on patches, so plan two fill passes. And nobody wants windows open in "
             "January: pick low- or zero-VOC lines and run HRV/fan on continuous."),
            ("Booking note: winter interior projects book out faster than summer "
             "ones — January and February repainting is when most people get quotes "
             "but the good slots go early. If you are planning a spring exterior "
             "repaint, the quote list opens around now too."),
        ],
    },
    {
        "id": "cost-to-paint-house-edmonton",
        "filename": "how-much-does-it-cost-to-paint-a-house-edmonton.md",
        "title": "How much does it cost to paint a house in Edmonton?",
        "seo_title": "How Much Does It Cost to Paint a House in Edmonton? (2026 pricing factors)",
        "excerpt": ("What actually drives a painting quote in Edmonton: square footage "
                    "is the start, but ceiling height, colour changes, trim count and "
                    "repair volume move the number more than most people expect."),
        "tags": ["pricing", "quotes", "edmonton", "faq"],
        "body": [
            ("The question everyone asks first, and the honest answer is: it depends "
             "on about six variables that are easy to check but hard to guess. "
             "Square footage of wall area is the start — but here is what moves a "
             "quote up or down from there."),
            ("Ceiling height. A 9-foot ceiling is roughly 28% more wall area than an "
             "8-foot one, and it moves the job from roller-on-a-stick to ladder and "
             "scaffold territory. Vaulted ceilings move it again."),
            ("Colour change depth. Same-hue repaint is two coats. Navy to white is "
             "a primer-tinted base plus three — that is not upselling, it is how "
             "opacity physics works. Dark-to-light change is the single biggest "
             "coat-count driver."),
            ("Trim, doors and cut-ups. Baseboards, casings, wainscot and windows "
             "are all brushed work at a fraction of roller speed. A room with six "
             "windows can take longer in cut-in than the walls take rolling."),
            ("Repair volume. Drywall patches, joint-tape cracks, nail pops — every "
             "repair gets a fill, sand, prime cycle. An older home with ten nail "
             "pops per room is quoting differently than a 2015 build."),
            ("What is usually NOT extra: prep basics (dust-down, floor protection, "
             "outlet plate removal) are part of doing the job right, not line items. "
             "A quote that charges separately for masking is a quote to question."),
            ("For a realistic ballpark on an Edmonton home: interiors typically land "
             "per-room or per-project and exteriors can swing widely with siding "
             "type and height — get two or three quotes, ask what each includes, "
             "and treat a suspiciously low bid as a question, not a bargain."),
        ],
    },
]


def write_drafts():
    os.makedirs(DRAFT_DIR, exist_ok=True)
    written = []
    for d in DRAFTS:
        path = os.path.join(DRAFT_DIR, d["filename"])
        header = {
            "title": d["title"],
            "date": None,  # set on import/promotion
            "excerpt": d["excerpt"],
            "tags": d["tags"],
            "seo_title": d["seo_title"],
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(header, indent=2) + "\n\n---\n\n")
            for para in d["body"]:
                f.write(para + "\n\n")
        written.append(path)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="list draft paths only")
    args = ap.parse_args()
    if args.list:
        for d in DRAFTS:
            print(os.path.join(DRAFT_DIR, d["filename"]))
        return
    for p in write_drafts():
        print("draft:", p)
    print("review, edit dates, then promote via add_post.py (owner-proof doctrine)")


if __name__ == "__main__":
    main()