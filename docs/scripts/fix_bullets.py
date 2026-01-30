from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]  # docs/
WIKI_DIR = ROOT / "_wiki"

def split_front_matter(text: str):
    """Return (front_matter_block, body_text)."""
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    fm_block = "---" + parts[1] + "---\n"
    body = parts[2].lstrip("\n")
    return fm_block, body

def fix_body(body: str) -> str:
    # 1) Remove inline Category:... markers (we use front matter instead)
    #    e.g. "...?Category:Hex" → "...?"
    body = re.sub(r"Category:[^\n]+", "", body)

    # 1a) Fix special leading-asterisk patterns from wikitext conversions.
    #     "* *Text **refers" -> "**Text** refers"
    body = re.sub(
        r"^\* \*(\S[^*]*?)\*\*\s*(refers\b)",
        r"**\1** \2",
        body,
        flags=re.M,
    )
    #     "* *![](/media/filename.jpg)Type:** [Name](/link/)"
    #     -> "![](/media/filename.jpg)**Type:** [Name](/link/)"
    body = re.sub(
        r"^\* \*(!\[[^\]]*\]\([^)]+\))\s*([A-Za-z][^*:\n]*:)\*\*",
        r"\1**\2**",
        body,
        flags=re.M,
    )
    body = re.sub(
        r"^(!\[[^\]]*\]\([^)]+\))\s*([A-Za-z][^*:\n]*:)\*\*",
        r"\1**\2**",
        body,
        flags=re.M,
    )

    # 1b) "* * Text" should be an indented bullet.
    body = re.sub(r"^\* \* ", "  * ", body, flags=re.M)

    # 2) Ensure bullets have a space after * or - when they start a line
    #    (^ or \n) + optional indent + * or - + non-space → add space
    body = re.sub(r"(^|\n)(\s*)([*-])(?!\*)(\S)", r"\1\2\3 \4", body)

    # 3) Ensure each bullet starts on its own line.
    #    If we see "?.* * " or "!. * * " or ".* * " etc, insert a newline
    #    before the bullet marker.
    #    This catches things like:
    #      "* What ...?* Does ...?* Who ...?"
    body = re.sub(r"([.?!])\s*(\* )", r"\1\n\2", body)
    body = re.sub(r"([.?!])\s*(- )", r"\1\n\2", body)

    return body

def main():
    for md in WIKI_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        fm_block, body = split_front_matter(text)
        new_body = fix_body(body)

        if new_body != body:
            md.write_text(fm_block + new_body, encoding="utf-8")
            print(f"Fixed bullets in {md.name}")

if __name__ == "__main__":
    main()
