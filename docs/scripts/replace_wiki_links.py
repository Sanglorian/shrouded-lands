import re
from pathlib import Path
import unicodedata

import yaml  # pip install pyyaml

ROOT = Path(__file__).resolve().parents[1]  # docs/
WIKI_DIR = ROOT / "_wiki"
DATA_DIR = ROOT / "_data"

ALIASES_PATH = DATA_DIR / "aliases.yml"

# ---------------------------
# Helpers
# ---------------------------

def parse_front_matter_and_body(text):
    """
    Return (front_matter_dict, body_text)
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    _, fm_text, body = parts
    front = yaml.safe_load(fm_text) or {}
    return front, body.lstrip("\n")


def split_front_matter_text(text):
    """
    Return (front_matter_block_text, body_text) without parsing YAML.
    front_matter_block_text includes the leading and trailing '---'
    if present, otherwise ''.
    """
    if not text.startswith("---"):
        return "", text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text

    # parts: ['', fm, body]
    fm_block = "---" + parts[1] + "---\n"
    body = parts[2].lstrip("\n")
    return fm_block, body


def load_alias_map():
    if not ALIASES_PATH.exists():
        print("No aliases.yml found, continuing without aliases.")
        return {}
    data = yaml.safe_load(ALIASES_PATH.read_text(encoding="utf-8")) or {}
    # Expecting a simple mapping alias -> canonical_title
    return data


def slugify_title(s: str) -> str:
    """
    Fallback slug for unresolved targets.
    Example: 'Green Lady (Myth)' -> 'green-lady-myth'
    """
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s.lower()


# Matches [[Target]] or [[Target|Text]]
WIKI_LINK_RE = re.compile(r"\[\[([^|\]]+)(\|([^]]+))?\]\]")


# ---------------------------
# Build title -> slug map
# ---------------------------

def build_title_to_slug_map():
    """
    title (from front matter) -> slug (filename without .md)
    """
    title_to_slug = {}

    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        front, _ = parse_front_matter_and_body(text)
        title = front.get("title") or md.stem
        slug = md.stem  # because permalink is /wiki/:name/

        if title in title_to_slug and title_to_slug[title] != slug:
            print(
                f"Warning: title '{title}' used for multiple slugs: "
                f"{title_to_slug[title]} and {slug}"
            )
        title_to_slug.setdefault(title, slug)

    return title_to_slug


# ---------------------------
# Main link replacement logic
# ---------------------------

def make_link_replacer(alias_map, title_to_slug, current_file):

    def replace(match):
        raw_target = match.group(1).strip()
        text = (match.group(3) or raw_target).strip()

        # Skip / demote certain namespaces and oddities
        if raw_target.startswith(("File:", "Image:", "Category:", ":")):
            # Drop the wiki markup, keep readable text
            # e.g. [[Category:Hex]] -> "Category:Hex"
            return text

        # Strip anchors like "Page#Section"
        base_target, _, _ = raw_target.partition("#")
        base_target = base_target.strip()

        # Apply alias map (and allow aliases to themselves)
        canonical = alias_map.get(base_target, base_target)
        canonical_base, _, _ = canonical.partition("#")
        canonical_base = canonical_base.strip()

        # Special handling for hex-like titles: 00.09 or 00.09.01 etc.
        m_hex = re.match(r"^(\d{2})\.(\d{2})(?:\.(\d{2}))?$", canonical_base)
        if m_hex:
            # Always link to the parent hex: 00.09.01 -> 00-09
            slug = f"{m_hex.group(1)}-{m_hex.group(2)}"
        else:
            slug = title_to_slug.get(canonical_base)

        if not slug:
            # Can't resolve – maybe typo or genuinely missing page.
            # Keep it as a *broken* link instead of dropping it.
            print(
                f"Unresolved link target '{raw_target}' "
                f"(canonical '{canonical_base}') in {current_file}; "
                f"keeping as broken link."
            )
            slug = slugify_title(canonical_base)

        url = f"/wiki/{slug}/"
        return f"[{text}]({url})"

    return replace


def process_files():
    alias_map = load_alias_map()
    title_to_slug = build_title_to_slug_map()

    print(f"Loaded {len(alias_map)} aliases.")
    print(f"Mapped {len(title_to_slug)} titles to slugs.")

    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")

        fm_block, body = split_front_matter_text(text)

        replacer = make_link_replacer(alias_map, title_to_slug, md.name)
        new_body = WIKI_LINK_RE.sub(replacer, body)

        new_text = fm_block + new_body
        md.write_text(new_text, encoding="utf-8")

        print(f"Processed {md.name}")

    print("Done replacing wiki links.")


if __name__ == "__main__":
    process_files()
