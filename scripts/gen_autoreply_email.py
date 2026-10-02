#!/usr/bin/env python3
"""gen_autoreply_email.py — lead-magnet auto-reply text generator (Task 036).

Renders the get-ready checklist from data/lead_magnet.json as plain text,
suitable for a submitter auto-reply email (Formspree autoresponse body paste)
or any channel. The site's post-submit get-ready block and this file share the
same source of truth: edit data/lead_magnet.json once, both update.

Honesty constraint (tasks 015/030): no response-time promises, no invented
guarantees. If you have not verified an item, wrap it in <PLACEHOLDER> tags in
the JSON and the generator renders it with a "(confirm before sending)">
notice instead — and the site shows the same notice.

Usage:
    python3 scripts/gen_autoreply_email.py            # stdout
    python3 scripts/gen_autoreply_email.py --out FILE # write FILE
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUBJECT = "Thanks for requesting a quote - here's a quick get-ready checklist"
DISCLAIMER = "Sent in response to your quote request to Chris Lloyd Painting."


def load_magnet():
    """Read data/lead_magnet.json, return (items, closing, placeholder_flag)."""
    with open(os.path.join(ROOT, "data", "lead_magnet.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("checklist", [])
    if not items:
        raise ValueError("lead_magnet.checklist is empty")
    closing = data.get("closing_note", "")
    return items, closing, bool(data.get("_edit_me"))


def render_text(items, closing, placeholder=False):
    """Deterministic plain-text body. Same input -> same bytes."""
    lines = []
    for i, item in enumerate(items, 1):
        marker = "*" if item.get("placeholder") else str(i)
        title = item.get("title", "").strip()
        detail = item.get("detail", "").strip()
        if placeholder and item.get("placeholder"):
            title = f"{title} (confirm before sending)"
        lines.append(f"{marker}. {title}")
        if detail:
            lines.append(f"   {detail}")
        lines.append("")
    if closing:
        lines.append(closing)
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines).replace("\n\n\n", "\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write to file instead of stdout")
    args = ap.parse_args()
    items, closing, is_placeholder = load_magnet()
    body = render_text(items, closing, placeholder=is_placeholder)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(body)
    else:
        print(body)


if __name__ == "__main__":
    main()