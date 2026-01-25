from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TERRAIN_CSV = ROOT / "terrain.csv"
OUTPUT_HTML = ROOT / "terrain-types.html"


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


def make_svg(hex_color: str, symbol: str, symbol_two: str, symbol_color: str) -> str:
    size = 60
    r = 24
    cx = size / 2
    cy = size / 2
    fill = f"#{hex_color}" if hex_color else "#cccccc"
    text_fill = f"#{symbol_color}" if symbol_color else "#333333"
    symbol_text = normalize_symbol(symbol) if symbol else ""
    points = hex_points(cx, cy, r)
    base_size = 24
    symbol_markup = ""
    if symbol or symbol_two:
        if symbol and symbol_two:
            offset = base_size * 0.3
            primary_symbol = normalize_symbol(symbol)
            secondary_symbol = normalize_symbol(symbol_two)
            symbol_markup = (
                f'<text x="{cx - offset}" y="{cy + offset}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{base_size}" font-family="sans-serif" '
                f'fill="{text_fill}">{html.escape(primary_symbol)}</text>'
                f'<text x="{cx + offset}" y="{cy - offset}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{base_size * 2 / 3:.1f}" '
                f'font-family="sans-serif" fill="{text_fill}">{html.escape(secondary_symbol)}</text>'
            )
        else:
            symbol_text = normalize_symbol(symbol or symbol_two)
            symbol_markup = (
                f'<text x="{cx}" y="{cy}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{base_size}" font-family="sans-serif" '
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


def build_html(rows: Iterable[dict[str, str]]) -> str:
    row_parts = []
    for row in rows:
        svg = make_svg(row["hex_color"], row["symbol"], row["symbol_two"], row["symbol_color"])
        row_parts.append(
            "\n".join(
                [
                    "<tr>",
                    f"  <td>{html.escape(row['terrain'])}</td>",
                    f"  <td class=\"example\">{svg}</td>",
                    "</tr>",
                ]
            )
        )

    table_rows = "\n".join(row_parts)
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
    </style>
  </head>
  <body>
    <h1>Terrain types</h1>
    <table>
      <thead>
        <tr>
          <th>Terrain</th>
          <th>Example</th>
        </tr>
      </thead>
      <tbody>
""" + table_rows + """
      </tbody>
    </table>
  </body>
</html>
"""


def main() -> None:
    rows = list(iter_terrain_rows())
    html_content = build_html(rows)
    OUTPUT_HTML.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    main()
