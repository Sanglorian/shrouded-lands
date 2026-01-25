from pathlib import Path
import csv
import re
import math
from typing import Optional
import yaml

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
OUT_DIR = ROOT / "assets" / "hexmaps"
TERRAIN_CSV = ROOT / "terrain.csv"
POI_CSV = ROOT / "poi.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

def split_front_matter(text: str):
    if not text.startswith("---"):
        return "", {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", {}, text
    fm_raw = parts[1]
    body = parts[2].lstrip("\n")
    fm = yaml.safe_load(fm_raw) or {}
    return fm_raw, fm, body

def is_hex_page(fm: dict) -> bool:
    cats = fm.get("categories") or []
    return any(c == "Category:Hex" for c in cats)

HEX_CODE_RE = re.compile(r"^\d{2}\.\d{2}(?:\.\d{2})?$")

def normalize_code(code: str) -> str:
    """Trim whitespace, strip weird punctuation."""
    return code.strip().strip("[]()")

def hex_slug_for_link(code: str) -> str:
    """
    For links:
    - 00.02      -> 00-02
    - 00.02.03   -> 00-02   (subhex pages live at 00-02)
    """
    parts = code.split(".")
    base = ".".join(parts[:2])
    return base.replace(".", "-")

def hex_slug_for_filename(code: str) -> str:
    """
    For SVG file names:
    - 00.02      -> 00-02
    - 00.02.03   -> 00-02-03
    This avoids collisions between hex and subhex pages.
    """
    return code.replace(".", "-")

def clean_neighbors(fm: dict, title: str):
    """Return up to 6 distinct neighbor codes (strings)."""
    raw_neighbors = fm.get("neighbors") or []
    seen = set()
    cleaned = []

    for n in raw_neighbors:
        if not isinstance(n, str):
            continue
        code = normalize_code(n)
        if not HEX_CODE_RE.match(code):
            continue
        if code == title:
            continue
        if code in seen:
            continue
        seen.add(code)
        cleaned.append(code)
        if len(cleaned) >= 6:
            break

    return cleaned


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
            color = (row[2] or "").strip() if len(row) > 2 else ""
            symbols[poi_name] = {
                "symbol": symbol,
                "color": color,
            }
    return symbols

def normalize_symbol(symbol: str) -> str:
    return symbol.replace("\ufe0f", "") + "\ufe0e"

def hex_points(cx, cy, r):
    """
    Flat-top hexagon.
    cx, cy = center
    r = radius
    """
    h = math.sqrt(3) * r / 2  # vertical offset from center to top/bottom edges
    # vertices starting at right, going counter-clockwise
    points = [
        (cx + r, cy),        # right
        (cx + r / 2, cy - h),
        (cx - r / 2, cy - h),
        (cx - r, cy),        # left
        (cx - r / 2, cy + h),
        (cx + r / 2, cy + h),
    ]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

def make_svg(
    title: str,
    neighbor_codes,
    center_fill: str,
    symbol: Optional[str],
    symbol_color: Optional[str],
    symbol_two: Optional[str],
    poi_symbol: Optional[str],
    poi_color: Optional[str],
) -> str:
    """
    title: the hex code for the current page, e.g. "26.01"
    neighbor_codes: list of hex codes, e.g. ["26.01.01", "24.02", ...]
                    max 6, already cleaned by clean_neighbors()
    """
    # Basic geometry
    hex_w = 80
    hex_h = 90
    pad = 10

    # Precomputed offsets for axial orientation
    # (center, N, NE, SE, S, SW, NW)
    positions = {
        "C":  (hex_w + pad, hex_h + pad),
        "N":  (hex_w + pad, pad),
        "NE": (2 * hex_w + 2 * pad, hex_h // 2 + pad),
        "SE": (2 * hex_w + 2 * pad, hex_h + hex_h // 2 + pad),
        "S":  (hex_w + pad, 2 * hex_h + pad),
        "SW": (pad, hex_h + hex_h // 2 + pad),
        "NW": (pad, hex_h // 2 + pad),
    }

    width = 3 * hex_w + 2 * pad
    height = 2 * hex_h + 2 * pad

    # Build a direction -> slug map from the neighbor list
    direction_order = ["N", "NE", "SE", "S", "SW", "NW"]
    dir_to_slug = {}

    for i, code in enumerate(neighbor_codes):
        if i >= len(direction_order):
            break
        dir_key = direction_order[i]
        # use link slug so sub-hexes (26.01.01) go to 26-01 etc.
        dir_to_slug[dir_key] = hex_slug_for_link(code)

    # ==========================================================
    # START SVG
    # ==========================================================
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    ]
    svg_parts.append(
        "<style>"
        "text { "
        "user-select: none; "
        "-webkit-user-select: none; "
        "-moz-user-select: none; "
        "-ms-user-select: none; "
        "}"
        "</style>"
    )


    def hex_points(x, y):
        return " ".join([
            f"{x + hex_w//2},{y}",
            f"{x + hex_w},{y + hex_h//3}",
            f"{x + hex_w},{y + 2*hex_h//3}",
            f"{x + hex_w//2},{y + hex_h}",
            f"{x},{y + 2*hex_h//3}",
            f"{x},{y + hex_h//3}",
        ])

    # ==========================================================
    # DRAW CENTER HEX
    # ==========================================================
    cx, cy = positions["C"]
    center_pts = hex_points(cx, cy)
    svg_parts.append(
        f'<polygon points="{center_pts}" fill="{center_fill}" stroke="#222" stroke-width="2"/>'
    )
    if symbol or symbol_two:
        base_x = cx + hex_w // 2
        base_y = cy + hex_h // 2
        base_size = 27
        if symbol and symbol_two:
            offset = base_size * 0.3
            primary_symbol = normalize_symbol(symbol)
            secondary_symbol = normalize_symbol(symbol_two)
            svg_parts.append(
                f'<text x="{base_x - offset}" y="{base_y + offset}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="{base_size}" font-family="sans-serif" '
                f'fill="{symbol_color or "#333333"}">{primary_symbol}</text>'
            )
            svg_parts.append(
                f'<text x="{base_x + offset}" y="{base_y - offset}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="{base_size * 2 / 3:.1f}" font-family="sans-serif" '
                f'fill="{symbol_color or "#333333"}">{secondary_symbol}</text>'
            )
        else:
            symbol_text = normalize_symbol(symbol or symbol_two)
            svg_parts.append(
                f'<text x="{base_x}" y="{base_y}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="{base_size}" font-family="sans-serif" '
                f'fill="{symbol_color or "#333333"}">{symbol_text}</text>'
            )
    if poi_symbol:
        base_x = cx + hex_w // 2
        base_y = cy + hex_h // 2
        poi_text = normalize_symbol(poi_symbol)
        poi_color_value = poi_color or "#000000"
        if not poi_color_value.startswith("#"):
            poi_color_value = f"#{poi_color_value}"
        svg_parts.append(
            f'<text x="{base_x}" y="{base_y}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="27" font-family="sans-serif" fill="{poi_color_value}">{poi_text}</text>'
        )
    label_y = cy + hex_h - 10
    svg_parts.append(
        f'<text x="{cx + hex_w//2}" y="{label_y}" '
        f'text-anchor="middle" dominant-baseline="alphabetic" '
        f'font-size="10" font-family="sans-serif">{title}</text>'
    )

    # ==========================================================
    # DRAW NEIGHBORS AROUND IT
    # ==========================================================
    for dir_key in ["N", "NE", "SE", "S", "SW", "NW"]:
        px, py = positions[dir_key]
        pts = hex_points(px, py)
        slug = dir_to_slug.get(dir_key)

        if slug:
            svg_parts.append(
                f'<a xlink:href="/wiki/{slug}/">'
                f'<polygon points="{pts}" fill="#ddeeff" stroke="#444" stroke-width="2"/>'
                f'</a>'
            )
        else:
            svg_parts.append(
                f'<polygon points="{pts}" fill="#eeeeee" stroke="#888" stroke-width="2"/>'
            )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)



def main():
    terrain_overrides = load_terrain_overrides()
    poi_symbols = load_poi_symbols()
    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm_raw, fm, body = split_front_matter(text)
        if not fm:
            continue
        if not is_hex_page(fm):
            continue

        title = str(fm.get("title") or "").strip()
        if not HEX_CODE_RE.match(title):
            # Not a numeric hex title, skip
            continue

        neighbors = clean_neighbors(fm, title)
        terrain = fm.get("terrain")
        override = terrain_overrides.get(terrain)

        center_fill = "#ffeecc"
        if override and override.get("hex_color"):
            center_fill = f"#{override['hex_color']}"
        symbol = override.get("symbol") if override else None
        symbol_two = override.get("symbol_two") if override else None
        symbol_color = (
            f"#{override['symbol_color']}" if override and override.get("symbol_color") else None
        )
        poi_name = (fm.get("poi") or "").strip() if isinstance(fm.get("poi"), str) else ""
        poi_entry = poi_symbols.get(poi_name) if poi_name else None
        poi_symbol = poi_entry.get("symbol") if poi_entry else None
        poi_color = poi_entry.get("color") if poi_entry else None

        svg = make_svg(
            title,
            neighbors,
            center_fill,
            symbol,
            symbol_color,
            symbol_two,
            poi_symbol,
            poi_color,
        )

        fname = f"hex-{hex_slug_for_filename(title)}.svg"
        out_path = OUT_DIR / fname
        out_path.write_text(svg, encoding="utf-8")
        print(f"Wrote {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
