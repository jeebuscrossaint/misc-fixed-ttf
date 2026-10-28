#!/usr/bin/env python3
"""Render every glyph with FreeType at its native pixel size and check the
result matches the source BDF bitmap pixel for pixel, under each hinting mode
a terminal is likely to request."""

import sys

import freetype

from build import ROOT, STYLES, lit_pixels, parse_bdf

MODES = {
    "full": freetype.FT_LOAD_DEFAULT,
    "light": freetype.FT_LOAD_TARGET_LIGHT,
    "autohint": freetype.FT_LOAD_TARGET_LIGHT | freetype.FT_LOAD_FORCE_AUTOHINT,
    "none": freetype.FT_LOAD_NO_HINTING,
}


def rendered(face, code, flags):
    face.load_char(code, flags)
    face.glyph.render(freetype.FT_RENDER_MODE_MONO)
    bitmap, left, top = face.glyph.bitmap, face.glyph.bitmap_left, face.glyph.bitmap_top
    return {
        (left + x, top - 1 - r)
        for r in range(bitmap.rows)
        for x in range(bitmap.width)
        if bitmap.buffer[r * bitmap.pitch + x // 8] >> (7 - x % 8) & 1
    }


def check(bdf):
    suffix = bdf.stem[-1] if bdf.stem[-1] in "BO" else ""
    ttf = ROOT / "ttf" / f"Fixed{bdf.stem[: len(bdf.stem) - len(suffix)]}-{STYLES[suffix]}.ttf"
    props, glyphs = parse_bdf(bdf)
    face = freetype.Face(str(ttf))
    face.set_pixel_sizes(0, int(props["PIXEL_SIZE"]))
    glyphs = [g for g in glyphs if g.get("code", -1) >= 0]
    bad = {mode: 0 for mode in MODES}
    for g in glyphs:
        want = set(lit_pixels(g))
        for mode, flags in MODES.items():
            bad[mode] += rendered(face, g["code"], flags) != want
    return len(glyphs), bad


def main():
    failed = False
    for bdf in sorted((ROOT / "bdf").glob("*.bdf")):
        total, bad = check(bdf)
        print(f"{bdf.stem:10} {total:6} glyphs  " + "  ".join(f"{m}:{n}" for m, n in bad.items()))
        failed |= any(bad.values())
    sys.exit(failed)


if __name__ == "__main__":
    main()
