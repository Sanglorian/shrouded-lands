import os
from pathlib import Path

import yaml  # pip install pyyaml if you don't have it

ROOT = Path(__file__).resolve().parents[1]   # points to docs/
WIKI_DIR = ROOT / "_wiki"

def process_file(path: Path):
    text = path.read_text(encoding="utf-8")

    if not text.lstrip().startswith("---"):
        return  # no front matter

    # Find front matter block (between the first two --- lines)
    lines = text.splitlines(keepends=True)
    if not lines[0].strip() == "---":
        return

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return

    frontmatter = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1:])

    try:
        data = yaml.safe_load(frontmatter) or {}
    except Exception as e:
        print(f"Skipping {path} (YAML error: {e})")
        return

    title = str(data.get("title", ""))

    if not title.startswith("Category:"):
        return  # not a category page

    # Set layout
    old_layout = data.get("layout")
    if old_layout == "category_page":
        return  # already done

    data["layout"] = "category_page"
    print(f"Updated layout in {path} (was {old_layout})")

    new_front = "---\n" + yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True
    ) + "---\n"

    path.write_text(new_front + body, encoding="utf-8")


def main():
    for md in WIKI_DIR.glob("*.md"):
        process_file(md)


if __name__ == "__main__":
    main()
