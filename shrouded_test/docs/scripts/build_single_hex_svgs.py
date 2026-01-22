from pathlib import Path
import math
import re
import yaml

# === CONFIG ===

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
OUT_DIR = ROOT / "assets" / "hexes"

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
        }
    return meta


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

def make_svg(code: str, has_page: bool, fill_color: str) -> str:
    # code like "10.09"
    x_str, y_str = code.split(".")
    slug = f"{x_str}-{y_str}"

    # Hex geometry
    r = 40
    h = (math.sqrt(3) * r) / 2.0

    pad = 10
    width = int(2 * r + 2 * pad)
    height = int(2 * h + 2 * pad)

    cx = width / 2.0
    cy = height / 2.0
    points = flat_hex_points(cx, cy, r)

    stroke = "#333333"

    if has_page:
        link_open = f'<a xlink:href="/wiki/{slug}/">'
        link_close = "</a>"
    else:
        link_open = ""
        link_close = ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  {link_open}
    <polygon points="{points}" fill="{fill_color}" stroke="{stroke}" stroke-width="2"/>
    <text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="middle"
          font-size="14" font-family="system-ui, sans-serif">{code}</text>
  {link_close}
</svg>
"""


# === MAIN ===

def main():
    hex_meta = collect_hex_metadata()
    print(f"Found {len(hex_meta)} existing hex pages.")

    for x in range(45):     # 00–44
        for y in range(30): # 00–29
            code = f"{x:02d}.{y:02d}"
            meta = hex_meta.get(code)

            if meta:
                has_page = True
                fill_color = meta.get("color_hex") or "#ffdca8"
            else:
                has_page = False
                fill_color = "#eeeeee"

            svg = make_svg(code, has_page, fill_color)
            fname = f"hex-{x:02d}-{y:02d}.svg"
            (OUT_DIR / fname).write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
