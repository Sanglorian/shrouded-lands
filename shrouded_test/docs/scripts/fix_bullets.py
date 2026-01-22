from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]  # docs/
WIKI_DIR = ROOT / "_wiki"

# Match lines where:
#   - optional leading spaces
#   - a single * or -
#   - immediately followed by a non-space character
BULLET_RE = re.compile(r'^(\s*)([*-])(\S.*)$')

def split_front_matter(text: str):
    """Return (front_matter_block, body_text)."""
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    fm_block = "---" + parts[1] + "---\n"
    body = parts[2].lstrip("\n")
    return fm_block, body

def fix_body(body: str):
    lines = body.splitlines(keepends=True)
    out = []
    changed = False

    for line in lines:
        m = BULLET_RE.match(line)
        if m:
            indent, bullet, rest = m.groups()
            # Insert a space after the bullet
            new_line = f"{indent}{bullet} {rest}"
            out.append(new_line)
            if new_line != line:
                changed = True
        else:
            out.append(line)

    return "".join(out), changed

def main():
    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm_block, body = split_front_matter(text)
        new_body, changed = fix_body(body)
        if changed:
            md.write_text(fm_block + new_body, encoding="utf-8")
            print(f"Fixed bullets in {md.name}")

if __name__ == "__main__":
    main()
