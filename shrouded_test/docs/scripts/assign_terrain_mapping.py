from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
MAPPING_CSV = ROOT / "terrain-mapping.csv"


def normalize_hex_code(code: str) -> str | None:
    cleaned = code.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace("-", ".")
    parts = cleaned.split(".")
    if len(parts) < 2:
        return None
    parts[0] = parts[0].zfill(2)
    parts[1] = parts[1].zfill(2)
    if len(parts) > 2:
        parts[2] = parts[2].zfill(2)
    return ".".join(parts)


def update_front_matter(text: str, terrain: str) -> tuple[str, bool]:
    if not text.startswith("---"):
        return text, False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text, False
    fm_raw = parts[1]
    body = parts[2].lstrip("\n")

    lines = fm_raw.splitlines()
    updated = False
    terrain_line = f"terrain: {terrain}"
    for idx, line in enumerate(lines):
        if line.startswith("terrain:"):
            if line.strip() != terrain_line:
                lines[idx] = terrain_line
                updated = True
            break
    else:
        lines.append(terrain_line)
        updated = True

    if not updated:
        return text, False

    fm_raw_new = "\n".join(lines).rstrip() + "\n"
    new_text = f"---\n{fm_raw_new}---\n{body}"
    return new_text, True


def main() -> int:
    if not MAPPING_CSV.exists():
        raise SystemExit(f"Missing terrain mapping CSV: {MAPPING_CSV}")

    mapping: dict[str, str] = {}
    with MAPPING_CSV.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            raw_hex = row.get("hex", "")
            terrain = (row.get("terrain") or "").strip()
            if not terrain:
                continue
            normalized = normalize_hex_code(raw_hex)
            if not normalized:
                continue
            mapping[normalized] = terrain

    updated_count = 0
    missing = []

    for hex_code, terrain in sorted(mapping.items()):
        wiki_path = WIKI_DIR / f"{hex_code}.md"
        if not wiki_path.exists():
            missing.append(hex_code)
            continue
        original = wiki_path.read_text(encoding="utf-8")
        updated_text, changed = update_front_matter(original, terrain)
        if changed:
            wiki_path.write_text(updated_text, encoding="utf-8")
            updated_count += 1

    print(f"Updated {updated_count} hex files.")
    if missing:
        print("Missing hex files:")
        for hex_code in missing:
            print(f"- {hex_code}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
