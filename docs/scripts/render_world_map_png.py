"""
Render the Shrouded Lands world map (hex tiles + labels) to a PNG.

Usage:
  python docs/scripts/render_world_map_png.py \
    --output /path/to/world-map.png

The script also writes a full-size map alongside the requested output with a
"-full" suffix (for example, world-map-full.png). In addition, it renders
small/full maps using the hex-white tiles with a "-white" suffix (for example,
world-map-white.png and world-map-white-full.png).

Requirements:
  - Playwright for Python: pip install playwright
  - Playwright browser binaries: python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


HEX_WIDTH = 30
HEX_HEIGHT = 26
HEX_X_STEP = 22.5
HEX_Y_STEP = 26
HEX_Y_OFFSET = 13

COLS = 52
ROWS = 34


def parse_simple_yaml_list(path: Path) -> list[dict[str, object]]:
    """Parse the simple list of dicts in world-map-labels.yml."""
    labels: list[dict[str, object]] = []
    current: dict[str, object] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("-"):
            if current:
                labels.append(current)
                current = {}
            line = line[1:].strip()
            if not line:
                continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith(("\"", "'")) and value.endswith(("\"", "'")):
            value = value[1:-1]
        else:
            try:
                value = int(value)
            except ValueError:
                pass
        current[key.strip()] = value

    if current:
        labels.append(current)

    return labels


def build_world_map_html(
    hex_dir: Path, labels_path: Path, stylesheet_path: Path
) -> str:
    tiles_markup = []
    for col in range(COLS):
        col_mod = col % 2
        for row in range(ROWS):
            left = col * HEX_X_STEP
            top = row * HEX_Y_STEP + (HEX_Y_OFFSET if col_mod == 1 else 0)
            col_code = f"{col:02d}"
            row_code = f"{row:02d}"
            hex_code = f"{col_code}-{row_code}"
            hex_path = hex_dir / f"hex-{hex_code}.svg"
            tiles_markup.append(
                (
                    "<div class=\"world-map__tile\" "
                    f"style=\"left: {left}px; top: {top}px;\">"
                    f"<img src=\"{hex_path.as_uri()}\" alt=\"{hex_code}\"></div>"
                )
            )

    labels = parse_simple_yaml_list(labels_path)
    label_markup = []
    for label in labels:
        col = int(label["col"])
        row = int(label["row"])
        col_mod = col % 2
        left = col * HEX_X_STEP + 15
        top = row * HEX_Y_STEP + 13 + (HEX_Y_OFFSET if col_mod == 1 else 0)
        label_type = label["type"]
        label_markup.append(
            (
                "<div class=\"world-map__label world-map__label--"
                f"{label_type}\" style=\"left: {left}px; top: {top}px;\">"
                f"{label['name']}"
                "</div>"
            )
        )

    width = HEX_WIDTH + HEX_X_STEP * (COLS - 1)
    height = HEX_HEIGHT + HEX_Y_STEP * (ROWS - 1) + HEX_Y_OFFSET

    stylesheet_uri = stylesheet_path.as_uri()

    return f"""
<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>World Map Render</title>
    <link rel=\"stylesheet\" href=\"{stylesheet_uri}\" />
  </head>
  <body class=\"world-map-page\">
    <div class=\"world-map-wrapper\">
      <div class=\"world-map\" style=\"width: {width}px; height: {height}px;\">
        {''.join(tiles_markup)}
        <div class=\"world-map__labels\">
          {''.join(label_markup)}
        </div>
      </div>
    </div>
  </body>
</html>
"""


def render_map(
    html: str,
    output_path: Path,
    viewport_width: int,
    viewport_height: int,
    timeout_ms: int,
    scale: float,
) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as temp_file:
        temp_file.write(html)
        temp_path = Path(temp_file.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                device_scale_factor=scale,
            )
            page = context.new_page()
            page.goto(temp_path.as_uri(), wait_until="load", timeout=timeout_ms)
            page.wait_for_load_state("load", timeout=timeout_ms)
            page.wait_for_function(
                "Array.from(document.images).every(img => img.complete)",
                timeout=timeout_ms,
            )
            map_element = page.locator(".world-map")
            map_element.screenshot(path=str(output_path))
            browser.close()
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the Shrouded Lands world map into a PNG."
    )
    parser.add_argument(
        "--output",
        default="docs/assets/world-map.png",
        help="Path to the PNG file to create.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=120_000,
        help="Timeout in milliseconds for page load and assets (default: 120000).",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Device scale factor for the screenshot (default: 1.0).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    hex_dir = repo_root / "docs" / "assets" / "hexes"
    hex_white_dir = repo_root / "docs" / "assets" / "hex-white"
    labels_path = repo_root / "docs" / "_data" / "world-map-labels.yml"
    stylesheet_path = repo_root / "docs" / "assets" / "style.css"

    if not hex_dir.exists():
        raise FileNotFoundError(f"Hex assets not found: {hex_dir}")
    if not hex_white_dir.exists():
        raise FileNotFoundError(f"Hex assets not found: {hex_white_dir}")
    if not labels_path.exists():
        raise FileNotFoundError(f"Labels file not found: {labels_path}")
    if not stylesheet_path.exists():
        raise FileNotFoundError(f"Stylesheet not found: {stylesheet_path}")


    html = build_world_map_html(hex_dir, labels_path, stylesheet_path)
    white_html = build_world_map_html(hex_white_dir, labels_path, stylesheet_path)
    width = HEX_WIDTH + HEX_X_STEP * (COLS - 1)
    height = HEX_HEIGHT + HEX_Y_STEP * (ROWS - 1) + HEX_Y_OFFSET
    viewport_width = math.ceil(width)
    viewport_height = math.ceil(height)

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    full_size_path = output_path.with_name(
        f"{output_path.stem}-full{output_path.suffix}"
    )
    white_output_path = output_path.with_name(
        f"{output_path.stem}-white{output_path.suffix}"
    )
    white_full_size_path = output_path.with_name(
        f"{output_path.stem}-white-full{output_path.suffix}"
    )

    render_map(
        html,
        output_path,
        viewport_width,
        viewport_height,
        args.timeout_ms,
        args.scale,
    )
    render_map(
        html,
        full_size_path,
        viewport_width,
        viewport_height,
        args.timeout_ms,
        1.0,
    )
    render_map(
        white_html,
        white_output_path,
        viewport_width,
        viewport_height,
        args.timeout_ms,
        args.scale,
    )
    render_map(
        white_html,
        white_full_size_path,
        viewport_width,
        viewport_height,
        args.timeout_ms,
        1.0,
    )

    print(f"Saved map to {output_path}")
    print(f"Saved full-size map to {full_size_path}")
    print(f"Saved white map to {white_output_path}")
    print(f"Saved white full-size map to {white_full_size_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
