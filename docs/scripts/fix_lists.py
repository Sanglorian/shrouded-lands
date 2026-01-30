import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]   # docs/
WIKI = ROOT / "_wiki"

# regex for markers at start of a line (with optional indent)
PAT = re.compile(r'^(\s*)([*#;:])(?!\s)', re.MULTILINE)

def parse_fm(text):
    if not text.startswith('---'):
        return None, text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return None, text
    fm = parts[1]
    body = parts[2]
    return fm, body

def main():
    for f in WIKI.glob("*.md"):
        orig = f.read_text(encoding="utf-8")
        fm, body = parse_fm(orig)

        # Only modify body
        new_body = PAT.sub(r'\1\2 ', body)

        if fm is None:
            # no front matter
            f.write_text(new_body, encoding="utf-8")
        else:
            out = f"---{fm}---\n{new_body.lstrip()}"
            f.write_text(out, encoding="utf-8")

        print("Fixed lists in", f.name)

if __name__ == "__main__":
    main()
