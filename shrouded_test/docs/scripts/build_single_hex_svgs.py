from pathlib import Path
import csv
import math
import re
from typing import Optional
import yaml

# === CONFIG ===

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
OUT_DIR = ROOT / "assets" / "hexes"
TERRAIN_CSV = ROOT / "terrain.csv"
POI_CSV = ROOT / "poi.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

HEX_TITLE_RE = re.compile(r"^(\d{2})\.(\d{2})(?:\.\d{2})?$")


# === FRONT MATTER PARSING ===

def split_front_matter(text: str):
    """
    Returns (raw_front_matter_text, front_matter_dict, body_text).
    If no front matter exists, returns ("", {}, text).
    """
    if not text.startswith("---"):
        return "", {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", {}, text
    fm_raw = parts[1]
    body = parts[2].lstrip("\n")
    fm = yaml.safe_load(fm_raw) or {}
    return fm_raw, fm, body


def collect_hex_metadata():
    """
    Scans _wiki/*.md and returns a dict keyed by "XX.YY" of:
      {
        "has_page": True,
        "color_hex": "#RRGGBB" or None
      }
    """
    meta = {}
    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm_raw, fm, body = split_front_matter(text)

        title = str(fm.get("title") or "").strip()
        m = HEX_TITLE_RE.match(title)
        if not m:
            continue

        code = f"{m.group(1)}.{m.group(2)}"
        color_hex = fm.get("color_hex")

        meta[code] = {
            "has_page": True,
            "color_hex": color_hex,
            "terrain": fm.get("terrain"),
            "poi": fm.get("poi"),
        }
    return meta


def load_terrain_overrides():
    if not TERRAIN_CSV.exists():
        return {}
    with TERRAIN_CSV.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        overrides = {}
        for row in reader:
            terrain = (row.get("terrain") or "").strip()
            if not terrain:
                continue
            overrides[terrain] = {
                "hex_color": (row.get("hex-color") or "").strip(),
                "symbol_color": (row.get("symbol-color") or "").strip(),
                "symbol": (row.get("symbol") or "").strip(),
                "symbol_two": (row.get("symbol-two") or "").strip(),
            }
        return overrides


def load_poi_symbols():
    if not POI_CSV.exists():
        return {}
    symbols = {}
    with POI_CSV.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            symbol = (row[0] or "").strip()
            poi_name = (row[1] or "").strip()
            if not symbol or not poi_name:
                continue
            symbols[poi_name] = symbol
    return symbols

def normalize_symbol(symbol: str) -> str:
    return symbol.replace("\ufe0f", "") + "\ufe0e"


# === HEX GEOMETRY ===

def flat_hex_points(cx, cy, r):
    """Flat-top regular hexagon (top/bottom edges horizontal)."""
    h = (math.sqrt(3) * r) / 2.0

    pts = [
        (cx - r / 2.0, cy - h),  # top-left
        (cx + r / 2.0, cy - h),  # top-right
        (cx + r,       cy),      # right
        (cx + r / 2.0, cy + h),  # bottom-right
        (cx - r / 2.0, cy + h),  # bottom-left
        (cx - r,       cy),      # left
    ]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


# === SVG CREATION ===

def make_svg(
    code: str,
    has_page: bool,
    fill_color: str,
    symbol: Optional[str],
    symbol_color: Optional[str],
    symbol_two: Optional[str],
    poi_symbol: Optional[str],
) -> str:
    # code like "10.09"
    x_str, y_str = code.split(".")
    slug = f"{x_str}-{y_str}"

    # --- Hex geometry: side length / radius = 30, no padding ---
    r = 30.0
    h = (math.sqrt(3) * r) / 2.0

    # Tight bounding box: hex touches all edges
    width = 2.0 * r
    height = 2.0 * h

    # Center of hex
    cx = r
    cy = h
    points = flat_hex_points(cx, cy, r)

    stroke = "#333333"

    if has_page:
        link_open = f'<a xlink:href="/wiki/{slug}/">'
        link_close = "</a>"
    else:
        link_open = ""
        link_close = ""

    symbol_markup = ""
    if symbol or symbol_two:
        base_size = 24
        if symbol and symbol_two:
            offset = base_size * 0.3
            primary_symbol = normalize_symbol(symbol)
            secondary_symbol = normalize_symbol(symbol_two)
            symbol_markup = (
                f'<text x="{cx - offset:.1f}" y="{cy + offset:.1f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{base_size}" '
                f'font-family="system-ui, sans-serif" fill="{symbol_color or "#333333"}">'
                f'{primary_symbol}</text>'
                f'<text x="{cx + offset:.1f}" y="{cy - offset:.1f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{base_size * 2 / 3:.1f}" '
                f'font-family="system-ui, sans-serif" fill="{symbol_color or "#333333"}">'
                f'{secondary_symbol}</text>'
            )
        else:
            symbol_text = normalize_symbol(symbol or symbol_two)
            symbol_markup = (
                f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
                f'dominant-baseline="middle" font-size="{base_size}" '
                f'font-family="system-ui, sans-serif" fill="{symbol_color or "#333333"}">'
                f'{symbol_text}</text>'
            )
    if poi_symbol:
        poi_text = normalize_symbol(poi_symbol)
        symbol_markup += (
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="24" '
            f'font-family="system-ui, sans-serif" fill="#000000">'
            f'{poi_text}</text>'
        )

    label_y = height - 6.0
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width:.2f}" height="{height:.2f}" viewBox="0 0 {width:.2f} {height:.2f}">
  {link_open}
    <polygon points="{points}" fill="{fill_color}" stroke="{stroke}" stroke-width="2"/>
    {symbol_markup}
    <text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" dominant-baseline="alphabetic"
          font-size="9" font-family="system-ui, sans-serif">{code}</text>
  {link_close}
</svg>
"""


# === MAIN ===

def main():
    hex_meta = collect_hex_metadata()
    terrain_overrides = load_terrain_overrides()
    poi_symbols = load_poi_symbols()
    print(f"Found {len(hex_meta)} existing hex pages.")

    for x in range(45):     # 00–44
        for y in range(30): # 00–29
            code = f"{x:02d}.{y:02d}"
            meta = hex_meta.get(code)

            if meta:
                has_page = True
                fill_color = meta.get("color_hex") or "#ffdca8"
                terrain = meta.get("terrain")
                poi_name = (meta.get("poi") or "").strip() if isinstance(meta.get("poi"), str) else ""
                override = terrain_overrides.get(terrain)
            else:
                has_page = False
                fill_color = "#eeeeee"
                poi_name = ""
                override = None

            if override:
                fill_color = f"#{override['hex_color']}" if override["hex_color"] else fill_color
                symbol = override.get("symbol")
                symbol_two = override.get("symbol_two")
                symbol_color = f"#{override['symbol_color']}" if override["symbol_color"] else None
            else:
                symbol = None
                symbol_two = None
                symbol_color = None
            poi_symbol = poi_symbols.get(poi_name) if poi_name else None

            svg = make_svg(code, has_page, fill_color, symbol, symbol_color, symbol_two, poi_symbol)
            fname = f"hex-{x:02d}-{y:02d}.svg"
            (OUT_DIR / fname).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
