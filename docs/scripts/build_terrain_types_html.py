from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
TERRAIN_CSV = ROOT / "terrain.csv"
POI_CSV = ROOT / "poi.csv"
OUTPUT_HTML = ROOT / "terrain-types.html"
NEUTRAL_GREEN_HEX = "a0d76b"


def normalize_symbol(symbol: str) -> str:
    return symbol.replace("\ufe0f", "") + "\ufe0e"


def hex_points(cx: float, cy: float, r: float) -> str:
    h = (3**0.5) * r / 2
    points = [
        (cx + r, cy),
        (cx + r / 2, cy - h),
        (cx - r / 2, cy - h),
        (cx - r, cy),
        (cx - r / 2, cy + h),
        (cx + r / 2, cy + h),
    ]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def iter_terrain_rows() -> Iterable[dict[str, str]]:
    with TERRAIN_CSV.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            terrain = (row.get("terrain") or "").strip()
            if not terrain:
                continue
            yield {
                "terrain": terrain,
                "hex_color": (row.get("hex-color") or "").strip(),
                "symbol_color": (row.get("symbol-color") or "").strip(),
                "symbol": (row.get("symbol") or "").strip(),
                "symbol_two": (row.get("symbol-two") or "").strip(),
            }


def iter_poi_rows() -> Iterable[dict[str, str]]:
    with POI_CSV.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            symbol = (row[0] or "").strip()
            poi = (row[1] or "").strip()
            symbol_color = (row[2] or "").strip() if len(row) > 2 else ""
            if not symbol or not poi:
                continue
            yield {
                "poi": poi,
                "symbol": symbol,
                "symbol_color": symbol_color,
            }


def make_svg(
    hex_color: str,
    symbol: str,
    symbol_two: str,
    symbol_color: str,
    font_family: str = "sans-serif",
) -> str:
    size = 60
    r = 24
    cx = size / 2
    cy = size / 2
    fill = f"#{hex_color}" if hex_color else "#cccccc"
    text_fill = f"#{symbol_color}" if symbol_color else "#333333"
    symbol_text = normalize_symbol(symbol) if symbol else ""
    points = hex_points(cx, cy, r)
    base_size = 24
    font_family_escaped = html.escape(font_family, quote=True)
    symbol_markup = ""
    if symbol or symbol_two:
        if symbol and symbol_two:
            offset = base_size * 0.3
            primary_symbol = normalize_symbol(symbol)
            secondary_symbol = normalize_symbol(symbol_two)
            symbol_markup = (
                f'<text x="{cx - offset}" y="{cy + offset}" text-anchor="middle" '
                f"dominant-baseline=\"middle\" font-size=\"{base_size}\" "
                f"font-family='{font_family_escaped}' "
                f'fill="{text_fill}">{html.escape(primary_symbol)}</text>'
                f'<text x="{cx + offset}" y="{cy - offset}" text-anchor="middle" '
                f"dominant-baseline=\"middle\" font-size=\"{base_size * 2 / 3:.1f}\" "
                f"font-family='{font_family_escaped}' fill=\"{text_fill}\">"
                f"{html.escape(secondary_symbol)}</text>"
            )
        else:
            symbol_text = normalize_symbol(symbol or symbol_two)
            symbol_markup = (
                f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                f"dominant-baseline=\"middle\" font-size=\"{base_size}\" "
                f"font-family='{font_family_escaped}' "
                f'fill="{text_fill}">{html.escape(symbol_text)}</text>'
            )
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{html.escape(symbol_text)}">'
        f'<polygon points="{points}" fill="{fill}" stroke="#222" stroke-width="2"/>'
        f'{symbol_markup}'
        "</svg>"
    )


def build_html(
    rows: Iterable[dict[str, str]],
    poi_rows: Iterable[dict[str, str]],
) -> str:
    rows = list(rows)
    poi_rows = list(poi_rows)
    font_previews = [
        ("Calibri", '"Calibri", "Carlito", system-ui, sans-serif'),
        ("Aptos", '"Aptos", "Segoe UI", system-ui, sans-serif'),
        ("Segoe UI", '"Segoe UI", system-ui, sans-serif'),
        ("Roboto", '"Roboto", "Noto Sans", system-ui, sans-serif'),
        ("Georgia", '"Georgia", "Times New Roman", serif'),
    ]

    def build_table_rows(
        base_rows: Iterable[dict[str, str]],
        label_key: str,
        hex_color_getter: Callable[[dict[str, str]], str],
        symbol_two_key: str | None = "symbol_two",
    ) -> str:
        row_parts = []
        for row in base_rows:
            hex_color = hex_color_getter(row)
            symbol_two = row.get(symbol_two_key, "") if symbol_two_key else ""
            svg = make_svg(hex_color, row["symbol"], symbol_two, row["symbol_color"])
            preview_parts = []
            for label, font_stack in font_previews:
                preview_svg = make_svg(
                    hex_color,
                    row["symbol"],
                    symbol_two,
                    row["symbol_color"],
                    font_family=font_stack,
                )
                preview_parts.append(
                    "\n".join(
                        [
                            '<div class="tile-swatch">',
                            f"  {preview_svg}",
                            f'  <span class="font-label">{html.escape(label)}</span>',
                            "</div>",
                        ]
                    )
                )
            row_parts.append(
                "\n".join(
                    [
                        "<tr>",
                        f"  <td>{html.escape(row[label_key])}</td>",
                        f"  <td class=\"example\">{svg}</td>",
                        "  <td class=\"font-previews\">",
                        '    <div class="font-preview-grid">',
                        "\n".join(f"      {part}" for part in preview_parts),
                        "    </div>",
                        "  </td>",
                        "</tr>",
                    ]
                )
            )
        return "\n".join(row_parts)

    table_rows = build_table_rows(
        rows,
        "terrain",
        lambda row: row["hex_color"],
        symbol_two_key="symbol_two",
    )
    poi_table_rows = build_table_rows(
        poi_rows,
        "poi",
        lambda _row: NEUTRAL_GREEN_HEX,
        symbol_two_key=None,
    )
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Terrain types</title>
    <style>
      body {
        font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        margin: 2rem;
        color: #222;
      }
      table {
        border-collapse: collapse;
        width: 100%;
        max-width: 720px;
      }
      th, td {
        border: 1px solid #ccc;
        padding: 0.5rem 0.75rem;
        text-align: left;
        vertical-align: middle;
      }
      th {
        background: #f4f4f4;
      }
      td.example {
        width: 100px;
      }
      td.font-previews {
        min-width: 320px;
      }
      .font-preview-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: flex-start;
      }
      .tile-swatch {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
      }
      .tile-swatch svg {
        display: block;
      }
      .font-label {
        font-size: 0.75rem;
        color: #555;
      }
    </style>
  </head>
  <body>
    <h1>Terrain types</h1>
    <table>
      <thead>
        <tr>
          <th>Terrain</th>
          <th>Example</th>
          <th>Font previews</th>
        </tr>
      </thead>
      <tbody>
""" + table_rows + """
      </tbody>
    </table>
    <h2>Points of interest</h2>
    <table>
      <thead>
        <tr>
          <th>Point of interest</th>
          <th>Example</th>
          <th>Font previews</th>
        </tr>
      </thead>
      <tbody>
""" + poi_table_rows + """
      </tbody>
    </table>
  </body>
</html>
"""


def main() -> None:
    rows = list(iter_terrain_rows())
    poi_rows = list(iter_poi_rows())
    html_content = build_html(rows, poi_rows)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    main()
