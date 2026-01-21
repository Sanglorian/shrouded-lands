from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "_wiki_raw"
WIKI_DIR = ROOT / "_wiki"

H1_RE = re.compile(r"^# (.+)$", re.MULTILINE)


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


def write_page(path: Path, fm: dict, body: str):
    fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    new_text = f"---\n{fm_yaml}\n---\n{body.lstrip()}"
    path.write_text(new_text, encoding="utf-8")


def main():
    for md in WIKI_DIR.glob("*.md"):
        raw_md = RAW_DIR / md.name
        if not raw_md.exists():
            print(f"Skipping {md.name}: no raw version")
            continue

        raw_text = raw_md.read_text(encoding="utf-8")
        _, raw_fm, raw_body = split_front_matter(raw_text)

        m = H1_RE.search(raw_body)
        if not m:
            print(f"Skipping {md.name}: raw has no H1 heading")
            continue

        raw_subtitle = m.group(1).strip()

        text = md.read_text(encoding="utf-8")
        _, fm, body = split_front_matter(text)
        if not fm:
            print(f"Skipping {md.name}: no front matter")
            continue

        old_subtitle = fm.get("subtitle")
        fm["subtitle"] = raw_subtitle

        write_page(md, fm, body)
        print(f"{md.name}: subtitle '{old_subtitle}' -> '{raw_subtitle}'")


if __name__ == "__main__":
    main()
