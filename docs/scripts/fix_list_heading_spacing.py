from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]   # docs/
WIKI_DIR = ROOT / "_wiki"

def needs_blank(prev_line: str, curr_line: str) -> bool:
    """Return True if we should insert a blank line before curr_line."""
    if not curr_line.lstrip().startswith("#"):
        return False

    # If previous line is empty, we're already fine
    if prev_line.strip() == "":
        return False

    stripped = prev_line.lstrip()

    # Bullet list items: * or -
    if stripped.startswith("* ") or stripped.startswith("- "):
        return True

    # Numbered list items: 1. Foo, 2. Bar, etc.
    if re.match(r"^\d+\.\s", stripped):
        return True

    return False

def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return False

    new_lines = [lines[0]]
    changed = False

    for i in range(1, len(lines)):
        prev = new_lines[-1]
        curr = lines[i]

        if needs_blank(prev, curr):
            new_lines.append("")  # insert blank line
            changed = True

        new_lines.append(curr)

    if changed:
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return changed

def main():
    for md in WIKI_DIR.glob("*.md"):
        if fix_file(md):
            print(f"Fixed spacing in {md.name}")

if __name__ == "__main__":
    main()
