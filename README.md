# misc-fixed-ttf

The X11 `fixed` bitmap fonts (`6x13`, `9x15`, `10x20`, ...) converted to
outline TrueType, so they work in places that no longer load bitmap fonts:
Wayland compositors, GTK/Pango 1.44+, kitty, and anything else built on
fontconfig + FreeType.

Every lit pixel of the original bitmap becomes a square in the outline, and
the em size is the bitmap's pixel size. Rendered at its native pixel size, each
font reproduces the original bitmap exactly. `verify.py` checks that for every
glyph under full, light, forced-auto and no hinting: 116,138 glyphs, 0
differences.

## Fonts

| Family          | Cell  | Styles                 | Glyphs |
|-----------------|-------|------------------------|-------:|
| `Fixed 4x6`     | 4×6   | Regular                |    919 |
| `Fixed 5x7`     | 5×7   | Regular                |  1,848 |
| `Fixed 5x8`     | 5×8   | Regular                |  1,426 |
| `Fixed 6x9`     | 6×9   | Regular                |  1,296 |
| `Fixed 6x10`    | 6×10  | Regular                |  1,597 |
| `Fixed 6x12`    | 6×12  | Regular                |  4,531 |
| `Fixed 6x13`    | 6×13  | Regular, Bold, Italic  |  4,121 |
| `Fixed 7x13`    | 7×13  | Regular, Bold, Italic  |  3,226 |
| `Fixed 7x14`    | 7×14  | Regular, Bold          |  2,576 |
| `Fixed 8x13`    | 8×13  | Regular, Bold, Italic  |  3,703 |
| `Fixed 9x15`    | 9×15  | Regular, Bold          |  4,777 |
| `Fixed 9x18`    | 9×18  | Regular, Bold          |  4,766 |
| `Fixed 10x20`   | 10×20 | Regular                |  5,205 |
| `Fixed 12x13ja` | 12×13 | Regular (Japanese)     | 19,208 |
| `Fixed 18x18ja` | 18×18 | Regular (Japanese)     | 19,168 |
| `Fixed 18x18ko` | 18×18 | Regular (Korean)       | 27,990 |

`Fixed 6x13` is the one X calls `fixed` and xterm uses by default. Glyph counts
are for the Regular style; the Bold and Italic files cover fewer characters,
the same as the originals, and the terminal falls back to Regular or another
font for the rest. "Italic" is the original oblique (`6x13O` etc.).

## Install

Copy the files from `ttf/` into `~/.local/share/fonts/` and run `fc-cache -f`.

## Use it at the right size

The fonts are only pixel-perfect at their native pixel size, or a whole
multiple of it. The pixel size is the second number in the name. Most programs
take a size in points, which at 96 DPI is `pixels × 0.75`:

| Font          | Pixels | Points at 96 DPI |
|---------------|-------:|-----------------:|
| `Fixed 6x13`  |     13 |             9.75 |
| `Fixed 9x15`  |     15 |            11.25 |
| `Fixed 9x18`  |     18 |             13.5 |
| `Fixed 10x20` |     20 |               15 |

For kitty at 96 DPI (a Wayland output at scale 1):

```
font_family Fixed 6x13
font_size   9.75
```

At other sizes the outlines scale like any other font and look soft.

## Building

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build.py    # bdf/*.bdf -> ttf/*.ttf
.venv/bin/python verify.py   # render every glyph and compare to the bitmap
```

## Source and license

The BDF files in `bdf/` are from Markus Kuhn's
[Unicode fonts and tools for X11](https://www.cl.cam.ac.uk/~mgk25/ucs-fonts.html)
(`ucs-fonts.tar.gz` and `ucs-fonts-asian.tar.gz`), unmodified. They are in the
public domain, and so are the converted fonts and the scripts here. See
`LICENSE`.
