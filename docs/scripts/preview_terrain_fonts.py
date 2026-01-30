#!/usr/bin/env python3
"""
terrain_font_preview.py

Generate terrain-types.html showing an example hex for each terrain type,
with the terrain symbol(s) rendered in different fonts.

This DOES NOT change your existing hex SVGs. It just builds a separate
HTML preview, using a simplified hex drawing:
- hex outline
- coloured fill from terrain.csv
- big terrain symbol(s) in the centre

The "digital clock" numeric labels are NOT included.
"""

from pathlib import Path
import html
import math

import build_single_hex_svgs as hexmod  # your original script

# DEBUG: set True to show sample letters instead of your terrain symbols
USE_TEST_LETTERS = False
TEST_SAMPLE = "AbgQy 123"


ROOT = hexmod.ROOT
OUTPUT_HTML = ROOT / "terrain-types.html"

# ---------------------------
# Fonts to preview
# ---------------------------

FONTS = [
    {
        "id": "calibri",
        "label": "Calibri",
        "svg_family": "Calibri, sans-serif",
    },
    {
        "id": "aptos",
        "label": "Aptos",
        "svg_family": "Aptos, sans-serif",
    },
    {
        "id": "gentium",
        "label": "Gentium Book Plus",
        "svg_family": "'Gentium Book Plus', serif",
    },
    {
        "id": "league",
        "label": "League Spartan",
        "svg_family": "'League Spartan', sans-serif",
    },
]

# Optional: load Google Fonts so the browser actually has these
GOOGLE_FONT_HREF = (
    "https://fonts.googleapis.com/css2?"
    "family=Gentium+Book+Basic:ital,wght@0,400;0,700;1,400;1,700&"
    "family=League+Spartan:wght@400;500;600;700&display=swap"
)


# ---------------------------
# Helpers
# ---------------------------

def collect_terrain_from_overrides(terrain_overrides: dict):
    """
    Use terrain.csv overrides as the source of terrain types to preview,
    because they are exactly where symbols are defined.
    """
    terrain_entries = []
    for terrain_name, row in sorted(terrain_overrides.items(), key=lambda kv: kv[0].lower()):
        symbol = (row.get("symbol") or "").strip()
        symbol_two = (row.get("symbol_two") or "").strip()
        hex_color = (row.get("hex_color") or "").strip()
        symbol_color = (row.get("symbol_color") or "").strip()

        if not symbol and not symbol_two:
            # No symbol defined; still keep it, but symbol will be blank
            pass

        terrain_entries.append({
            "terrain": terrain_name,
            "symbol": symbol or None,
            "symbol_two": symbol_two or None,
            "hex_color": f"#{hex_color}" if hex_color else "#eeeeee",
            "symbol_color": f"#{symbol_color}" if symbol_color else "#333333",
        })

    return terrain_entries


def make_preview_hex_svg(
    symbol: str | None,
    symbol_two: str | None,
    fill_color: str,
    symbol_color: str,
    font_family: str,
) -> str:
    # Geometry: same as your main hexes (flat-top, r=30)
    r = 30.0
    h = (math.sqrt(3) * r) / 2.0
    width = 2.0 * r
    height = 2.0 * h

    cx = r
    cy = h

    # Polygon vertices
    vertices = hexmod.flat_hex_vertices(cx, cy, r)
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in vertices)

    # Normalise the terrain symbols the same way as main script
    def norm(s: str | None) -> str | None:
        return hexmod.normalize_symbol(s) if s else None

    primary = norm(symbol)
    secondary = norm(symbol_two)

    # --- Main terrain symbol(s) in the centre ---
    symbol_markup = ""
    base_size = 26

    if primary and secondary:
        offset = base_size * 0.35
        symbol_markup = (
            f'<text x="{cx - offset:.1f}" y="{cy + offset:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="{base_size}" '
            f'font-family="{html.escape(font_family)}" '
            f'fill="{html.escape(symbol_color)}">'
            f'{html.escape(primary)}</text>'
            f'<text x="{cx + offset:.1f}" y="{cy - offset:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="{base_size * 2 / 3:.1f}" '
            f'font-family="{html.escape(font_family)}" '
            f'fill="{html.escape(symbol_color)}">'
            f'{html.escape(secondary)}</text>'
        )
    elif primary:
        symbol_markup = (
            f'<text x="{cx:.1f}" y="{cy:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="{base_size}" '
            f'font-family="{html.escape(font_family)}" '
            f'fill="{html.escape(symbol_color)}">'
            f'{html.escape(primary)}</text>'
        )
    # else: no terrain symbol, leave blank

    # --- Font sample text near the bottom so we can see the font shape ---
    sample_text = "AbgQy 123"
    sample_y = cy + (h * 0.7)  # lower part of the hex

    sample_markup = (
        f'<text x="{cx:.1f}" y="{sample_y:.1f}" '
        f'text-anchor="middle" dominant-baseline="middle" '
        f'font-size="10" '
        f'font-family="{html.escape(font_family)}" '
        f'fill="#000000">'
        f'{html.escape(sample_text)}</text>'
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{width:.2f}" height="{height:.2f}"
     viewBox="0 0 {width:.2f} {height:.2f}">
  <polygon points="{points}" fill="{html.escape(fill_color)}"
           stroke="#333333" stroke-width="2"/>
  {symbol_markup}
  {sample_markup}
</svg>"""

    return svg





def build_html(terrain_entries, terrain_svgs_by_font):
    """
    terrain_svgs_by_font[(terrain_name, font_id)] = svg_text
    """
    head = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Terrain Font Preview</title>

  <!-- Load fonts for preview -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{html.escape(GOOGLE_FONT_HREF)}" rel="stylesheet">

  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 1.5rem;
      background: #f8f8f8;
      color: #222;
    }}
    h1 {{
      margin-bottom: 0.5rem;
    }}
    .subtitle {{
      margin-top: 0;
      color: #555;
      font-size: 0.9rem;
    }}
    .terrain-section {{
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid #ddd;
    }}
    .terrain-title {{
      font-size: 1.1rem;
      margin-bottom: 0.5rem;
    }}
    .hex-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
    }}
    .hex-card {{
      background: white;
      border-radius: 0.5rem;
      padding: 0.75rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      width: 220px;
      box-sizing: border-box;
    }}
    .hex-card-title {{
      font-size: 0.9rem;
      margin-bottom: 0.5rem;
      color: #333;
    }}
    .hex-card svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
  </style>
</head>
<body>
  <h1>Terrain Font Preview</h1>
  <p class="subtitle">
    Each terrain shows a simplified hex with its terrain symbol(s) rendered
    in a different <code>font-family</code>. The seven-segment hex labels
    in your main map are not shown here.
  </p>
"""

    sections = []

    for entry in terrain_entries:
        terrain_name = entry["terrain"]
        t_safe = html.escape(terrain_name)

        cards = []
        for font in FONTS:
            font_id = font["id"]
            key = (terrain_name, font_id)
            svg_text = terrain_svgs_by_font.get(key)
            if not svg_text:
                continue

            card_html = f"""
      <div class="hex-card">
        <div class="hex-card-title">{html.escape(font["label"])}</div>
        {svg_text}
      </div>
""".rstrip()
            cards.append(card_html)

        if not cards:
            continue

        section_html = f"""
  <section class="terrain-section" id="terrain-{t_safe}">
    <div class="terrain-title">{t_safe}</div>
    <div class="hex-grid">
{chr(10).join(cards)}
    </div>
  </section>
""".rstrip()

        sections.append(section_html)

    return head + "\n".join(sections) + "\n</body>\n</html>\n"


# ---------------------------
# Main
# ---------------------------

def main():
    # Load terrain overrides from your CSV
    terrain_overrides = hexmod.load_terrain_overrides()
    terrain_entries = collect_terrain_from_overrides(terrain_overrides)

    if not terrain_entries:
        print("No terrain entries found in terrain.csv – nothing to preview.")
        return

    terrain_svgs_by_font: dict[tuple[str, str], str] = {}

    for entry in terrain_entries:
        terrain_name = entry["terrain"]
        symbol = entry["symbol"]
        symbol_two = entry["symbol_two"]
        fill_color = entry["hex_color"]
        symbol_color = entry["symbol_color"]

        for font in FONTS:
            svg_family = font["svg_family"]
            font_id = font["id"]

            svg = make_preview_hex_svg(
                symbol=symbol,
                symbol_two=symbol_two,
                fill_color=fill_color,
                symbol_color=symbol_color,
                font_family=svg_family,
            )
            terrain_svgs_by_font[(terrain_name, font_id)] = svg

    html_text = build_html(terrain_entries, terrain_svgs_by_font)
    OUTPUT_HTML.write_text(html_text, encoding="utf-8")
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
