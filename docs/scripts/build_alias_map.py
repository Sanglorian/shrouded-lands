import re
import os
import yaml
from collections import defaultdict

WIKI_DIR = "_wiki"           # directory with your .md wiki pages
DATA_DIR = "_data"
ALIASES_YML = os.path.join(DATA_DIR, "aliases.yml")

REDIRECT_RE = re.compile(r'^#REDIRECT\s*\[\[([^\]]+)\]\]', re.IGNORECASE)

def normalize(name: str) -> str:
    """Normalize a wiki title / alias for matching."""
    return name.strip().replace("_", " ").lower()

def read_front_matter_and_body(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_text = parts[1]
    body = parts[2].lstrip("\n")
    front = yaml.safe_load(fm_text) or {}
    return front, body

def write_front_matter_and_body(path, front, body):
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front, f, sort_keys=False, allow_unicode=True)
        f.write("---\n\n")
        f.write(body)

def discover_pages():
    """
    Scan _wiki for .md files, collect:
      - slug (filename without .md)
      - title
      - body
      - redirect_target (if redirect)
    """
    pages = []

    for fname in os.listdir(WIKI_DIR):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(WIKI_DIR, fname)
        slug = os.path.splitext(fname)[0]

        front, body = read_front_matter_and_body(path)
        title = front.get("title", slug)

        # detect redirect
        redirect_target = None
        for line in body.splitlines():
            m = REDIRECT_RE.match(line.strip())
            if m:
                redirect_target = m.group(1).strip()
                break

        pages.append({
            "path": path,
            "slug": slug,
            "title": title,
            "front": front,
            "body": body,
            "redirect_target": redirect_target,
        })

    return pages

def build_title_index(pages):
    """
    Map normalized title -> list of pages with that title.
    Normally you should have 1, but we store list to be safe.
    """
    index = defaultdict(list)
    for p in pages:
        norm = normalize(p["title"])
        index[norm].append(p)
    return index

def resolve_redirect(target_title, redirects_by_title):
    """
    Follow redirect chain:
      title A -> title B -> title C (non-redirect)
    Return the final non-redirect title.
    Detect and break loops.
    """
    seen = set()
    current = target_title
    while True:
        norm = normalize(current)
        if norm in seen:
            # loop detected, stop
            return current
        seen.add(norm)
        next_title = redirects_by_title.get(norm)
        if not next_title:
            return current
        current = next_title

def main():
    pages = discover_pages()
    title_index = build_title_index(pages)

    # First, collect redirects as title -> target_title (raw)
    redirects_by_title = {}
    for p in pages:
        if p["redirect_target"]:
            src_title = p["title"]
            redirects_by_title[normalize(src_title)] = p["redirect_target"]

    # Resolve each redirect to its final canonical title
    alias_to_canonical_title = {}
    for norm_src, raw_target in redirects_by_title.items():
        final_title = resolve_redirect(raw_target, redirects_by_title)
        alias_to_canonical_title[norm_src] = final_title

    # Now map canonical title -> slug (we only care about non-redirect pages)
    canonical_slug_by_title_norm = {}

    for p in pages:
        if p["redirect_target"]:
            continue  # redirect page, not canonical
        norm = normalize(p["title"])
        canonical_slug_by_title_norm[norm] = p["slug"]

    # Build final alias map: alias_norm -> canonical slug
    alias_to_slug = {}

    for alias_norm, canonical_title in alias_to_canonical_title.items():
        canonical_norm = normalize(canonical_title)
        slug = canonical_slug_by_title_norm.get(canonical_norm)
        if slug:
            alias_to_slug[alias_norm] = slug
        else:
            # No real page for that title; you can log/print if you want
            print(f"Warning: alias points to missing page: {canonical_title!r}")

    # Ensure _data exists
    os.makedirs(DATA_DIR, exist_ok=True)

    data = {
        "aliases": alias_to_slug
    }

    with open(ALIASES_YML, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=True, allow_unicode=True)

    # Optional: mark redirect pages in front matter so we can hide them from index
    for p in pages:
        if p["redirect_target"]:
            front = p["front"]
            front["is_redirect"] = True  # flag for index filtering
            # Could also store the canonical slug or title if you like:
            canonical_title = alias_to_canonical_title.get(normalize(p["title"]), p["redirect_target"])
            front["redirect_to"] = canonical_title
            write_front_matter_and_body(p["path"], front, p["body"])

    print(f"Alias map written to {ALIASES_YML}")
    print("Redirect pages flagged with is_redirect: true and redirect_to in front matter.")

if __name__ == "__main__":
    main()
