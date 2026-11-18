#!/usr/bin/env python3
"""img_budget.py — image dimensions from raw file headers, no Pillow, no browser
(PLAN-SITE-100 phase 1 step 6). Alt-text coverage is already checked by check_a11y.py;
this script is scoped to size/dimension only, so the two don't duplicate each other.

Reads PNG/JPEG headers directly to get pixel width/height, cross-checks against the
<img width=".." height="..."> attributes actually declared in the HTML, and flags:
  oversized   - native resolution is more than OVERSIZE_FACTOR x the declared display
                size in either dimension (shipping pixels nobody can see - real waste).
  heavy       - file bytes exceed BYTE_BUDGET regardless of dimensions.
A declared size up to 2x native (common for retina/high-DPI displays) is NOT flagged.
Oversized compares the SHORTER native dimension against the shorter declared one, not
width vs width/height vs height directly - CSS object-fit:cover (used throughout this
site's product/gallery cards) intentionally crops a taller-than-square source image into
a square box, so a portrait photo having more pixels on its long axis isn't waste; the
full file has to be downloaded either way, and the short axis is what sets the real
minimum resolution needed.

Run: python3 scripts/img_budget.py   (exit 0 = clean, 1 = findings printed to stdout)
"""
import html.parser
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OVERSIZE_FACTOR = 2.0   # native dimension allowed up to 2x declared (retina headroom)
BYTE_BUDGET = 150_000   # bytes, per image


def png_dims(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def jpeg_dims(data):
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 4 <= n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 4 > n:
            break
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):  # SOF markers
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + seg_len
    return None


def is_oversized(native_w, native_h, declared_w, declared_h):
    return min(native_w, native_h) > min(declared_w, declared_h) * OVERSIZE_FACTOR


def image_dims(path):
    with open(path, "rb") as fh:
        data = fh.read(65536)  # headers live well within the first 64KB
    if path.endswith(".png"):
        return png_dims(data)
    if path.endswith((".jpg", ".jpeg")):
        return jpeg_dims(data)
    return None  # webp/svg/gif: not handled yet, skipped rather than guessed


class ImgParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.imgs = []  # (src, declared_w, declared_h)

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        d = dict(attrs)
        src = d.get("src", "")
        if not src.startswith("assets/"):
            return
        try:
            w = int(d["width"]) if d.get("width", "").isdigit() else None
            h = int(d["height"]) if d.get("height", "").isdigit() else None
        except (KeyError, ValueError):
            w = h = None
        self.imgs.append((src, w, h))


def audit():
    findings = []
    checked = set()
    for page in sorted(f for f in os.listdir(ROOT) if f.endswith(".html")):
        with open(os.path.join(ROOT, page), encoding="utf-8") as fh:
            text = fh.read()
        p = ImgParser()
        p.feed(text)
        for src, dw, dh in p.imgs:
            key = (page, src)
            if key in checked:
                continue
            checked.add(key)
            path = os.path.join(ROOT, src)
            if not os.path.isfile(path):
                findings.append((page, src, "missing file"))
                continue
            size = os.path.getsize(path)
            if size > BYTE_BUDGET:
                findings.append((page, src, f"heavy: {size:,} bytes > {BYTE_BUDGET:,}"))
            dims = image_dims(path)
            if dims and dw and dh:
                nw, nh = dims
                if is_oversized(nw, nh, dw, dh):
                    findings.append((page, src,
                                      f"oversized: native {nw}x{nh} vs declared {dw}x{dh}"))
    return findings


def main():
    findings = audit()
    if not findings:
        print("img_budget: clean — every local <img> is within size/dimension budget")
        return 0
    for page, src, reason in findings:
        print(f"{page}: {src} — {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
