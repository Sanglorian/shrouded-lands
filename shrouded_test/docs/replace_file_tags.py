import re
from pathlib import Path

# We assume the script lives in the same folder as _wiki
ROOT = Path(__file__).resolve().parent
WIKI_DIR = ROOT / "_wiki"

file_tag_pattern = re.compile(
    r"\[\[File:([^|\]]+)([^]]*)\]\]",
    re.IGNORECASE
)

def replace_file_tag(match):
    filename = match.group(1).strip()
    rest = match.group(2) or ""

    parts = [p.strip() for p in rest.split("|") if p.strip()]
    caption = parts[-1] if parts else ""

    safe_filename = filename.replace(" ", "_")
    url = f"/media/{safe_filename}"
    alt_text = caption if caption else filename

    return f"![{alt_text}]({url})"

def process_file(path: Path):
    text = path.read_text(encoding="utf-8")
    new_text = file_tag_pattern.sub(replace_file_tag, text)

    if new_text != text:
        print(f"Updated {path.name}")
        path.write_text(new_text, encoding="utf-8")

def main():
    if not WIKI_DIR.exists():
        print(f"ERROR: No _wiki directory found at: {WIKI_DIR}")
        return

    for md in WIKI_DIR.glob("*.md"):
        process_file(md)

if __name__ == "__main__":
    main()
