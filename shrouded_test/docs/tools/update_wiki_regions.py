#!/usr/bin/env python3
import sys
import re
from pathlib import Path

import yaml

YAML_DELIM = re.compile(r"^---\s*$")
REGION_RE = re.compile(r"(.*)Region:\s*(.+)")


def split_front_matter(text):
    lines = text.splitlines()
    if not lines or not YAML_DELIM.match(lines[0]):
        return {}, text

    try:
        end_idx = next(
            i for i, line in enumerate(lines[1:], start=1)
            if YAML_DELIM.match(line)
        )
    except StopIteration:
        return {}, text

    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])

    front = yaml.safe_load(fm_text) or {}
    return front, body


def extract_region(body):
    region = None
    new_lines = []

    for line in body.splitlines():
        match = REGION_RE.search(line)
        if match:
            if region is None:
                region = match.group(2).strip()
            prefix = match.group(1).rstrip()
            if prefix:
                new_lines.append(prefix)
            continue
        new_lines.append(line)

    return region, "\n".join(new_lines)


def update_file(path):
    text = path.read_text(encoding="utf-8")
    front, body = split_front_matter(text)

    region, body = extract_region(body)
    if region is None:
        return False

    front = dict(front)
    front["region"] = region

    fm_text = yaml.safe_dump(front, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{fm_text}\n---\n\n{body}\n"
    path.write_text(out, encoding="utf-8")
    return True


def main():
    if len(sys.argv) > 2:
        print("Usage: python update_wiki_regions.py [wiki_dir]")
        sys.exit(1)

    if len(sys.argv) == 2:
        wiki_dir = Path(sys.argv[1])
    else:
        wiki_dir = Path("_wiki")
    if not wiki_dir.is_dir():
        print(f"Wiki directory not found: {wiki_dir}")
        sys.exit(1)

    updated = 0
    for path in wiki_dir.rglob("*.md"):
        if update_file(path):
            print(f"Updated {path}")
            updated += 1

    print(f"Region updates applied to {updated} file(s).")


if __name__ == "__main__":
    main()
