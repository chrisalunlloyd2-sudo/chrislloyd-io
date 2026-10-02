#!/usr/bin/env python3
"""gen_pricesheet.py — one-page customer-facing price sheet PDF (Task 035).

Reads data/pricing.json (source of truth; must stay in sync with
scripts/quote_estimator.py DEFAULTS — test_site_scripts.py drift alarm) and
renders line items derived from the estimator's own math (interior/exterior,
prep, cut-in, the 1.2 exterior paint premium) rather than inventing numbers.

Output: dist/pricesheet.pdf (overwritten each run)
PLACEHOLDER RATES until Chris replaces pricing.json — footer says so.

Usage:
    python3 scripts/gen_pricesheet.py            # writes dist/pricesheet.pdf
    python3 scripts/gen_pricesheet.py --out X    # custom output path
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

# Display labels only — the VALUES come from data/pricing.json, never hardcoded
# here (single source of truth, mirroring quote_estimator.py DEFAULTS).
RATE_LABELS = [
    ("labour_rate", "Painting labour rate ($/hr)"),
    ("roller_sqft_hr", "Interior wall coverage (sq-ft/hour rolled)"),
    ("cutin_hr_per_room", "Cut-in time per room (hours)"),
    ("prep_hr_per_room", "Baseline prep per room (hours)"),
    ("repair_hr_per_pop", "Drywall repair per patch/pop (hours)"),
    ("height_9ft_factor", "9-ft ceiling slowdown factor"),
    ("exterior_sqft_hr", "Exterior siding coverage (sq-ft/hour)"),
    ("paint_cost_wall_gal", "Paint cost, interior wall ($/gallon)"),
    ("gal_coverage_sqft", "Paint coverage per gallon (sq-ft, per coat)"),
    ("coats_standard", "Standard coat count"),
]

TITLE = "Pricing Guide - Chris Lloyd Painting"
SUBTITLE = "Edmonton & surrounding area, residential repaint estimates"


def load_rates():
    path = os.path.join(ROOT, "data", "pricing.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["rates"], bool(data.get("_edit_me"))


def derived_numbers(r):
    """Reuse the estimator's own math for the worked-example line items."""
    import quote_estimator

    int_8ft = quote_estimator.interior(1, 12, 14, 8, rates=r)
    int_9ft = quote_estimator.interior(1, 12, 14, 9, rates=r)
    ext = quote_estimator.exterior(1000, rates=r)
    gal = ext["paint_gallons"]
    ext_paint_premium = round(gal * r["paint_cost_wall_gal"] * 0.2, 2)
    return {
        "int_8ft": int_8ft,
        "int_9ft": int_9ft,
        "ext_1000": ext,
        "ext_paint_premium": ext_paint_premium,
    }


def build_pdf(rates, out_path):
    from datetime import datetime, timezone

    from fpdf import FPDF

    pdf = FPDF(unit="mm", format="letter")
    # Fixed creation date keeps regenerate runs byte-identical (no git churn).
    pdf.set_creation_date(datetime(2026, 1, 1, tzinfo=timezone.utc))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(TITLE)
    pdf.set_author("Chris Lloyd Painting")
    pdf.set_creator("gen_pricesheet.py (fpdf2)")
    pdf.set_subject("Residential repaint price sheet")
    pdf.add_page()

    # Header band
    pdf.set_fill_color(30, 58, 95)          # deep blue
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 216, 30, style="F")
    pdf.set_y(8)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, TITLE, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, SUBTITLE, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_y(35)

    pdf.set_text_color(33, 33, 33)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Rate Table", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9.5)
    for key, label in RATE_LABELS:
        v = rates.get(key, "n/a")
        shown = f"${v:.2f}/hr" if key == "labour_rate" else (
            f"{v:.1f}x" if key == "height_9ft_factor" else f"{v:g}")
        pdf.cell(120, 6, label)
        pdf.cell(0, 6, shown, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Worked Examples (1 room, 12x14 ft, 2 coats)",
             new_x="LMARGIN", new_y="NEXT")
    d = derived_numbers(rates)

    def example_row(name, e):
        lo, hi = e["total_range"]
        pdf.cell(120, 6, name)
        pdf.cell(0, 6,
                 f"{e['labour_hours']:.1f} h labour + "
                 f"${e['paint_cost']:.2f} paint = ${lo:,}-${hi:,}",
                 align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9.5)
    example_row("Interior, 8-ft ceilings", d["int_8ft"])
    example_row("Interior, 9-ft ceilings (slowdown applies)", d["int_9ft"])
    example_row("Exterior, 1000 sq-ft siding", d["ext_1000"])

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0, 5,
        "Notes: quotes also include tape/masking and site cleanup; exterior work "
        "is weather-window dependent and excludes scaffolding. Paint pricing "
        "assumes ${:.0f}/gallon at {:g} sq-ft per coat; exterior paint carries a "
        "1.2x premium (${:.2f} over interior at 1000 sq-ft). Final numbers depend "
        "on room count, size, height, and repairs - see the site estimator.".format(
            rates["paint_cost_wall_gal"], rates["gal_coverage_sqft"],
            d["ext_paint_premium"]))

    # Footer / placeholder disclaimer
    pdf.set_y(-28)
    pdf.set_draw_color(30, 58, 95)
    pdf.line(15, pdf.get_y(), 201, pdf.get_y())
    pdf.set_y(pdf.get_y() + 2)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 30, 30)
    pdf.multi_cell(
        0, 4.5,
        "PLACEHOLDER RATES - EDIT-ME / OWNER-ACTION: rates are seeded from "
        "scripts/quote_estimator.py DEFAULTS and must be replaced with real "
        "production rates before customer use. Rates subject to confirmation.")
    pdf.set_text_color(90, 90, 90)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.cell(0, 4,
             f"Generated deterministically from data/pricing.json",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.output(out_path)


def main():
    ap = argparse.ArgumentParser(description="Generate customer-facing price-sheet PDF")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "pricesheet.pdf"))
    args = ap.parse_args()

    rates, placeholder = load_rates()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    build_pdf(rates, args.out)
    pdf_size = os.path.getsize(args.out)
    print(f"Wrote {args.out} ({pdf_size} bytes, placeholder={placeholder})")
    return 0


if __name__ == "__main__":
    sys.exit(main())