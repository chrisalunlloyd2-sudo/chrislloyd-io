#!/usr/bin/env python3
"""gen_estimator_fixtures.py — deterministic parity fixtures for the estimator widget.

Runs scripts/quote_estimator.py (the single source of truth) on the widget's
default inputs and prints the numbers as JSON. Output feeds
scripts/test_estimator_logic.js (JS-vs-CLI parity cases) — the test file reads
this script's output at test time so the fixtures NEVER go stale.

Usage: python3 scripts/gen_estimator_fixtures.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "quote_estimator", os.path.join(HERE, "quote_estimator.py"))
qe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qe)

CASES = {
    # widget default interior inputs (mirrors JS defaults)
    "interior_default": {"rooms": 3, "w": 12, "l": 14, "height": 8, "repairs": 0},
    # mode-switch / factor cases
    "interior_9ft": {"rooms": 2, "w": 12, "l": 14, "height": 9, "repairs": 3},
    "interior_small": {"rooms": 1, "w": 10, "l": 10, "height": 8, "repairs": 0},
    "interior_repairs": {"rooms": 3, "w": 12, "l": 14, "height": 8, "repairs": 5},
    # exterior default + scaling
    "exterior_default": {"sqft": 1500},
    "exterior_2x": {"sqft": 3000},
}

out = {}
for name, c in CASES.items():
    if "sqft" in c:
        out[name] = qe.exterior(c["sqft"])
    else:
        out[name] = qe.interior(c["rooms"], c["w"], c["l"], c["height"], c["repairs"])

print(json.dumps(out, indent=1))