from pathlib import Path
import math
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
OUT_DIR = ROOT / "assets" / "hexes"

OUT_DIR.mkdir(parents=True, exist_ok=True)

HEX_TITLE_RE = re.compile(r"^(\d{2})\.(\d{2})(?:\.\d{2})?$")

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

def collect_existing_hexes():
    existing = set()
    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm_raw, fm, body = split_front_matter(text)
        title = str(fm.get("title") or "").strip()
        m = HEX_TITLE_RE.match(title)
        if not m:
            continue
        base_code = f"{m.group(1)}.{m.group(2)}"
        existing.add(base_code)
    return existing

def flat_hex_points(cx, cy, r):
    """
    Flat-top regular hexagon:
    Top and bottom edges are horizontal.
    """
    h = (math.sqrt(3) * r) / 2.0  # vertical offset from center to top/bottom edges

    # Start at top-left corner, go clockwise:
    # 1. top-left
    # 2. top-right
    # 3. right
    # 4. bottom-right
    # 5. bottom-left
    # 6. left
    pts = [
        (cx - r / 2.0, cy - h),
        (cx + r / 2.0, cy - h),
        (cx + r,       cy),
        (cx + r / 2.0, cy + h),
        (cx - r / 2.0, cy + h),
        (cx - r,       cy),
    ]
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def make_svg(code: str, has_page: bool) -> str:
    # code like "10.09"
    x_str, y_str = code.split(".")
    slug = f"{x_str}-{y_str}"

    # Hex geometry
    r = 40  # "radius" to left/right corners
    h = (math.sqrt(3) * r) / 2.0

    # Add a little padding around the hex
    pad = 10
    width = int(2 * r + 2 * pad)
    height = int(2 * h + 2 * pad)

    cx = width / 2.0
    cy = height / 2.0

    points = flat_hex_points(cx, cy, r)

    # Different fill for hexes that *do* have a page vs blanks
    fill = "#ffdca8" if has_page else "#eeeeee"
    stroke = "#333333"

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <a xlink:href="/wiki/{slug}/">
    <polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
    <text x="{cx}" y="{cy}" text-anchor="middle" dominant-baseline="middle"
          font-size="14" font-family="system-ui, sans-serif">{code}</text>
  </a>
</svg>
"""


def main():
    existing = collect_existing_hexes()
    print(f"Found {len(existing)} existing hex pages.")

    for x in range(45):   # 00–44
        for y in range(30):  # 00–29
            code = f"{x:02d}.{y:02d}"
            has_page = code in existing
            svg = make_svg(code, has_page)
            fname = f"hex-{x:02d}-{y:02d}.svg"
            out_path = OUT_DIR / fname
            out_path.write_text(svg, encoding="utf-8")
            # Optional: uncomment if you want spammy output
            # print(f"Wrote {out_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
