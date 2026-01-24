import json
import shutil
from pathlib import Path

# ---------- PATHS ----------

# Where your Shrouded Lands dump lives (already created by your Python scraper)
DUMP_DIR = Path("shrouded_test_output")
PAGES_JSON_DIR = DUMP_DIR / "pages"
MEDIA_SRC_DIR = DUMP_DIR / "images"   # from shrouded_test_images.py
INDEX_JSONL = DUMP_DIR / "index.jsonl"

# Where we build the Jekyll site (this script will create / overwrite these)
SITE_DIR = Path("docs")
LAYOUTS_DIR = SITE_DIR / "_layouts"
WIKI_DIR = SITE_DIR / "_wiki"
MEDIA_DST_DIR = SITE_DIR / "media"
CONFIG_PATH = SITE_DIR / "_config.yml"
INDEX_HTML_PATH = SITE_DIR / "index.html"


# ---------- HELPERS ----------

def safe_slug(title: str) -> str:
    """Generate a simple slug from a page title."""
    slug = title.strip().lower()
    # Spaces to dashes
    slug = slug.replace(" ", "-")
    # Replace characters that are awkward in filenames/URLs
    bad = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#', '%', '&', '{', '}', '+', '!', '@', '^']
    for ch in bad:
        slug = slug.replace(ch, "-")
    # Collapse double dashes
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug or "page"


def ensure_dirs():
    SITE_DIR.mkdir(exist_ok=True)
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DST_DIR.mkdir(parents=True, exist_ok=True)


def write_config():
    """
    Write a basic _config.yml for the Shrouded Lands mirror.
    Overwrites existing config if present.
    """
    config = """title: "Shrouded Lands Wiki Mirror"
markdown: kramdown

collections:
  wiki:
    output: true
    permalink: /wiki/:name/

defaults:
  - scope:
      path: ""
      type: wiki
    values:
      layout: wiki_page
"""
    CONFIG_PATH.write_text(config, encoding="utf-8")
    print(f"[CFG] Wrote {CONFIG_PATH}")


def write_layouts():
    """
    Write default.html and wiki_page.html layouts.
    Overwrites if they already exist (you can customize later).
    """
    default_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ page.title }} - {{ site.title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 2rem auto;
      max-width: 900px;
      padding: 0 1rem;
      line-height: 1.5;
    }
    a { color: #0366d6; text-decoration: none; }
    a:hover { text-decoration: underline; }
    header { margin-bottom: 1.5rem; }
    header h1 { margin: 0 0 0.25rem 0; font-size: 1.8rem; }
    header .meta { color: #666; font-size: 0.9rem; }
    pre {
      background: #f5f5f5;
      padding: 1rem;
      border-radius: 6px;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    nav a { margin-right: 1rem; font-size: 0.9rem; }
    footer {
      margin-top: 2rem;
      font-size: 0.8rem;
      color: #777;
      border-top: 1px solid #eee;
      padding-top: 0.5rem;
    }
  </style>
</head>
<body>
  <nav>
    <a href="{{ '/' | relative_url }}">Home</a>
  </nav>
  {{ content }}
  <footer>
    Mirror generated from <code>shrouded_test_output</code> data.
  </footer>
</body>
</html>
"""

    wiki_page_html = """---
layout: default
---

<header>
  {% if page.subtitle %}
    <h1>{{ page.subtitle }}</h1>
  {% else %}
    <h1>{{ page.title }}</h1>
  {% endif %}
  <div class="meta">
    {% if page.subtitle %}
      Title: {{ page.title }} ·
    {% endif %}
    Page ID: {{ page.pageid }} · Namespace: {{ page.namespace }}
    {% if page.original_url %}
      · Original: <a href="{{ page.original_url }}" target="_blank">{{ page.original_url }}</a>
    {% endif %}
  </div>
  {% if page.categories %}
    <div class="meta">
      Categories:
      {% for cat in page.categories %}
        <span>{{ cat }}</span>{% unless forloop.last %}, {% endunless %}
      {% endfor %}
    </div>
  {% endif %}
</header>

<h2>Raw wikitext</h2>
<pre>{{ content | escape }}</pre>
"""

    (LAYOUTS_DIR / "default.html").write_text(default_html, encoding="utf-8")
    print(f"[LAYOUT] Wrote {LAYOUTS_DIR / 'default.html'}")

    (LAYOUTS_DIR / "wiki_page.html").write_text(wiki_page_html, encoding="utf-8")
    print(f"[LAYOUT] Wrote {LAYOUTS_DIR / 'wiki_page.html'}")


def copy_media():
    """
    Copy all media files from shrouded_test_output/images into docs/media.
    Does not modify the original dump.
    """
    if not MEDIA_SRC_DIR.exists():
        print(f"[MEDIA] No images directory found at {MEDIA_SRC_DIR}, skipping.")
        return

    for src in MEDIA_SRC_DIR.iterdir():
        if not src.is_file():
            continue
        dst = MEDIA_DST_DIR / src.name
        if dst.exists():
            print(f"[MEDIA] Skip existing {src.name}")
            continue
        print(f"[MEDIA] Copying {src.name}")
        shutil.copy2(src, dst)


def yaml_escape(s: str) -> str:
    """Escape a string for safe double-quoted YAML."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_wiki_pages():
    """
    Read index.jsonl + pages/*.json and write _wiki/*.md files
    with YAML front matter + wikitext body.

    This does NOT modify the original dump; it only reads from it.
    """
    if not INDEX_JSONL.exists():
        raise FileNotFoundError(f"{INDEX_JSONL} not found. Run your Shrouded dump first.")

    index_entries = []

    with INDEX_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            pageid = rec["pageid"]
            title = rec["title"]
            ns = rec["ns"]
            fullurl = rec.get("fullurl") or ""
            categories = rec.get("categories") or []

            page_json_path = PAGES_JSON_DIR / f"{pageid}.json"
            if not page_json_path.exists():
                print(f"[WARN] No JSON for pageid {pageid} ({title})")
                continue

            page_data = json.loads(page_json_path.read_text(encoding="utf-8"))
            content = page_data.get("content", "")

            slug = safe_slug(title)
            md_path = WIKI_DIR / f"{slug}.md"
            # Disambiguate if two pages slugify to the same name
            if md_path.exists():
                md_path = WIKI_DIR / f"{slug}-{pageid}.md"

            print(f"[WIKI] Writing {md_path.name} for '{title}'")

            yaml_title = yaml_escape(title)
            yaml_url = yaml_escape(fullurl)

            front_matter_lines = [
                "---",
                "layout: wiki_page",
                f'title: "{yaml_title}"',
                f"pageid: {pageid}",
                f"namespace: {ns}",
                f'original_url: "{yaml_url}"',
                "categories:",
            ]
            if categories:
                for c in categories:
                    front_matter_lines.append(f'  - "{yaml_escape(c)}"')
            else:
                front_matter_lines.append("  []")

            # You can populate this later if you build a media mapping per page
            front_matter_lines.append("media: []")
            front_matter_lines.append("---")

            front_matter = "\n".join(front_matter_lines)
            body = content or ""

            md_text = f"{front_matter}\n\n{body}\n"
            md_path.write_text(md_text, encoding="utf-8")

            index_entries.append({
                "title": title,
                "slug": md_path.stem,
                "namespace": ns,
                "pageid": pageid,
            })

    # Build a simple index.html listing all pages
    index_entries_sorted = sorted(index_entries, key=lambda e: (e["namespace"], e["title"].lower()))
    items_html = "\n".join(
        f'<li>[ns {e["namespace"]}] <a href="{{{{ "/wiki/{e["slug"]}/" | relative_url }}}}">{yaml_escape(e["title"])}</a></li>'
        for e in index_entries_sorted
    )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Shrouded Lands Wiki Mirror</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 2rem auto;
      max-width: 900px;
      padding: 0 1rem;
      line-height: 1.5;
    }}
    h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
    .desc {{ color: #555; margin-bottom: 1rem; }}
    ul {{ list-style: none; padding-left: 0; }}
    li {{ margin-bottom: 0.25rem; }}
    code {{
      background: #f5f5f5;
      padding: 0.1rem 0.3rem;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
  <h1>Shrouded Lands Wiki Mirror</h1>
  <p class="desc">
    Static mirror generated from the live wiki dump.
    Pages are shown as raw wikitext; media files are under <code>/media/</code>.
  </p>
  <h2>Pages</h2>
  <ul>
    {items_html}
  </ul>
</body>
</html>
"""
    INDEX_HTML_PATH.write_text(index_html, encoding="utf-8")
    print(f"[INDEX] Wrote {INDEX_HTML_PATH}")


def main():
    print(f"[INFO] Building Jekyll site from Shrouded dump at: {DUMP_DIR.resolve()}")
    ensure_dirs()
    write_config()
    write_layouts()
    copy_media()
    write_wiki_pages()
    print(f"\n[OK] Jekyll site built in: {SITE_DIR.resolve()}")
    print("You can now commit 'docs/' to a GitHub repo and use it as your GitHub Pages source.")


if __name__ == "__main__":
    main()
