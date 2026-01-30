from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "_wiki_raw"
WIKI_DIR = ROOT / "_wiki"


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
    fm_yaml = yaml.safe_dump(
        fm,
        sort_keys=False,
        allow_unicode=True
    ).strip()
    new_text = f"---\n{fm_yaml}\n---\n{body.lstrip()}"
    path.write_text(new_text, encoding="utf-8")


def main():
    for md in WIKI_DIR.glob("*.md"):
        raw_md = RAW_DIR / md.name
        if not raw_md.exists():
            print(f"Skipping {md.name}: no raw file")
            continue

        raw_text = raw_md.read_text(encoding="utf-8")
        _, raw_fm, _ = split_front_matter(raw_text)

        if "title" not in raw_fm:
            print(f"Skipping {md.name}: raw has no title")
            continue

        orig_title = raw_fm["title"]

        text = md.read_text(encoding="utf-8")
        _, fm, body = split_front_matter(text)
        if not fm:
            print(f"Skipping {md.name}: no front matter")
            continue

        old_title = fm.get("title")
        fm["title"] = orig_title

        write_page(md, fm, body)
        print(f"{md.name}: '{old_title}' -> '{orig_title}'")


if __name__ == "__main__":
    main()
