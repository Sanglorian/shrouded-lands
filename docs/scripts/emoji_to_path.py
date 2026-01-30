# scripts/emoji_to_path.py

from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen


def char_to_svg_path(
    char: str,
    font_path: str | Path,
    target_px: float = 26.0,
) -> str:
    """
    Convert a single Unicode character to an SVG path string
    using the given TrueType/OpenType font.

    - char: a single Unicode character (e.g. "🌳")
    - font_path: path to NotoEmoji-Regular.ttf (or similar)
    - target_px: approximate cap-height in pixels

    Returns a 'd' string suitable for <path d="...">.
    """
    font_path = Path(font_path)
    font = TTFont(font_path)

    cmap = font.getBestCmap()
    codepoint = ord(char)
    if codepoint not in cmap:
        raise ValueError(f"Font {font_path.name} has no glyph for {repr(char)} (U+{codepoint:04X})")

    glyph_name = cmap[codepoint]
    glyph_set = font.getGlyphSet()
    glyph = glyph_set[glyph_name]

    units_per_em = font["head"].unitsPerEm

    # Scale from font units to pixels
    scale = target_px / units_per_em

    # Build an SVG path pen with a scale + y-flip (font y-axis is up; SVG y-axis is down)
    svg_pen = SVGPathPen(glyph_set)
    t_pen = TransformPen(svg_pen, (scale, 0, 0, -scale, 0, 0))
    glyph.draw(t_pen)

    d = svg_pen.getCommands()
    return d
