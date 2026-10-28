#!/usr/bin/env python3
"""Convert the X11 misc-fixed BDF bitmaps in bdf/ into outline TTFs in ttf/.

Every lit pixel becomes a square of UNITS font units, and the em is the BDF
PIXEL_SIZE, so rendering at that many pixels per em reproduces the bitmap
exactly. Pixels are traced into merged contours rather than emitted as one
square each, so anti-aliased rasterizers never show seams between them.
"""

import sys
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables.O_S_2f_2 import Panose

UNITS = 128
ROOT = Path(__file__).resolve().parent
VERSION = "1.0"

STYLES = {"": "Regular", "B": "Bold", "O": "Italic"}


def parse_bdf(path):
    props, glyphs = {}, []
    lines = iter(path.read_text(encoding="latin-1").splitlines())
    for line in lines:
        key, _, rest = line.partition(" ")
        if key == "STARTPROPERTIES":
            for line in lines:
                if line == "ENDPROPERTIES":
                    break
                k, _, v = line.partition(" ")
                props[k] = v.strip('"')
        elif key == "STARTCHAR":
            g = {"name": rest}
            for line in lines:
                k, _, v = line.partition(" ")
                if k == "ENCODING":
                    g["code"] = int(v.split()[0])
                elif k == "DWIDTH":
                    g["advance"] = int(v.split()[0])
                elif k == "BBX":
                    g["bbx"] = tuple(map(int, v.split()))
                elif k == "BITMAP":
                    w, h = g["bbx"][:2]
                    rows = [next(lines) for _ in range(h)]
                    g["rows"] = [int(r, 16) >> (len(r) * 4 - w) if r else 0 for r in rows]
                elif k == "ENDCHAR":
                    break
            glyphs.append(g)
    return props, glyphs


def lit_pixels(g):
    w, h, xoff, yoff = g["bbx"]
    for r, bits in enumerate(g["rows"]):
        y = yoff + h - 1 - r
        for c in range(w):
            if bits >> (w - 1 - c) & 1:
                yield xoff + c, y


def trace(pixels):
    """Boundary contours of a pixel set, clockwise with ink on the right."""
    pixels = set(pixels)
    edges = {}
    for x, y in pixels:
        for a, b in (((x, y), (x, y + 1)), ((x, y + 1), (x + 1, y + 1)),
                     ((x + 1, y + 1), (x + 1, y)), ((x + 1, y), (x, y))):
            # A shared edge between two lit pixels appears once each way.
            if a in edges.get(b, ()):
                edges[b].discard(a)
            else:
                edges.setdefault(a, set()).add(b)
    contours = []
    while any(edges.values()):
        # A pinch vertex has two exits and no incoming direction yet to pick one.
        start = next(p for p, outs in edges.items() if len(outs) == 1)
        prev, cur = None, start
        points = [start]
        while True:
            outs = edges[cur]
            if len(outs) == 1:
                nxt = next(iter(outs))
            else:
                # Diagonal pinch: turn right so each pixel's contour stays its own.
                dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                right = (cur[0] + dy, cur[1] - dx)
                nxt = right if right in outs else next(iter(outs))
            outs.discard(nxt)
            prev, cur = cur, nxt
            if cur == start:
                break
            points.append(cur)
        contours.append(simplify(points))
    return contours


def simplify(points):
    n = len(points)
    keep = []
    for i, p in enumerate(points):
        a, b = points[i - 1], points[(i + 1) % n]
        if (p[0] - a[0]) * (b[1] - p[1]) != (p[1] - a[1]) * (b[0] - p[0]):
            keep.append(p)
    return keep


def draw(pixels):
    pen = TTGlyphPen(None)
    for contour in trace(pixels):
        pen.moveTo((contour[0][0] * UNITS, contour[0][1] * UNITS))
        for x, y in contour[1:]:
            pen.lineTo((x * UNITS, y * UNITS))
        pen.closePath()
    return pen.glyph()


def build(bdf, out_dir):
    stem = bdf.stem
    suffix = stem[-1] if stem[-1] in "BO" else ""
    size = stem[: len(stem) - len(suffix)]
    style = STYLES[suffix]
    family = f"Fixed {size}"
    ps_name = f"Fixed{size}-{style}"

    props, glyphs = parse_bdf(bdf)
    ascent, descent = int(props["FONT_ASCENT"]), int(props["FONT_DESCENT"])
    advance = glyphs[0]["advance"] * UNITS

    default = int(props.get("DEFAULT_CHAR", -1))
    order, cmap, outlines, metrics = [".notdef"], {}, {}, {}
    notdef = next((g for g in glyphs if g.get("code") == default), None)
    outlines[".notdef"] = draw(lit_pixels(notdef)) if notdef else TTGlyphPen(None).glyph()
    metrics[".notdef"] = (advance, 0)
    for g in glyphs:
        code = g.get("code", -1)
        if code < 0 or code in cmap:
            continue
        name = f"uni{code:04X}" if code <= 0xFFFF else f"u{code:05X}"
        order.append(name)
        cmap[code] = name
        glyph = draw(lit_pixels(g))
        outlines[name] = glyph
        glyph.recalcBounds(None)
        metrics[name] = (g["advance"] * UNITS, getattr(glyph, "xMin", 0))

    fb = FontBuilder(int(props["PIXEL_SIZE"]) * UNITS, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascent * UNITS, descent=-descent * UNITS)
    fb.setupNameTable({
        "copyright": props.get("COPYRIGHT", "Public domain font."),
        "familyName": family,
        "styleName": style,
        "uniqueFontIdentifier": f"{ps_name};{VERSION}",
        "fullName": f"{family} {style}" if style != "Regular" else family,
        "psName": ps_name,
        "version": f"Version {VERSION}",
        "description": f"Outline conversion of the X11 misc-fixed {stem} bitmap font",
    })
    panose = Panose()
    panose.bFamilyType = 2
    panose.bProportion = 9  # monospaced
    fs_selection = {"Regular": 1 << 6, "Bold": 1 << 5, "Italic": 1 << 0}[style]
    fb.setupOS2(
        usWeightClass=700 if style == "Bold" else 400,
        fsSelection=fs_selection,
        fsType=0,
        achVendID="MISC",
        xAvgCharWidth=advance,
        sTypoAscender=ascent * UNITS,
        sTypoDescender=-descent * UNITS,
        sTypoLineGap=0,
        usWinAscent=ascent * UNITS,
        usWinDescent=descent * UNITS,
        sxHeight=int(props.get("X_HEIGHT", 0)) * UNITS,
        sCapHeight=int(props.get("CAP_HEIGHT", 0)) * UNITS,
        panose=panose,
    )
    fb.font["OS/2"].recalcUnicodeRanges(fb.font)
    fb.font["head"].macStyle = {"Regular": 0, "Bold": 1, "Italic": 2}[style]
    fb.setupPost(isFixedPitch=1)

    out = out_dir / f"{ps_name}.ttf"
    fb.save(out)
    return out


def main():
    out_dir = ROOT / "ttf"
    out_dir.mkdir(exist_ok=True)
    bdfs = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "bdf").glob("*.bdf"))
    for bdf in bdfs:
        print(build(bdf, out_dir).relative_to(ROOT))


if __name__ == "__main__":
    main()
