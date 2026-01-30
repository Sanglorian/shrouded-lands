from pathlib import Path
import csv
import math
import re
from typing import Optional
import yaml

from emoji_to_path import char_to_svg_path  # NEW: convert emoji glyphs to SVG paths

# === CONFIG ===

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
OUT_DIR = ROOT / "assets" / "hexes"
OUT_DIR_WHITE = ROOT / "assets" / "hex-white"
TERRAIN_CSV = ROOT / "terrain.csv"
POI_CSV = ROOT / "poi.csv"
LINEWORK_YAML = ROOT / "_data" / "hex-lines.yml"
HEX_TERRAIN_YAML = ROOT / "_data" / "hex-terrain.yml"

OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR_WHITE.mkdir(parents=True, exist_ok=True)

# Fonts for glyph-as-path rendering (Noto / OpenMoji)
FONTS_DIR = ROOT / "fonts"
NOTO_EMOJI_FONT = FONTS_DIR / "NotoEmoji-Regular.ttf"
OPENMOJI_BLACK_FONT = FONTS_DIR / "OpenMoji-black-glyf.ttf"

HEX_TITLE_RE = re.compile(r"^(\d{2})\.(\d{2})(?:\.\d{2})?$")
HEX_CODE_RE = re.compile(r"(\d{2})\.(\d{2})")


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
        "color_hex": "#RRGGBB" or None,
        "terrain": ...,
        "poi": ...
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
    """
    Load terrain.csv with optional font columns:

      terrain,hex-color,symbol-color,symbol,symbol-two,symbol-font,symbol-two-font
    """
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
                # optional per-symbol font selectors: "system", "noto", "openmoji"
                "symbol_font": (row.get("symbol-font") or "").strip(),
                "symbol_two_font": (row.get("symbol-two-font") or "").strip(),
            }
        return overrides


def load_poi_symbols():
    """
    Load poi.tsv (tab-separated) with optional font column:

      symbol<TAB>poi_name<TAB>color_hex<TAB>font

    font can be "system", "noto", "openmoji". Blank -> system.
    """
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
            font = (row[3] or "").strip() if len(row) > 3 else ""
            symbols[poi_name] = {
                "symbol": symbol,
                "color": color,
                "font": font,
            }
    return symbols


def normalize_symbol(symbol: str) -> str:
    """
    Original behavior: strip U+FE0F and add U+FE0E to force text-style emoji.
    """
    return symbol.replace("\ufe0f", "") + "\ufe0e"


def render_segment_text(text: str, center_x: float, baseline_y: float, size: float, color: str) -> str:
    font_family = '"Aptos", "Segoe UI", system-ui, sans-serif'
    return (
        f'<text x="{center_x:.2f}" y="{baseline_y:.2f}" text-anchor="middle" '
        f'dominant-baseline="alphabetic" font-size="{size:.2f}" '
        f'font-family="{font_family}" fill="{color}">{text}</text>'
    )


def parse_hex_code(value: str) -> Optional[tuple[int, int]]:
    match = HEX_TITLE_RE.match(value.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def edge_direction(q: int, r: int, neighbor_q: int, neighbor_r: int) -> Optional[str]:
    if neighbor_q == q and neighbor_r == r - 1:
        return "Top"
    if neighbor_q == q and neighbor_r == r + 1:
        return "Bottom"
    if neighbor_q == q + 1:
        if q % 2 == 0:
            if neighbor_r == r - 1:
                return "TopRight"
            if neighbor_r == r:
                return "BottomRight"
        else:
            if neighbor_r == r:
                return "TopRight"
            if neighbor_r == r + 1:
                return "BottomRight"
    if neighbor_q == q - 1:
        if q % 2 == 0:
            if neighbor_r == r - 1:
                return "TopLeft"
            if neighbor_r == r:
                return "BottomLeft"
        else:
            if neighbor_r == r:
                return "TopLeft"
            if neighbor_r == r + 1:
                return "BottomLeft"
    return None


def opposite_edge(direction: str) -> str:
    opposites = {
        "Top": "Bottom",
        "TopRight": "BottomLeft",
        "BottomRight": "TopLeft",
        "Bottom": "Top",
        "BottomLeft": "TopRight",
        "TopLeft": "BottomRight",
    }
    return opposites.get(direction, direction)


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
        edge_spec = (entry.get("edge") or "").strip()
        if hex_code and path:
            raw_tokens = [token.strip() for token in path.split("->") if token.strip()]
            path_tokens = [aliases.get(token, token) for token in raw_tokens]
            linework.setdefault(hex_code, []).append(
                {
                    "kind": "path",
                    "layer": (entry.get("layer") or "").strip(),
                    "color": (entry.get("color") or "").strip() or "#000000",
                    "path_tokens": path_tokens,
                }
            )
            continue
        if edge_spec:
            codes = HEX_CODE_RE.findall(edge_spec)
            if len(codes) != 2:
                continue
            start = f"{codes[0][0]}.{codes[0][1]}"
            end = f"{codes[1][0]}.{codes[1][1]}"
            start_coords = parse_hex_code(start)
            end_coords = parse_hex_code(end)
            if not start_coords or not end_coords:
                continue
            direction = edge_direction(start_coords[0], start_coords[1], end_coords[0], end_coords[1])
            if not direction:
                continue
            color = (entry.get("color") or "").strip() or "#000000"
            layer = (entry.get("layer") or "").strip()
            linework.setdefault(start, []).append(
                {
                    "kind": "edge",
                    "layer": layer,
                    "color": color,
                    "edge": direction,
                }
            )
            linework.setdefault(end, []).append(
                {
                    "kind": "edge",
                    "layer": layer,
                    "color": color,
                    "edge": opposite_edge(direction),
                }
            )
    return linework


def load_hex_terrain_map():
    if not HEX_TERRAIN_YAML.exists():
        return {}
    data = yaml.safe_load(HEX_TERRAIN_YAML.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    terrain_map = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        hex_code = (entry.get("hex") or "").strip()
        terrain = (entry.get("terrain") or "").strip()
        if hex_code and terrain:
            terrain_map[hex_code] = terrain
    return terrain_map


# === FONT / GLYPH HELPERS ===

def normalize_font_choice(raw: str) -> str:
    """
    Normalize a raw font choice ("system", "noto", "open", "openmoji", etc.)
    into one of: "system", "noto", "openmoji".
    Blank or unknown -> "system".
    """
    if not raw:
        return "system"
    v = raw.strip().lower()
    if v.startswith("noto"):
        return "noto"
    if v.startswith("open"):
        return "openmoji"
    if v == "system":
        return "system"
    return "system"


def base_char_for_font(s: str) -> str:
    """
    Remove variation selectors and return the first base character,
    for use when looking up a glyph in a font.
    """
    if not s:
        return s
    cleaned = s.replace("\ufe0f", "").replace("\ufe0e", "")
    return cleaned[0] if cleaned else s[0]


def render_symbol_glyph(
    symbol: str,
    font_choice: str,
    x: float,
    y: float,
    size: float,
    color: str,
    opacity_attr: str,
    outline_color: Optional[str] = None,
    outline_width: Optional[float] = None,
) -> str:
    """
    Render a single glyph either as:
      - system text (normalize_symbol + system-ui), or
      - SVG path from Noto/OpenMoji via char_to_svg_path.

    x, y: logical "centre" of the glyph
    size: approximate visual size (similar to font-size)
    """
    if not symbol:
        return ""

    fc = normalize_font_choice(font_choice)

    if fc == "system":
        symbol_text = normalize_symbol(symbol)
        outline_attr = ""
        if outline_color and outline_width:
            outline_attr = (
                f' stroke="{outline_color}" stroke-width="{outline_width}" '
                'paint-order="stroke fill" stroke-linejoin="round"'
            )
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{size}" '
            f'font-family="system-ui, sans-serif" fill="{color}"{opacity_attr}{outline_attr}>'
            f'{symbol_text}</text>'
        )

    # Path sources (ALWAYS produce a list)
    if fc == "noto":
        font_paths = [NOTO_EMOJI_FONT]
    elif fc == "openmoji":
        font_paths = [OPENMOJI_BLACK_FONT]
    else:
        font_paths = [NOTO_EMOJI_FONT, OPENMOJI_BLACK_FONT]

    base_ch = base_char_for_font(symbol)

    def try_font(font_choice: Path) -> Optional[str]:
        if not font_choice.exists():
            return None
        try:
            return char_to_svg_path(base_ch, font_choice, target_px=size)
        except Exception:
            return None

    d = None
    for font_path in font_paths:
        d = try_font(font_path)
        if d:
            break
    if not d:
        symbol_text = normalize_symbol(symbol)
        outline_attr = ""
        if outline_color and outline_width:
            outline_attr = (
                f' stroke="{outline_color}" stroke-width="{outline_width}" '
                'paint-order="stroke fill" stroke-linejoin="round"'
            )
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="{size}" '
            f'font-family="system-ui, sans-serif" fill="{color}"{opacity_attr}{outline_attr}>'
            f'{symbol_text}</text>'
        )

    # Approximate centering:
    tx = x - size * 0.5
    ty = y + size * 0.4

    outline_attr = ""
    if outline_color and outline_width:
        outline_attr = (
            f' stroke="{outline_color}" stroke-width="{outline_width}" '
            'paint-order="stroke fill" stroke-linejoin="round" stroke-linecap="round"'
        )
    return (
        f'<g transform="translate({tx:.1f},{ty:.1f})">'
        f'<path d="{d}" fill="{color}"{opacity_attr}{outline_attr} />'
        f'</g>'
    )


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
    fill_opacity: Optional[float],
    symbol: Optional[str],
    symbol_color: Optional[str],
    symbol_two: Optional[str],
    symbol_opacity: Optional[float],
    poi_symbol: Optional[str],
    poi_color: Optional[str],
    linework: list[dict],
    symbol_font: Optional[str] = None,
    symbol_two_font: Optional[str] = None,
    poi_font: Optional[str] = None,
    show_border: bool = True,
    show_label: bool = True,
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

    symbol_opacity_attr = f' fill-opacity="{symbol_opacity:.2f}"' if symbol_opacity is not None else ""

    # Default colours and font choices
    glyph_color = symbol_color or "#333333"
    primary_font_choice = normalize_font_choice(symbol_font or "")
    secondary_font_choice = normalize_font_choice(symbol_two_font or symbol_font or "")
    poi_font_choice = normalize_font_choice(poi_font or "")

    symbol_markup = ""
    if symbol or symbol_two:
        base_size = 24
        if symbol and symbol_two:
            offset = base_size * 0.3
            # Primary at bottom-left-ish
            symbol_markup += render_symbol_glyph(
                symbol,
                primary_font_choice,
                cx - offset,
                cy + offset,
                base_size,
                glyph_color,
                symbol_opacity_attr,
            )
            # Secondary at top-right-ish, slightly smaller
            symbol_markup += render_symbol_glyph(
                symbol_two,
                secondary_font_choice,
                cx + offset,
                cy - offset,
                base_size * 2.0 / 3.0,
                glyph_color,
                symbol_opacity_attr,
            )
        else:
            active_symbol = symbol or symbol_two
            active_font_choice = primary_font_choice if symbol else secondary_font_choice
            symbol_markup = render_symbol_glyph(
                active_symbol,
                active_font_choice,
                cx,
                cy,
                base_size,
                glyph_color,
                symbol_opacity_attr,
            )

    poi_markup = ""
    if poi_symbol:
        poi_color_value = poi_color or "#000000"
        if not poi_color_value.startswith("#"):
            poi_color_value = f"#{poi_color_value}"
        poi_markup = render_symbol_glyph(
            poi_symbol,
            poi_font_choice,
            cx,
            cy - 6,
            24,
            poi_color_value,
            "",  # no separate opacity for POIs currently
            outline_color="#ffffff",
            outline_width=2,
        )

    top_left, top_right, right, bottom_right, bottom_left, left = vertices

    def midpoint(a, b):
        return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)

    anchors = {
        "Top": ((top_left[0] + top_right[0]) / 2.0, (top_left[1] + top_right[1]) / 2.0),
        "TopRight": midpoint(top_right, right),
        "Right": right,
        "BottomRight": midpoint(right, bottom_right),
        "Bottom": ((bottom_left[0] + bottom_right[0]) / 2.0, (bottom_left[1] + bottom_right[1]) / 2.0),
        "BottomLeft": midpoint(bottom_left, left),
        "Left": left,
        "TopLeft": midpoint(left, top_left),
        "Center": (cx, cy),
    }

    edge_segments = {
        "Top": (top_left, top_right),
        "TopRight": (top_right, right),
        "BottomRight": (right, bottom_right),
        "Bottom": (bottom_right, bottom_left),
        "BottomLeft": (bottom_left, left),
        "TopLeft": (left, top_left),
    }

    linework_markup = ""
    for item in linework:
        kind = item.get("kind") or "path"
        if kind == "edge":
            edge_name = item.get("edge")
            segment = edge_segments.get(edge_name)
            if not segment:
                continue
            (sx, sy), (ex, ey) = segment
            path_parts = [f"M {sx:.1f} {sy:.1f}", f"L {ex:.1f} {ey:.1f}"]
        else:
            tokens = item.get("path_tokens") or []
            coords = [anchors.get(token) for token in tokens if anchors.get(token)]
            if len(coords) < 2:
                continue
            path_parts = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
            path_parts.extend(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
        linework_markup += (
            f'<path d="{" ".join(path_parts)}" '
            f'stroke="{item.get("color") or "#000000"}" stroke-width="4" '
            f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    label_markup = ""
    if show_label:
        label_y = height - 6.0
        label_markup = render_segment_text(code, cx, label_y, 8.5, "#222222")
    fill_opacity_attr = f' fill-opacity="{fill_opacity:.2f}"' if fill_opacity is not None else ""
    stroke_attr = f' stroke="{stroke}" stroke-width="2"' if show_border else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width:.2f}" height="{height:.2f}" viewBox="0 0 {width:.2f} {height:.2f}">
  {link_open}
    <polygon points="{points}" fill="{fill_color}"{fill_opacity_attr}{stroke_attr}/>
    {symbol_markup}
    {linework_markup}
    {poi_markup}
    {label_markup}
  {link_close}
</svg>
"""


# === MAIN ===

def main():
    hex_meta = collect_hex_metadata()
    terrain_overrides = load_terrain_overrides()
    poi_symbols = load_poi_symbols()
    hex_linework = load_hex_linework()
    hex_terrain_map = load_hex_terrain_map()
    print(f"Found {len(hex_meta)} existing hex pages.")

    for x in range(52):     # 00–51
        for y in range(34): # 00–33
            code = f"{x:02d}.{y:02d}"
            meta = hex_meta.get(code)

            if meta:
                has_page = True
                fill_color = meta.get("color_hex") or "#ffdca8"
                terrain = meta.get("terrain")
                poi_name = (meta.get("poi") or "").strip() if isinstance(meta.get("poi"), str) else ""
                override = terrain_overrides.get(terrain)
                use_terrain_fallback = False
            else:
                has_page = False
                fill_color = "#eeeeee"
                poi_name = ""
                terrain = hex_terrain_map.get(code)
                override = terrain_overrides.get(terrain) if terrain else None
                use_terrain_fallback = bool(terrain)

            if override:
                fill_color = f"#{override['hex_color']}" if override["hex_color"] else fill_color
                symbol = override.get("symbol")
                symbol_two = override.get("symbol_two")
                symbol_color = f"#{override['symbol_color']}" if override["symbol_color"] else None
                symbol_font = override.get("symbol_font")
                symbol_two_font = override.get("symbol_two_font")
            else:
                symbol = None
                symbol_two = None
                symbol_color = None
                symbol_font = None
                symbol_two_font = None

            fill_opacity = 0.5 if use_terrain_fallback else None
            symbol_opacity = 0.5 if use_terrain_fallback else None

            poi_entry = poi_symbols.get(poi_name) if poi_name else None
            poi_symbol = poi_entry.get("symbol") if poi_entry else None
            poi_color = poi_entry.get("color") if poi_entry else None
            poi_font = poi_entry.get("font") if poi_entry else None

            linework = hex_linework.get(code, [])
            svg = make_svg(
                code,
                has_page,
                fill_color,
                fill_opacity,
                symbol,
                symbol_color,
                symbol_two,
                symbol_opacity,
                poi_symbol,
                poi_color,
                linework,
                symbol_font=symbol_font,
                symbol_two_font=symbol_two_font,
                poi_font=poi_font,
            )
            fname = f"hex-{x:02d}-{y:02d}.svg"
            (OUT_DIR / fname).write_text(svg, encoding="utf-8")
            svg_white = make_svg(
                code,
                has_page,
                fill_color,
                fill_opacity,
                symbol,
                symbol_color,
                symbol_two,
                symbol_opacity,
                poi_symbol,
                poi_color,
                linework,
                symbol_font=symbol_font,
                symbol_two_font=symbol_two_font,
                poi_font=poi_font,
                show_border=False,
                show_label=False,
            )
            (OUT_DIR_WHITE / fname).write_text(svg_white, encoding="utf-8")


if __name__ == "__main__":
    main()
