from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

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

def process_file(path: Path):
    text = path.read_text(encoding="utf-8")
    fm_raw, fm, body = split_front_matter(text)
    if not fm:
        return

    if not is_hex_page(fm):
        return

    lines = body.splitlines()
    heading_idx = None
    heading_text = None

    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            heading_text = m.group(2).strip()
            heading_idx = i
            break

    if heading_idx is None or not heading_text:
        return  # no heading found, nothing to do

    # If you want to drop a leading "The ", uncomment below:
    # if heading_text.lower().startswith("the "):
    #     heading_text = heading_text[4:]

    # Update title in front matter
    fm["title"] = heading_text

    # Remove that heading line
    del lines[heading_idx]

    # Optionally also remove a blank line immediately after
    if heading_idx < len(lines) and lines[heading_idx].strip() == "":
        del lines[heading_idx]

    new_body = "\n".join(lines).rstrip() + "\n"

    fm_yaml = yaml.safe_dump(
        fm,
        sort_keys=False,
        allow_unicode=True
    ).strip()

    new_text = f"---\n{fm_yaml}\n---\n{new_body}"
    path.write_text(new_text, encoding="utf-8")
    print(f"Updated title from first heading in {path.name} -> '{heading_text}'")

def main():
    for md in WIKI_DIR.glob("*.md"):
        process_file(md)

if __name__ == "__main__":
    main()
