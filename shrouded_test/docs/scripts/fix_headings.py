from pathlib import Path
import re

# docs/
ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"

# Match lines that start with "# " followed by another heading, e.g.:
# "# # Pirate Kings"  -> "# Pirate Kings"
# "# ## Subhexes"    -> "## Subhexes"
HEADING_RE = re.compile(r'^# (#+ .*)$', re.MULTILINE)

def main():
    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        new_text = HEADING_RE.sub(r'\1', text)
        if new_text != text:
            md.write_text(new_text, encoding="utf-8")
            print(f"Fixed headings in {md.name}")

if __name__ == "__main__":
    main()
