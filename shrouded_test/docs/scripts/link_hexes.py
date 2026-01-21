from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"

# Match any hex code: 00.00 or 00.00.00
HEX_CODE_RE = re.compile(r"\b(\d{2}\.\d{2}(?:\.\d{2})?)\b")

# Strip existing hex links of the form:
# [00.02](/wiki/00-02/) or [00.02.03](/wiki/00-02/)
HEX_LINK_RE = re.compile(
    r"\[(\d{2}\.\d{2}(?:\.\d{2})?)\]\(/wiki/\d{2}-\d{2}/\)"
)

def split_front_matter(text: str):
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    fm = "---" + parts[1] + "---\n"
    body = parts[2].lstrip("\n")
    return fm, body

def relink_hexes(text: str) -> str:
    # 1) Remove any existing hex links so we don't double-wrap or inherit bad ones
    text_no_links = HEX_LINK_RE.sub(lambda m: m.group(1), text)

    # 2) Link all bare hex codes, mapping 00.02.03 -> /wiki/00-02/
    def repl(m: re.Match) -> str:
        code = m.group(1)           # e.g. "00.02.03"
        start = m.start()

        # Don't link if the code is already the visible text
        # of a markdown link (i.e. immediately after '[')
        if start > 0 and text_no_links[start - 1] == "[":
            return code

        parts = code.split(".")
        base = ".".join(parts[:2])  # "00.02"
        slug = base.replace(".", "-")  # "00-02"

        return f"[{code}](/wiki/{slug}/)"

    return HEX_CODE_RE.sub(repl, text_no_links)

def main():
    for md in WIKI_DIR.glob("*.md"):
        raw = md.read_text(encoding="utf-8")
        fm, body = split_front_matter(raw)
        new_body = relink_hexes(body)
        if new_body != body:
            md.write_text(fm + new_body, encoding="utf-8")
            print("Re-linked hexes in", md.name)

if __name__ == "__main__":
    main()
