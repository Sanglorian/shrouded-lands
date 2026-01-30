import re
from pathlib import Path

# Adjust this if your script lives in scripts/
ROOT = Path(__file__).resolve().parent
WIKI_DIR = ROOT / "_wiki"

file_tag_pattern = re.compile(
    r"\[\[File:([^|\]]+)([^]]*)\]\]",
    re.IGNORECASE
)

FORMAT_KEYWORDS = {
    "thumb", "thumbnail", "frameless", "border",
    "right", "left", "center", "none"
}

def is_format_token(token: str) -> bool:
    """Return True if this looks like a formatting/size token, not caption text."""
    t = token.strip().lower()

    if not t:
        return True

    # alignment / display keywords
    if t in FORMAT_KEYWORDS:
        return True

    # upright / upright=1.5 style
    if t.startswith("upright"):
        return True

    # simple size: 350px
    if re.fullmatch(r"\d+px", t):
        return True

    # WxHpx style: 350x200px
    if re.fullmatch(r"\d+x\d+px", t):
        return True

    return False


def replace_file_tag(match):
    filename = match.group(1).strip()
    rest = match.group(2) or ""

    parts = [p.strip() for p in rest.split("|") if p.strip()]

    caption = ""
    if parts:
        candidate = parts[-1]
        if not is_format_token(candidate):
            caption = candidate

    safe_filename = filename.replace(" ", "_")
    url = f"/media/{safe_filename}"

    # If no real caption, leave alt text empty
    if caption:
        return f"![{caption}]({url})"
    else:
        return f"![]({url})"


def process_file(path: Path):
    text = path.read_text(encoding="utf-8")
    new_text = file_tag_pattern.sub(replace_file_tag, text)

    if new_text != text:
        print(f"Updated {path.name}")
        path.write_text(new_text, encoding="utf-8")


def main():
    if not WIKI_DIR.exists():
        print(f"ERROR: No _wiki directory found at: {WIKI_DIR}")
        return

    for md in WIKI_DIR.glob("*.md"):
        process_file(md)


if __name__ == "__main__":
    main()
