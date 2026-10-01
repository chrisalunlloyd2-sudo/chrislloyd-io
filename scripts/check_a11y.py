#!/usr/bin/env python3
"""Lighthouse-style static a11y/quality audit for chrislloyd-io.

Deterministic mirror of the Lighthouse accessibility + best-practices rules
that can be evaluated without a browser: color contrast (WCAG 4.5:1 normal /
3:1 large text), alt-text coverage, label association, landmarks, headings,
lang/viewport meta, form a11y. No browser, no network.

Exit code 0 = no actionable issues, 1 = findings (printed to stdout).
"""
import html.parser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# WCAG relative luminance + contrast
# ---------------------------------------------------------------------------

def _srgb_to_lin(c):
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(hex_color):
    m = re.match(r"^#([0-9a-fA-F]{6})$", hex_color.strip())
    if not m:
        return None
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = _srgb_to_lin(r), _srgb_to_lin(g), _srgb_to_lin(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(fg, bg):
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    if l1 is None or l2 is None:
        return None
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def blend(fg_hex, bg_hex, alpha):
    """Alpha-composite fg over bg, return hex."""
    fr, fg_c, fb = (int(fg_hex[1:3], 16), int(fg_hex[3:5], 16), int(fg_hex[5:7], 16))
    br, bg_c, bb = (int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16))
    mix = lambda f, b: round(f * alpha + b * (1 - alpha))
    return "#%02x%02x%02x" % (mix(fr, br), mix(fg_c, bg_c), mix(fb, bb))

# ---------------------------------------------------------------------------
# CSS tokens
# ---------------------------------------------------------------------------

def load_tokens():
    css = open(os.path.join(ROOT, "assets", "style.css"), encoding="utf-8").read()
    tokens = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css))
    return css, tokens

def resolve(value, tokens, depth=0):
    """Resolve a CSS color value ('var(--x)' or hex) to hex."""
    if depth > 8:
        return None
    v = value.strip()
    m = re.match(r"^var\((--[\w-]+)\)$", v)
    if m:
        return resolve(tokens.get(m.group(1), ""), tokens, depth + 1)
    if re.match(r"^#[0-9a-fA-F]{6}$", v):
        return v.lower()
    return None

# ---------------------------------------------------------------------------
# Color-contrast checks
# ---------------------------------------------------------------------------

NORMAL_MIN = 4.5
LARGE_MIN = 3.0

def check_contrast():
    css, tokens = load_tokens()
    ink = resolve("var(--ink)", tokens)
    ink_alt = resolve("var(--ink-alt)", tokens)
    ivory = resolve("var(--ivory)", tokens)
    muted = resolve("var(--ivory-muted)", tokens)
    terra = resolve("var(--terracotta)", tokens)
    teal = resolve("var(--teal)", tokens)
    white = "#ffffff"

    # (label, fg, bg, large_text?) — large = >=24px, or >=18.66px bold.
    pairs = [
        ("body --ivory on --ink", ivory, ink, False),
        ("body text --ivory on --ink-alt", ivory, ink_alt, False),
        ("secondary --ivory-muted on --ink", muted, ink, False),
        ("secondary --ivory-muted on --ink-alt", muted, ink_alt, False),
        ("links a{--teal} on --ink", teal, ink, False),
        ("links a{--teal} on --ink-alt", teal, ink_alt, False),
        (".kicker --terracotta on --ink", terra, ink, False),
        (".col-title --terracotta on --ink-alt (1.05rem w600)", terra, ink_alt, False),
        (".col-title --teal on --ink-alt (labour col)", teal, ink_alt, False),
        (".rating --terracotta on --ink (reviews/contact cards)", terra, ink, False),
        (".rating --terracotta on --ink-alt (other cards)", terra, ink_alt, False),
        (".btn --ink on --ivory", ink, ivory, False),
        (".btn:hover --ink on #fff", ink, white, False),
        (".btn-outline --ivory on --ink", ivory, ink, False),
        # .gallery-chip: was --ivory-on-accent pre-031 (3.1:1); now ink-on-accent, see fix entries below.
        (".nav a --ivory-muted on --ink", muted, ink, False),
        (".hero h1 em --teal on --ink (large)", teal, ink, True),
        (".blog-date --terracotta on --ink-alt (cards)", terra, ink_alt, False),
        ("footer --ivory-muted on --ink", muted, ink, False),
        (".form-status --teal on --ink (contact card)", teal, ink, False),
        (".web3-badge --teal on --ink", teal, ink, False),
        (".contact-form input --ivory on --ink-alt", ivory, ink_alt, False),
        (".gallery-chip --ink on --terracotta (task 031 fix)", ink, terra, False),
        (".gallery-chip-after --ink on --teal (task 031 fix)", ink, teal, False),
        (".contact-form input::placeholder --ivory-muted on --ink-alt (task 031 fix)", muted, ink_alt, False),
        (".field-optional --ivory-muted on --ink (task 031 fix: no opacity)", muted, ink, False),
    ]
    findings = []
    for label, fg, bg, large in pairs:
        r = contrast_ratio(fg, bg)
        if r is None:
            findings.append(("error", "contrast: unresolvable pair — " + label))
            continue
        need = LARGE_MIN if large else NORMAL_MIN
        if r < need:
            findings.append(("fail", "contrast %.2f:1 < %.1f:1 — %s" % (r, need, label)))
        else:
            findings.append(("pass", "contrast %.2f:1 — %s" % (r, label)))

    # task 031: .field-optional opacity .7 was removed (solid --ivory-muted now,
    # checked above). Keep the pre-fix blended ratio as an informational line.
    eff = blend(muted, ink_alt, 0.7)
    r = contrast_ratio(eff, ink_alt)
    findings.append(("pass", "contrast %.2f:1 — (pre-fix reference) .field-optional @ opacity .7 on --ink-alt" % (r,)))

    return findings

# ---------------------------------------------------------------------------
# HTML structural checks
# ---------------------------------------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}

class Auditor(html.parser.HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.imgs = []        # (line, attrs)
        self.form_ctrls = []  # (line, tag, id, inside_label_flag)
        self.labels_for = []  # line, for-value, wrapped-control-seen
        self.landmarks = {"header": 0, "nav": 0, "main": 0, "footer": 0}
        self.h1 = 0
        self.headings = []    # (tag, line)
        self.lang = None
        self.has_viewport = False
        self.html_attrs = {}
        self._label_depth = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        line = self.getpos()[0]
        if tag == "img":
            self.imgs.append((line, d))
        elif tag == "label":
            self._label_depth += 1
            self.labels_for.append({"line": line, "for": d.get("for"), "wrap": False})
        elif self._label_depth > 0 and tag in ("input", "select", "textarea"):
            if d.get("type") == "hidden":
                return
            self.labels_for[-1]["wrap"] = True
        elif tag in ("input", "select", "textarea") and d.get("type") != "hidden":
            self.form_ctrls.append((line, tag, d.get("id"), False))
        elif tag in self.landmarks:
            self.landmarks[tag] += 1
        elif tag == "html":
            self.lang = d.get("lang")
            self.html_attrs = d
        elif tag == "meta" and d.get("name") == "viewport":
            self.has_viewport = True
        elif tag == "h1":
            self.h1 += 1
        elif tag in ("h2", "h3", "h4", "h5", "h6"):
            self.headings.append((tag, line))

    def handle_endtag(self, tag):
        if tag == "label" and self._label_depth > 0:
            self._label_depth -= 1

    def label_lines(self):
        return {l["line"] for l in self.labels_for}

def check_html_file(path):
    findings = []
    rel = os.path.relpath(path, ROOT)
    try:
        raw = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return [("error", rel + ": file not found")]

    # meta viewport may be self-closing; HTMLParser handles it either way.
    a = Auditor(path)
    for chunk in raw.splitlines(keepends=True):
        a.feed(chunk)
        a.close()

    if a.lang is None:
        findings.append(("fail", rel + ":1 <html> missing lang attribute"))
    if not a.has_viewport:
        findings.append(("fail", rel + ": <meta name=viewport> missing"))

    for line, d in a.imgs:
        if "alt" not in d:
            findings.append(("fail", "%s:%d <img> missing alt attribute" % (rel, line)))
        elif d["alt"].strip() == "" and "aria-hidden" not in d and "presentation" not in (d.get("role") or ""):
            # empty alt on a content image is suspicious; decorative is OK with aria-hidden/role
            findings.append(("warn", "%s:%d <img alt=\"\"> empty alt, not marked decorative" % (rel, line)))

    labelled_lines = a.label_lines()
    for line, tag, cid, _ in a.form_ctrls:
        if cid is None:
            # unlabelled unless wrapped in a <label> that opened before it
            if not any(l["for"] is None for l in a.labels_for):
                findings.append(("fail", "%s:%d <%s> has no id and no label association" % (rel, line, tag)))
            else:
                # unlabelled-by-for: acceptable only if wrapped inside a <label>
                wrapped = any(
                    l["for"] is None and l["line"] < line
                    for l in a.labels_for
                    if l["line"] < line
                )
                if not wrapped:
                    findings.append(("fail", "%s:%d <%s id=%r> not associated with any <label>" % (rel, line, tag, cid)))

    if a.h1 == 0:
        findings.append(("warn", rel + ": no <h1> on page"))
    elif a.h1 > 1:
        findings.append(("warn", rel + ": %d <h1> elements" % a.h1))

    for lm, n in sorted(a.landmarks.items()):
        if n > 1:
            findings.append(("fail", rel + ": %d <%s> landmarks" % (n, lm)))

    # heading order: no skipping levels downwards
    prev = 1
    for tag, line in a.headings:
        lvl = int(tag[1])
        if lvl > prev + 1:
            findings.append(("warn", "%s:%d heading skips levels (%s after h%d)" % (rel, line, tag, prev)))
        prev = lvl

    return findings

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    findings = check_contrast()
    for name in ("index.html", "blog.html", "leduc.html", "sherwood-park.html",
                 "spruce-grove.html", "st-albert.html"):
        findings.extend(check_html_file(os.path.join(ROOT, name)))

    fails = [f for f in findings if f[0] == "fail"]
    warns = [f for f in findings if f[0] == "warn"]
    errors = [f for f in findings if f[0] == "error"]
    passes = [f for f in findings if f[0] == "pass"]

    print("== contrast (informational passes) ==")
    for _, msg in passes:
        print("  ok", msg)
    if errors:
        print("\n== errors ==")
        for _, msg in errors:
            print("  !", msg)
    if warns:
        print("\n== warnings ==")
        for _, msg in warns:
            print("  ~", msg)
    print("\n== failures ==")
    if fails:
        for _, msg in fails:
            print("  FAIL", msg)
    else:
        print("  (none)")

    print("\nscore-ish summary: %d pass, %d warn, %d fail, %d error" % (
        len(passes), len(warns), len(fails), len(errors)))
    return 1 if (fails or errors) else 0

if __name__ == "__main__":
    sys.exit(main())