from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # docs/
WIKI_DIR = ROOT / "_wiki"

def strip_parens(url: str) -> str:
    return (
        url.replace("%28", "")
        .replace("%29", "")
        .replace("(", "")
        .replace(")", "")
    )


def replace_markdown_links(text: str) -> str:
    result = []
    i = 0
    length = len(text)

    while i < length:
        start = text.find("](", i)
        if start == -1:
            result.append(text[i:])
            break

        result.append(text[i:start + 2])
        i = start + 2
        url_start = i
        depth = 0

        while i < length:
            if text.startswith("%28", i):
                depth += 1
                i += 3
                continue
            if text.startswith("%29", i):
                if depth > 0:
                    depth -= 1
                i += 3
                continue

            char = text[i]
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            i += 1

        url = text[url_start:i]
        result.append(strip_parens(url))

        if i < length and text[i] == ")":
            result.append(")")
            i += 1

    return "".join(result)


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text = replace_markdown_links(text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for md in WIKI_DIR.glob("*.md"):
        if process_file(md):
            changed += 1
    print(f"Updated {changed} files.")


if __name__ == "__main__":
    main()
