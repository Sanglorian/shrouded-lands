from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
POI_MAPPING_CSV = ROOT / "poi-mapping.csv"

HEX_TITLE_RE = re.compile(r"^\d{2}\.\d{2}$")


def load_poi_mapping():
    mapping = {}
    with POI_MAPPING_CSV.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for row in reader:
            hex_code = (row.get("hex") or "").strip()
            poi_name = (row.get("poi") or "").strip()
            if not hex_code or not poi_name:
                continue
            mapping[hex_code] = poi_name
    return mapping


def update_front_matter(path: Path, poi_name: str) -> bool:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, flags=re.DOTALL)
    if not match:
        return False
    yaml_block, body = match.groups()

    new_poi_line = f'poi: "{poi_name}"'
    if "poi:" in yaml_block:
        yaml_block = re.sub(r"poi:.*", new_poi_line, yaml_block)
    else:
        yaml_block = f"{yaml_block}\n{new_poi_line}"

    new_content = f"---\n{yaml_block}\n---\n{body}"
    path.write_text(new_content, encoding="utf-8")
    return True


def main():
    if not POI_MAPPING_CSV.exists():
        raise RuntimeError(f"Missing {POI_MAPPING_CSV}")
    if not WIKI_DIR.exists():
        raise RuntimeError(f"Missing {WIKI_DIR}")

    mapping = load_poi_mapping()
    updates = 0

    for md in WIKI_DIR.glob("*.md"):
        if md.name.startswith("."):
            continue
        title = md.stem
        if not HEX_TITLE_RE.match(title):
            continue
        poi_name = mapping.get(title)
        if not poi_name:
            continue
        if update_front_matter(md, poi_name):
            updates += 1
            print(f"Updated {md.name} -> {poi_name}")

    print(f"Updated {updates} hex pages.")


if __name__ == "__main__":
    main()
