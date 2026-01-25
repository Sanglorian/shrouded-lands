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
LINEWORK_YAML = ROOT / "_data" / "hex-lines.yml"

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
    fm = parse_front_matter(fm_raw)
    return fm_raw, fm, body


def parse_front_matter(fm_raw: str) -> dict:
    data = {}
    current_list_key = None
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("- "):
            if current_list_key is None:
                continue
            item = line[2:].strip()
            data.setdefault(current_list_key, []).append(strip_quotes(item))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            current_list_key = key
            data[key] = []
            continue
        current_list_key = None
        data[key] = strip_quotes(value)
    return data


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


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

def load_hex_linework():
    if not LINEWORK_YAML.exists():
        return {}
    data = yaml.safe_load(LINEWORK_YAML.read_text(encoding="utf-8")) or {}
    aliases = data.get("direction_aliases") or {}
    entries = data.get("entries") or []
    linework = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        hex_code = (entry.get("hex") or "").strip()
        path = (entry.get("path") or "").strip()
        if not hex_code or not path:
            continue
        raw_tokens = [token.strip() for token in path.split("->") if token.strip()]
        path_tokens = [aliases.get(token, token) for token in raw_tokens]
        linework.setdefault(hex_code, []).append(
            {
                "layer": (entry.get("layer") or "").strip(),
                "color": (entry.get("color") or "").strip() or "#000000",
                "path_tokens": path_tokens,
            }
        )
    return linework

# === HEX GEOMETRY ===

def flat_hex_vertices(cx, cy, r):
    """Flat-top regular hexagon (top/bottom edges horizontal)."""
    h = (math.sqrt(3) * r) / 2.0

    return [
        (cx - r / 2.0, cy - h),  # top-left
        (cx + r / 2.0, cy - h),  # top-right
        (cx + r,       cy),      # right
        (cx + r / 2.0, cy + h),  # bottom-right
        (cx - r / 2.0, cy + h),  # bottom-left
        (cx - r,       cy),      # left
    ]

def flat_hex_points(cx, cy, r):
    """Flat-top regular hexagon (top/bottom edges horizontal)."""
    pts = flat_hex_vertices(cx, cy, r)
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
    linework: list[dict],
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
    vertices = flat_hex_vertices(cx, cy, r)
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in vertices)

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

    top_left, top_right, right, bottom_right, bottom_left, left = vertices
    anchors = {
        "Top": ((top_left[0] + top_right[0]) / 2.0, (top_left[1] + top_right[1]) / 2.0),
        "TopRight": top_right,
        "Right": right,
        "BottomRight": bottom_right,
        "Bottom": ((bottom_left[0] + bottom_right[0]) / 2.0, (bottom_left[1] + bottom_right[1]) / 2.0),
        "BottomLeft": bottom_left,
        "Left": left,
        "TopLeft": top_left,
        "Center": (cx, cy),
    }

    linework_markup = ""
    for item in linework:
        tokens = item.get("path_tokens") or []
        coords = [anchors.get(token) for token in tokens if anchors.get(token)]
        if len(coords) < 2:
            continue
        path_parts = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
        path_parts.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
        linework_markup += (
            f'<path d="{" ".join(path_parts)}" '
            f'stroke="{item.get("color") or "#000000"}" stroke-width="2" '
            f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    label_y = height - 6.0
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width:.2f}" height="{height:.2f}" viewBox="0 0 {width:.2f} {height:.2f}">
  {link_open}
    <polygon points="{points}" fill="{fill_color}" stroke="{stroke}" stroke-width="2"/>
    {linework_markup}
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
    hex_linework = load_hex_linework()
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

            linework = hex_linework.get(code, [])
            svg = make_svg(code, has_page, fill_color, symbol, symbol_color, symbol_two, poi_symbol, linework)
            fname = f"hex-{x:02d}-{y:02d}.svg"
            (OUT_DIR / fname).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
