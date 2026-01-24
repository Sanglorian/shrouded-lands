import sys
import re
import os
from pathlib import Path

import yaml

YAML_DELIM = re.compile(r'^---\s*$')


def split_front_matter(text):
    """
    Split a Jekyll-style file into (front_matter_dict, body_text).
    If no front matter, returns ({}, original_text).
    """
    lines = text.splitlines()
    if not lines or not YAML_DELIM.match(lines[0]):
        return {}, text

    # find closing ---
    try:
        end_idx = next(
            i for i, line in enumerate(lines[1:], start=1)
            if YAML_DELIM.match(line)
        )
    except StopIteration:
        # malformed front matter, just treat whole thing as body
        return {}, text

    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx+1:])

    front = yaml.safe_load(fm_text) or {}
    return front, body


HEX_RE = re.compile(r'\b\d{2}\.\d{2}(?:\.\d{2})?\b')


def extract_image(body):
    """
    Extract first [[File:...]] reference and return (filename, body_without_tag).
    """
    m = re.search(r'\[\[File:([^|\]]+)', body)
    if not m:
        return None, body

    filename = m.group(1).strip()
    body = body.replace(m.group(0), '').lstrip()
    return filename, body


def extract_name(body):
    """
    Extract first ==Heading== as 'name'.
    Leaves the heading in the body (we'll convert it to markdown later).
    """
    m = re.search(r'^==\s*(.+?)\s*==\s*$', body, flags=re.M)
    if not m:
        return None
    return m.group(1).strip()


def extract_region(body):
    """
    Look for a line starting with 'Region: ...' (case-insensitive).
    Returns (region, body_without_that_line).
    """
    lines = body.splitlines()
    new_lines = []
    region = None

    for line in lines:
        m = re.search(r'^\s*Region:\s*(.+)\s*$', line, flags=re.I)
        if m and region is None:
            region = m.group(1).strip()
            # drop this line
        else:
            new_lines.append(line)

    return region, "\n".join(new_lines)


def strip_region_markup(region):
    if not region:
        return region

    cleaned = region.strip()
    cleaned = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", cleaned)
    cleaned = re.sub(r"\[\[([^\]]+)\]\]", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.+?)__", r"\1", cleaned)
    cleaned = re.sub(r"\*(.+?)\*", r"\1", cleaned)
    cleaned = re.sub(r"_(.+?)_", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def extract_neighbors(body):
    """
    Look for 'Connects to:' line and extract hex codes.
    Returns (neighbors_list, body_without_that_line).
    """
    lines = body.splitlines()
    new_lines = []
    neighbors = []

    for line in lines:
        if 'Connects to:' in line:
            # collect all hex-like tokens on that line
            neighbors.extend(HEX_RE.findall(line))
            # drop this line
        else:
            new_lines.append(line)

    return neighbors or None, "\n".join(new_lines)


def clean_html_noise(body):
    """
    Strip most of the Word/HTML noise, keep structure.
    """
    # Replace <p ...> and </p> with blank lines
    body = re.sub(r'<p[^>]*>', '\n\n', body, flags=re.I)
    body = re.sub(r'</p>', '\n\n', body, flags=re.I)

    # Replace <br> / <br/> with newlines
    body = re.sub(r'<br\s*/?>', '\n', body, flags=re.I)

    # Drop span tags but keep inner text
    body = re.sub(r'<span[^>]*>', '', body, flags=re.I)
    body = body.replace('</span>', '')

    # You can add more tag-stripping here if needed
    return body


def convert_headings(body):
    """
    Convert ==Heading== and ===Heading=== styles to markdown.
    """
    # === => ###
    body = re.sub(r'^===\s*(.+?)\s*===\s*$', r'### \1', body, flags=re.M)
    # == => ##
    body = re.sub(r'^==\s*(.+?)\s*==\s*$', r'## \1', body, flags=re.M)
    return body


def clean_categories(body):
    """
    Remove [[Category:...]] lines.
    """
    return re.sub(r'^\s*\[\[Category:[^\]]+\]\]\s*$', '', body, flags=re.M)


def fix_hooks_bullets(body):
    """
    Turn '-What ...' into '- What ...' etc.
    """
    # Lines starting with '-' and then a non-space: add a space
    body = re.sub(r'^-(\S)', r'- \1', body, flags=re.M)
    return body


def normalise_spacing(body):
    """
    Collapse ridiculous blank lines.
    """
    # Strip trailing spaces
    body = re.sub(r'[ \t]+$', '', body, flags=re.M)
    # Collapse 3+ blank lines to 2
    body = re.sub(r'\n{3,}', '\n\n', body)
    return body.strip() + "\n"


def process_file(src_path, dst_path):
    text = src_path.read_text(encoding='utf-8')
    front, body = split_front_matter(text)

    # 1) strip categories from body (they're already in front matter)
    body = clean_categories(body)

    # 2) extract image tag
    image, body = extract_image(body)

    # 3) extract region + neighbors
    region, body = extract_region(body)
    region = strip_region_markup(region)
    neighbors, body = extract_neighbors(body)

    # 4) clean HTML junk
    body = clean_html_noise(body)

    # 5) convert headings
    body = convert_headings(body)

    # 6) fix hooks bullets
    body = fix_hooks_bullets(body)

    # 7) normalise spacing
    body = normalise_spacing(body)

    # 8) infer 'name' from first heading if not present
    name = extract_name(body)

    # ---- update front matter ----
    front = dict(front)  # shallow copy

    if name and 'name' not in front:
        front['name'] = name

    if region and 'region' not in front:
        front['region'] = region

    if neighbors:
        # merge with existing or overwrite?
        front['neighbors'] = sorted(set(neighbors))

    if image and 'image' not in front:
        front['image'] = image

    # write out
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(front, sort_keys=False, allow_unicode=True).strip()
    out = f"---\n{fm_text}\n---\n\n{body}"
    dst_path.write_text(out, encoding='utf-8')


def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_wiki.py <src_dir> <dst_dir>")
        sys.exit(1)

    src_dir = Path(sys.argv[1])
    dst_dir = Path(sys.argv[2])

    if not src_dir.is_dir():
        print(f"Source dir not found: {src_dir}")
        sys.exit(1)

    for path in src_dir.rglob("*.md"):
        rel = path.relative_to(src_dir)
        dst_path = dst_dir / rel
        print(f"Converting {rel} -> {dst_path}")
        process_file(path, dst_path)


if __name__ == "__main__":
    main()
