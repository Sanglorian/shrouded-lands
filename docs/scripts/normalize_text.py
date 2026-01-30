from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"

# MediaWiki heading pattern: == Foo ==, === Foo ===, etc.
MW_HEADING_RE = re.compile(r'^(=+)\s*(.*?)\s*(=+)\s*$', re.MULTILINE)

BOLD_RE = re.compile(r"'''(.*?)'''", re.DOTALL)
ITALIC_RE = re.compile(r"''(.*?)''", re.DOTALL)

def convert_headings(text: str) -> str:
    def repl(m):
        left = m.group(1)
        content = m.group(2).strip()
        right = m.group(3)
        if len(left) != len(right):
            return m.group(0)
        level = len(left)
        md = "#" * level
        return f"{md} {content}"
    return MW_HEADING_RE.sub(repl, text)

def normalize(text: str) -> str:
    # convert headings first
    text = convert_headings(text)

    # bold: '''foo''' → **foo**
    text = BOLD_RE.sub(r'**\1**', text)

    # italics: ''foo'' → *foo*
    text = ITALIC_RE.sub(r'*\1*', text)

    # non-breaking spaces → normal space
    text = text.replace('\u00A0', ' ')

    return text

def split_front(text):
    if not text.startswith('---'):
        return '', text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return '', text
    fm = '---' + parts[1] + '---\n'
    body = parts[2].lstrip('\n')
    return fm, body

def main():
    for md in WIKI_DIR.glob("*.md"):
        raw = md.read_text(encoding="utf-8")
        fm, body = split_front(raw)
        new_body = normalize(body)
        if new_body != body:
            md.write_text(fm + new_body, encoding="utf-8")
            print(f"Normalized", md.name)

if __name__ == "__main__":
    main()
