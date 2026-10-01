#!/usr/bin/env python3
"""quote_estimator.py — internal quote sanity-checker for Chris (NOT customer-facing).

Estimates labour hours + paint for residential repaint work using a rate
table YOU edit. Deterministic math, no LLM. Run it before quoting to see if
your gut number is in the same ballpark as the table.

!!! The default rates below are PLACEHOLDERS marked EDIT-ME — replace with
your real production rates (or edit data/pricing.json when it exists). Never
publish this output to customers; it is a self-check tool only.

Usage:
    python3 scripts/quote_estimator.py --rooms 3 --size 12x14 --height 9
    python3 scripts/quote_estimator.py --exterior-sqft 1800 --siding hardie
"""
import argparse
import json
import os

# EDIT-ME: placeholder hourly + consumables. Replace with real rates.
DEFAULTS = {
    "labour_rate": 55.0,          # $/hr, EDIT-ME
    "coats_standard": 2,
    "roller_sqft_hr": 150.0,      # wall sqft rolled per hour, standard 8ft, EDIT-ME
    "cutin_hr_per_room": 1.5,     # hrs cut-in per room, EDIT-ME
    "prep_hr_per_room": 2.5,      # baseline prep per room (patch/sand/wash/tape), EDIT-ME
    "repair_hr_per_pop": 0.25,    # hrs per drywall repair beyond baseline, EDIT-ME
    "height_9ft_factor": 1.3,     # 9ft ceilings slowdown, EDIT-ME
    "exterior_sqft_hr": 100.0,    # exterior siding sqft per hour, EDIT-ME
    "paint_cost_wall_gal": 75.0,  # EDIT-ME
    "gal_coverage_sqft": 350.0,   # per coat
}

def interior(room_count, size_w, size_l, height=8, repairs=0, coats=2, rates=None):
    r = dict(DEFAULTS, **(rates or {}))
    wall_sqft = room_count * 2 * (size_w + size_l) * height
    area_hr = wall_sqft / r["roller_sqft_hr"]
    cutin_hr = room_count * r["cutin_hr_per_room"]
    prep_hr = room_count * r["prep_hr_per_room"] + repairs * r["repair_hr_per_pop"]
    factor = r["height_9ft_factor"] if height >= 9 else 1.0
    labour_hr = (area_hr + cutin_hr + prep_hr) * factor
    gal = wall_sqft * coats / r["gal_coverage_sqft"]
    paint_cost = gal * r["paint_cost_wall_gal"]
    labour_cost = labour_hr * r["labour_rate"]
    return {
        "wall_sqft": round(wall_sqft, 1),
        "labour_hours": round(labour_hr, 1),
        "labour_cost": round(labour_cost, 2),
        "paint_gallons": round(gal, 1),
        "paint_cost": round(paint_cost, 2),
        "total_range": (round((labour_cost + paint_cost) * 0.9), round((labour_cost + paint_cost) * 1.15)),
        "rates": "PLACEHOLDER EDIT-ME" if not rates else "custom",
    }

def exterior(sqft, coats=2, rates=None):
    r = dict(DEFAULTS, **(rates or {}))
    labour_hr = sqft / r["exterior_sqft_hr"] * coats
    gal = sqft * coats / r["gal_coverage_sqft"]
    paint_cost = gal * r["paint_cost_wall_gal"] * 1.2  # exterior typically pricier
    labour_cost = labour_hr * r["labour_rate"]
    return {
        "siding_sqft": sqft,
        "labour_hours": round(labour_hr, 1),
        "labour_cost": round(labour_cost, 2),
        "paint_gallons": round(gal, 1),
        "paint_cost": round(paint_cost, 2),
        "total_range": (round((labour_cost + paint_cost) * 0.9), round((labour_cost + paint_cost) * 1.15)),
        "note": "weather-window dependent; excludes scaffolding/height premiums",
        "rates": "PLACEHOLDER EDIT-ME" if not rates else "custom",
    }

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rooms", type=int, help="number of interior rooms")
    ap.add_argument("--size", type=str, help="room size WxL ft (e.g. 12x14); same for all rooms")
    ap.add_argument("--height", type=int, default=8, choices=[8, 9], help="ceiling height")
    ap.add_argument("--repairs", type=int, default=0, help="extra drywall repairs/patches")
    ap.add_argument("--coats", type=int, default=2)
    ap.add_argument("--exterior-sqft", type=int, help="exterior siding area to paint")
    args = ap.parse_args()

    out = {}
    if args.rooms and args.size:
        w, _, l = args.size.partition("x")
        out["interior"] = interior(args.rooms, float(w), float(l), args.height, args.repairs, args.coats)
    if args.exterior_sqft:
        out["exterior"] = exterior(args.exterior_sqft, args.coats)
    if not out:
        ap.print_help()
        return 1
    print(json.dumps(out, indent=1))
    print("\nINTERNAL ONLY — placeholder rates, sanity-check against your real numbers.")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())