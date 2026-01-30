from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"

# Match patterns like:
# [[00.02](/wiki/00-02/)](/wiki/00-02/)
# i.e. outer link wraps an inner link with the SAME url
NESTED_LINK_RE = re.compile(
    r"\[\[([^\]]+?)\]\((/wiki/[^)]+?)\)\]\(\2\)"
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

def cleanup(text: str) -> str:
    def repl(m):
        inner_text = m.group(1)
        url = m.group(2)
        # collapse to a single proper link
        return f"[{inner_text}]({url})"

    return NESTED_LINK_RE.sub(repl, text)

def main():
    for md in WIKI_DIR.glob("*.md"):
        raw = md.read_text(encoding="utf-8")
        fm, body = split_front_matter(raw)
        new_body = cleanup(body)
        if new_body != body:
            md.write_text(fm + new_body, encoding="utf-8")
            print("Fixed nested links in", md.name)

if __name__ == "__main__":
    main()
