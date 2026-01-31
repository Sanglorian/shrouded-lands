"""Generate PDFs per category with description and page membership."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape as xml_escape

import yaml

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (ListFlowable, ListItem, Paragraph,
                                    Preformatted, SimpleDocTemplate, Spacer)
except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
    raise SystemExit(
        "Missing dependency: reportlab. Install with `pip install reportlab`."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "_wiki"
OUT_DIR = ROOT / "output" / "category_pdfs"

def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.lstrip().startswith("---"):
        return {}, text

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return {}, text

    frontmatter = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1 :])
    try:
        data = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        data = {}
    return data, body


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "category"


def apply_inline_formatting(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = xml_escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"_([^_]+)_", r"<i>\1</i>", text)
    return text


def markdown_to_flowables(text: str) -> list:
    styles = getSampleStyleSheet()
    body_style = styles["BodyText"]
    heading_style = styles["Heading2"]
    elements: list = []
    lines = text.splitlines()
    paragraph_lines: list[str] = []
    list_items: list[str] = []
    in_code_block = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph = " ".join(line.strip() for line in paragraph_lines)
            paragraph = apply_inline_formatting(paragraph)
            elements.append(Paragraph(paragraph, body_style))
            elements.append(Spacer(1, 10))
            paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            items = [
                ListItem(Paragraph(apply_inline_formatting(item), body_style))
                for item in list_items
            ]
            elements.append(ListFlowable(items, bulletType="bullet"))
            elements.append(Spacer(1, 10))
            list_items = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if in_code_block:
                elements.append(
                    Preformatted("\n".join(code_lines), styles["Code"])
                )
                elements.append(Spacer(1, 10))
                code_lines = []
                in_code_block = False
            else:
                flush_paragraph()
                flush_list()
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            heading_text = apply_inline_formatting(heading_match.group(2))
            elements.append(Paragraph(heading_text, heading_style))
            elements.append(Spacer(1, 10))
            continue

        list_match = re.match(r"^[*-]\s+(.*)", line)
        if list_match:
            flush_paragraph()
            list_items.append(list_match.group(1))
            continue

        paragraph_lines.append(line)

    flush_paragraph()
    flush_list()
    if in_code_block and code_lines:
        elements.append(Preformatted("\n".join(code_lines), styles["Code"]))
        elements.append(Spacer(1, 10))

    return elements


def build_page_flowables(
    title: str,
    page_info: dict | None,
    styles: dict,
    *,
    include_heading: bool = True,
    heading_style: str = "Heading2",
) -> list:
    elements: list = []
    frontmatter = page_info.get("frontmatter", {}) if page_info else {}
    body = page_info.get("body", "") if page_info else ""

    display_title = frontmatter.get("subtitle") or title
    if include_heading:
        elements.append(Paragraph(xml_escape(display_title), styles[heading_style]))
        elements.append(Spacer(1, 10))

    summary = frontmatter.get("summary")
    if summary:
        elements.append(
            Paragraph(f"<i>{xml_escape(str(summary))}</i>", styles["BodyText"])
        )
        elements.append(Spacer(1, 10))

    meta_lines: list[str] = []
    if frontmatter.get("subtitle"):
        meta_lines.append(f"<b>Hex:</b> {xml_escape(title)}")
    region = frontmatter.get("region")
    if region:
        meta_lines.append(f"<b>Region:</b> {xml_escape(str(region))}")
    if meta_lines:
        elements.append(Paragraph("<br/>".join(meta_lines), styles["BodyText"]))
        elements.append(Spacer(1, 10))

    if body:
        elements.extend(markdown_to_flowables(body))

    categories = frontmatter.get("categories") or []
    if isinstance(categories, list) and categories:
        labels = [
            str(cat).replace("Category:", "").strip() for cat in categories if cat
        ]
        elements.append(
            Paragraph(
                f"<b>Categories:</b> {xml_escape(', '.join(labels))}",
                styles["BodyText"],
            )
        )
        elements.append(Spacer(1, 10))

    original_url = frontmatter.get("original_url")
    if original_url:
        elements.append(
            Paragraph(
                f"<b>Original:</b> {xml_escape(str(original_url))}",
                styles["BodyText"],
            )
        )
        elements.append(Spacer(1, 10))

    return elements


def write_pdf(
    path: Path,
    title: str,
    pages: Iterable[str],
    page_data: dict[str, dict],
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    elements: list = []

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

    category_info = page_data.get(title)
    if category_info:
        elements.extend(
            build_page_flowables(
                title,
                category_info,
                styles,
                include_heading=False,
            )
        )

    elements.append(Paragraph("Pages", styles["Heading2"]))
    if pages:
        list_items = [ListItem(Paragraph(item, styles["BodyText"])) for item in pages]
        elements.append(ListFlowable(list_items, bulletType="bullet"))
        elements.append(Spacer(1, 12))
        for page in pages:
            page_info = page_data.get(page)
            if page_info:
                elements.extend(
                    build_page_flowables(
                        page,
                        page_info,
                        styles,
                        include_heading=True,
                        heading_style="Heading3",
                    )
                )
            else:
                elements.append(Paragraph(xml_escape(page), styles["Heading3"]))
                elements.append(
                    Paragraph("No content found for this page.", styles["BodyText"])
                )
                elements.append(Spacer(1, 10))
    else:
        elements.append(Paragraph("No pages listed for this category.", styles["BodyText"]))

    doc.build(elements)


def main() -> None:
    page_data: dict[str, dict] = {}
    category_to_pages: dict[str, set[str]] = {}
    referenced_categories: set[str] = set()

    for path in WIKI_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        title = str(frontmatter.get("title", "")).strip()
        if title:
            page_data[title] = {
                "frontmatter": frontmatter,
                "body": body.strip(),
            }

        categories = frontmatter.get("categories") or []
        if not isinstance(categories, list):
            continue

        for category in categories:
            if isinstance(category, str):
                referenced_categories.add(category)

        if title:
            for category in categories:
                if not isinstance(category, str):
                    continue
                category_to_pages.setdefault(category, set()).add(title)

    for category in sorted(referenced_categories):
        pages = sorted(category_to_pages.get(category, set()))
        filename = f"{slugify(category)}.pdf"
        output_path = OUT_DIR / filename
        write_pdf(output_path, category, pages, page_data)

    print(f"Wrote {len(referenced_categories)} category PDFs to {OUT_DIR}")


if __name__ == "__main__":
    main()
