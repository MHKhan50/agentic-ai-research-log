#!/usr/bin/env python3
"""Convert docs/article_draft.md to a readable PDF using ReportLab Platypus.

Optional helper; the core benchmark does not depend on ReportLab.
Install with: python3 -m pip install -r requirements-pdf.txt
"""
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted,
    ListFlowable, ListItem, KeepTogether,
)


def inline_markup(text):
    value = html.escape(text, quote=False)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', value)
    value = re.sub(r"\[(.*?)\]\((https?://[^)]+)\)", r'<link href="\2" color="#1769aa">\1</link>', value)
    return value


def parse_markdown(markdown_text, styles, usable_width):
    lines = markdown_text.splitlines()
    story = []
    i = 0
    in_code = False
    code_lines = []
    paragraph_lines = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            story.append(Paragraph(inline_markup(text), styles["BodyTextCustom"]))
            story.append(Spacer(1, 5))
            paragraph_lines = []

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush_paragraph()
            if not in_code:
                in_code = True
                code_lines = []
            else:
                story.append(Preformatted("\n".join(code_lines), styles["CodeCustom"]))
                story.append(Spacer(1, 7))
                in_code = False
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not line.strip():
            flush_paragraph()
            i += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            parsed_rows = []
            for table_line in table_lines:
                cells = [cell.strip() for cell in table_line.strip().strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in cells):
                    continue
                parsed_rows.append([Paragraph(inline_markup(cell), styles["TableCellCustom"]) for cell in cells])
            if parsed_rows:
                col_count = max(len(row) for row in parsed_rows)
                normalized = [row + [Paragraph("", styles["TableCellCustom"])] * (col_count-len(row)) for row in parsed_rows]
                col_widths = [usable_width / col_count] * col_count
                table = Table(normalized, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172b4d")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#b8c2cc")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(table)
                story.append(Spacer(1, 9))
            continue
        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[2:].strip()), styles["TitleCustom"]))
            story.append(Spacer(1, 7))
            i += 1
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(Spacer(1, 7))
            story.append(Paragraph(inline_markup(line[3:].strip()), styles["Heading1Custom"]))
            story.append(Spacer(1, 4))
            i += 1
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[4:].strip()), styles["Heading2Custom"]))
            story.append(Spacer(1, 3))
            i += 1
            continue
        if re.match(r"^\s*[-*]\s+", line):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                item_text = re.sub(r"^\s*[-*]\s+", "", lines[i]).strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["BodyTextCustom"]), leftIndent=10))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=18, bulletFontName="Helvetica", bulletFontSize=7))
            story.append(Spacer(1, 5))
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\s*\d+\.\s+", "", lines[i]).strip()
                items.append(ListItem(Paragraph(inline_markup(item_text), styles["BodyTextCustom"]), leftIndent=10))
                i += 1
            story.append(ListFlowable(items, bulletType="1", leftIndent=20))
            story.append(Spacer(1, 5))
            continue
        paragraph_lines.append(line)
        i += 1
    flush_paragraph()
    if in_code and code_lines:
        story.append(Preformatted("\n".join(code_lines), styles["CodeCustom"]))
    return story


def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d5dbe3"))
    canvas.line(18*mm, 15*mm, A4[0]-18*mm, 15*mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5b6573"))
    canvas.drawString(18*mm, 9*mm, "ToolGuard v0.1.0 — research draft; verify results before publication")
    canvas.drawRightString(A4[0]-18*mm, 9*mm, "Page {}".format(doc.page))
    canvas.restoreState()


def main():
    source = Path("docs/article_draft.md")
    output = Path("docs/article_draft.pdf")
    markdown_text = source.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
        topMargin=18*mm, bottomMargin=22*mm,
        title="ToolGuard: Measuring Validation Gates and Bounded Retries",
        author="MHKhan50",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_CENTER, textColor=colors.HexColor("#172b4d"), spaceAfter=8))
    styles.add(ParagraphStyle(name="Heading1Custom", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#172b4d"), keepWithNext=True))
    styles.add(ParagraphStyle(name="Heading2Custom", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#26466d"), keepWithNext=True))
    styles.add(ParagraphStyle(name="BodyTextCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12, spaceAfter=3))
    styles.add(ParagraphStyle(name="TableCellCustom", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name="CodeCustom", fontName="Courier", fontSize=7.5, leading=9, leftIndent=8, rightIndent=8, borderWidth=0.5, borderColor=colors.HexColor("#d5dbe3"), borderPadding=6, backColor=colors.HexColor("#f5f7fa")))
    story = parse_markdown(markdown_text, styles, A4[0] - 36*mm)
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    print("PDF written to {}".format(output))


if __name__ == "__main__":
    main()
