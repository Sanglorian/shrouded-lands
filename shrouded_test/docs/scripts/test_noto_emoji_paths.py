#!/usr/bin/env python3
"""
test_terrain_poi_emoji_fonts.py

Read all terrain + POI symbols from terrain.csv and poi.csv (via
build_single_hex_svgs helpers) and render, for EACH GLYPH:

  - Noto Emoji glyph as an SVG <path> (via fontTools)
  - OpenMoji Black glyph as an SVG <path> (via fontTools)
  - The same glyph as SVG <text> using the SAME normalize_symbol() logic
    and font-family as build_single_hex_svgs.py

Also show the terrain/POI label so you can see what each glyph is used for.
"""

from pathlib import Path
import html

from emoji_to_path import char_to_svg_path
import build_single_hex_svgs as hexmod  # reuse normalize_symbol + CSV loaders


# ----------------------------
# CONFIG
# ----------------------------

HERE = Path(__file__).resolve().parent
FONTS_DIR = (HERE / ".." / "fonts").resolve()

# Font files – expected to live in docs/fonts/
NOTO_FONT_PATH = (FONTS_DIR / "NotoEmoji-Regular.ttf").resolve()
OPENMOJI_FONT_PATH = (FONTS_DIR / "OpenMoji-black-glyf.ttf").resolve()

OUTPUT_HTML = HERE / "terrain_poi_emoji_test.html"


# ----------------------------
# Helpers to extract glyphs
# ----------------------------

def split_symbols(s: str) -> list[str]:
    """
    Split a symbol field into individual glyphs:

    - Strip whitespace.
    - Remove variation selectors (U+FE0F/U+FE0E).
    - Return a list of individual codepoints (characters) that remain.
    """
    if not s:
        return []
    cleaned = s.replace("\ufe0f", "").replace("\ufe0e", "").strip()
    return [ch for ch in cleaned if ch.strip()]


def load_glyph_rows() -> list[dict]:
    """
    Use build_single_hex_svgs helpers to read terrain.csv and poi.csv, and
    return a list of glyph rows:

      {
        "kind": "terrain" | "poi",
        "name": terrain_or_poi_name,
        "source": "symbol" | "symbol-two" | "poi-symbol",
        "char": single_character_glyph
      }
    """
    rows: list[dict] = []

    # Terrain symbols from terrain.csv via load_terrain_overrides()
    terrain_overrides = hexmod.load_terrain_overrides()
    # terrain_overrides: { terrain_name: { "hex_color", "symbol_color", "symbol", "symbol_two" } }

    for terrain_name, tovr in sorted(terrain_overrides.items(), key=lambda kv: kv[0].lower()):
        for field, source_tag in (("symbol", "symbol"), ("symbol_two", "symbol-two")):
            raw = (tovr.get(field) or "").strip()
            if not raw:
                continue
            chars = split_symbols(raw)
            for ch in chars:
                rows.append(
                    {
                        "kind": "terrain",
                        "name": terrain_name,
                        "source": source_tag,
                        "char": ch,
                    }
                )

    # POI symbols from poi.csv via load_poi_symbols()
    poi_symbols = hexmod.load_poi_symbols()
    # poi_symbols: { poi_name: { "symbol": symbol, "color": color } }

    for poi_name, pdata in sorted(poi_symbols.items(), key=lambda kv: kv[0].lower()):
        raw = (pdata.get("symbol") or "").strip()
        if not raw:
            continue
        chars = split_symbols(raw)
        for ch in chars:
            rows.append(
                {
                    "kind": "poi",
                    "name": poi_name,
                    "source": "poi-symbol",
                    "char": ch,
                }
            )

    return rows


# ----------------------------
# SVG helpers
# ----------------------------

def make_path_svg_for_glyph(ch: str, font_path: Path) -> str:
    """
    Build a small SVG snippet that shows a glyph from the given font as a <path>.

    - ch is a single codepoint (variation selectors already removed)
    - We scale to ~64 px and draw in a 140x140 canvas, shifted left so nothing clips.
    """
    d = char_to_svg_path(ch, font_path, target_px=64.0)

    # Bigger canvas so we don't clip; shift LEFT (x=50) so right side is visible.
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="140" height="140" viewBox="0 0 140 140">
  <rect x="0" y="0" width="140" height="140" fill="#f0f0f0" />
  <g transform="translate(50,110)">
    <path d="{d}" fill="#000000" />
  </g>
</svg>"""
    return svg


def make_system_svg_for_glyph(ch: str) -> str:
    """
    Build an SVG that uses normal <text> with the same normalization and
    font-family as build_single_hex_svgs.make_svg does for terrain symbols.

    That script:
      - calls normalize_symbol(symbol)
      - renders with font-family="system-ui, sans-serif"
    """
    normalized = hexmod.normalize_symbol(ch)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="140" height="140" viewBox="0 0 140 140">
  <rect x="0" y="0" width="140" height="140" fill="#f0f0f0" />
  <text x="70" y="90"
        text-anchor="middle"
        dominant-baseline="middle"
        font-size="64"
        font-family="system-ui, sans-serif">
    {html.escape(normalized)}
  </text>
</svg>"""
    return svg


# ----------------------------
# HTML builder
# ----------------------------

def build_html() -> str:
    glyph_rows = load_glyph_rows()
    glyph_rows.sort(key=lambda r: (r["kind"], r["name"], r["source"], r["char"]))

    rows_html_fragments = []

    for row in glyph_rows:
        ch = row["char"]
        kind = row["kind"]
        name = row["name"]
        source = row["source"]

        codepoint = f"U+{ord(ch):04X}"
        label = f"[{kind}] {name} ({source})"

        # Noto Emoji path
        try:
            noto_svg = make_path_svg_for_glyph(ch, NOTO_FONT_PATH)
            noto_cell = noto_svg
            noto_note = ""
        except Exception as e:
            noto_cell = (
                f'<div style="color:#b00; font-size: 12px;">'
                f'Error: {html.escape(str(e))}'
                f'</div>'
            )
            noto_note = " (no glyph in Noto?)"

        # OpenMoji Black path
        try:
            openmoji_svg = make_path_svg_for_glyph(ch, OPENMOJI_FONT_PATH)
            openmoji_cell = openmoji_svg
            openmoji_note = ""
        except Exception as e:
            openmoji_cell = (
                f'<div style="color:#b00; font-size: 12px;">'
                f'Error: {html.escape(str(e))}'
                f'</div>'
            )
            openmoji_note = " (no glyph in OpenMoji?)"

        # System-default SVG text, matching your hex generator's behavior
        system_svg = make_system_svg_for_glyph(ch)

        row_html = f"""
      <tr>
        <td style="padding: 0.5rem; white-space: nowrap; vertical-align: top;">
          <code>{html.escape(ch)}</code><br>
          <small>{html.escape(codepoint)}</small><br>
          <small>{html.escape(label)}</small>
        </td>
        <td style="padding: 0.5rem; text-align: center; border-left: 1px solid #ddd; vertical-align: top;">
          {noto_cell}
          <div style="font-size: 11px; color: #555; margin-top: 0.25rem;">
            Noto Emoji as &lt;path&gt;{html.escape(noto_note)}
          </div>
        </td>
        <td style="padding: 0.5rem; text-align: center; border-left: 1px solid #ddd; vertical-align: top;">
          {openmoji_cell}
          <div style="font-size: 11px; color: #555; margin-top: 0.25rem;">
            OpenMoji Black as &lt;path&gt;{html.escape(openmoji_note)}
          </div>
        </td>
        <td style="padding: 0.5rem; text-align: center; border-left: 1px solid #ddd; vertical-align: top;">
          {system_svg}
          <div style="font-size: 11px; color: #555; margin-top: 0.25rem;">
            System emoji as SVG &lt;text&gt; (normalize_symbol + system-ui)
          </div>
        </td>
      </tr>
""".rstrip()

        rows_html_fragments.append(row_html)

    rows_html = "\n".join(rows_html_fragments)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Terrain &amp; POI Emoji – Noto/OpenMoji vs System</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 1.5rem;
      background: #fafafa;
      color: #222;
    }}
    h1 {{
      margin-bottom: 0.5rem;
    }}
    .subtitle {{
      margin-top: 0;
      margin-bottom: 1.5rem;
      color: #555;
      font-size: 0.9rem;
      max-width: 60rem;
    }}
    table {{
      border-collapse: collapse;
      background: white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    th, td {{
      border-bottom: 1px solid #ddd;
    }}
    th {{
      background: #f0f0f0;
      font-weight: 600;
      text-align: left;
      padding: 0.5rem;
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <h1>Terrain &amp; POI Emoji – Noto/OpenMoji vs System</h1>
  <p class="subtitle">
    Each row is a glyph from your terrain/POI data (terrain.csv and poi.csv),
    labelled with its terrain/POI name. Columns show:
    <strong>Noto Emoji Regular</strong> as SVG <code>&lt;path&gt;</code>,
    <strong>OpenMoji Black</strong> as SVG <code>&lt;path&gt;</code>, and the same glyph
    rendered as SVG <code>&lt;text&gt;</code> using <code>normalize_symbol()</code> and
    <code>font-family="system-ui, sans-serif"</code>, matching your hex generator.
  </p>
  <table>
    <tr>
      <th>Glyph &amp; Label</th>
      <th>Noto Emoji as Path</th>
      <th>OpenMoji Black as Path</th>
      <th>System Emoji as SVG Text</th>
    </tr>
{rows_html}
  </table>
</body>
</html>
"""
    return html_doc


# ----------------------------
# Main
# ----------------------------

def main():
    missing = []
    if not NOTO_FONT_PATH.exists():
        missing.append(str(NOTO_FONT_PATH))
    if not OPENMOJI_FONT_PATH.exists():
        missing.append(str(OPENMOJI_FONT_PATH))

    if missing:
        msg = "Font file(s) not found:\n  " + "\n  ".join(missing)
        msg += "\n\nMake sure NotoEmoji-Regular.ttf and OpenMoji-black-glyf.ttf are in docs/fonts/ (or update paths in this script)."
        raise SystemExit(msg)

    html_text = build_html()
    OUTPUT_HTML.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT_HTML.resolve()}")
    print("Open this file in a browser to compare Noto/OpenMoji paths vs system emoji for all terrain/POI glyphs.")


if __name__ == "__main__":
    main()
