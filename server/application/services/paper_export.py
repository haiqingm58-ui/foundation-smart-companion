from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Literal

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as PdfImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont


ExportVariant = Literal["questions", "answer-sheet", "answers"]
ExportFormat = Literal["docx", "pdf"]
DOCX_FONT_NAME = "Arial Unicode MS"
PDF_FONT_NAME = "FoundationPaperUnicode"
PDF_FONT_CANDIDATES = (
    (Path("/Library/Fonts/Arial Unicode.ttf"), 0),
    (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), 0),
    (Path("/System/Library/Fonts/Supplemental/Songti.ttc"), 0),
    (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), 0),
    (Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"), 0),
)


@dataclass(frozen=True)
class ExportOptions:
    include_student_fields: bool = True
    asset_root: Path | None = None


def render_paper(
    paper: Any,
    variant: ExportVariant,
    format: ExportFormat,
    options: ExportOptions,
) -> bytes:
    if variant not in {"questions", "answer-sheet", "answers"}:
        raise ValueError(f"unsupported paper export variant: {variant}")
    if format == "docx":
        return _render_docx(paper, variant, options)
    if format == "pdf":
        return _render_pdf(paper, variant, options)
    raise ValueError(f"unsupported paper export format: {format}")


def _value(record: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(record, dict) and name in record:
            return record[name]
        if hasattr(record, name):
            return getattr(record, name)
    return default


def _paper_questions(paper: Any) -> list[Any]:
    rows = _value(paper, "paper_questions", "paperQuestions", default=[])
    return sorted(rows or [], key=lambda item: _value(item, "sequence", default=0))


def _question(row: Any) -> Any:
    return _value(row, "question", default=row)


def _question_value(row: Any, *names: str, default: Any = None) -> Any:
    return _value(_question(row), *names, default=default)


def _paper_title(paper: Any, variant: ExportVariant) -> str:
    title = str(_value(paper, "title", default="试卷"))
    if variant == "answer-sheet":
        return f"{title}答题卡"
    return title


def _subject_name(paper: Any) -> str:
    subject = _value(paper, "subject", default=None)
    return str(_value(subject, "name", "title", default="") or "")


def _answer_text(value: Any) -> str:
    if value is None:
        return "未提供"
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    if isinstance(value, dict):
        if "value" in value:
            return str(value["value"])
        return "；".join(f"{key}：{item}" for key, item in value.items())
    return str(value)


def _iter_formulas(row: Any) -> list[str]:
    question = _question(row)
    formulas = list(_value(_value(question, "source_metadata", "sourceMetadata", default={}), "formulas", default=[]) or [])
    for attachment in _value(question, "attachments", default=[]) or []:
        if _value(attachment, "kind", "type") == "formula":
            formula = _value(attachment, "latex", "text", "value")
            if formula:
                formulas.append(str(formula))
    return list(dict.fromkeys(formulas))


def _iter_tables(row: Any) -> list[list[list[Any]]]:
    question = _question(row)
    tables = list(_value(_value(question, "source_metadata", "sourceMetadata", default={}), "tables", default=[]) or [])
    for attachment in _value(question, "attachments", default=[]) or []:
        if _value(attachment, "kind", "type") == "table":
            rows = _value(attachment, "rows", default=[])
            if rows:
                tables.append(rows)
    return tables


def _image_bytes(attachment: Any, options: ExportOptions) -> bytes | None:
    if _value(attachment, "kind", "type") != "image":
        return None
    source = _value(attachment, "url", "data", "path", "src")
    if not isinstance(source, str):
        return None
    if source.startswith("data:image/") and ";base64," in source:
        try:
            return base64.b64decode(source.split(";base64,", 1)[1])
        except ValueError:
            return None
    path = Path(source)
    if not path.is_absolute() and options.asset_root:
        path = options.asset_root / path
    try:
        return path.read_bytes()
    except OSError:
        return None


def _iter_images(row: Any, options: ExportOptions) -> list[tuple[bytes, str]]:
    images: list[tuple[bytes, str]] = []
    for attachment in _question_value(row, "attachments", default=[]) or []:
        image = _image_bytes(attachment, options)
        if image:
            images.append((image, str(_value(attachment, "alt", "caption", default="题图"))))
    return images


def _set_docx_font_slots(r_pr, font_name: str = DOCX_FONT_NAME) -> None:
    r_fonts = r_pr.get_or_add_rFonts()
    for slot in ("ascii", "hAnsi", "eastAsia", "cs"):
        r_fonts.set(qn(f"w:{slot}"), font_name)


def _set_docx_run_font(run, font_name: str = DOCX_FONT_NAME) -> None:
    run.font.name = font_name
    _set_docx_font_slots(run._element.get_or_add_rPr(), font_name)


def _set_docx_style_font(style, font_name: str = DOCX_FONT_NAME) -> None:
    style.font.name = font_name
    _set_docx_font_slots(style._element.get_or_add_rPr(), font_name)


def _set_cell_text(cell, text: str, *, bold: bool = False, font_size: float = 10.5) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(font_size)
    _set_docx_run_font(run)


def _prevent_row_split(row) -> None:
    properties = row._tr.get_or_add_trPr()
    properties.append(OxmlElement("w:cantSplit"))


def _repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    properties.append(header)


def _set_table_widths(table, widths: list[Cm]) -> None:
    table.autofit = False
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = width


def _docx_table(document: Document, rows: list[list[Any]]) -> None:
    if not rows:
        return
    column_count = max(len(row) for row in rows)
    table = document.add_table(rows=0, cols=column_count)
    table.style = "Table Grid"
    _set_table_widths(table, [Cm(16.5 / column_count)] * column_count)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for index in range(column_count):
            _set_cell_text(cells[index], str(values[index]) if index < len(values) else "", bold=row_index == 0)
        _prevent_row_split(table.rows[-1])
        if row_index == 0:
            _repeat_table_header(table.rows[-1])
    document.add_paragraph().paragraph_format.space_after = Pt(1)


def _docx_text(document: Document, text: str, *, bold: bool = False, italic: bool = False, size: float = 10.5, keep: bool = False) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.25
    paragraph.paragraph_format.keep_together = True
    paragraph.paragraph_format.keep_with_next = keep
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    _set_docx_run_font(run)


def _add_docx_question(document: Document, row: Any, options: ExportOptions) -> None:
    number = _value(row, "sequence", default=0)
    points = _value(row, "points", default=0)
    text = str(_question_value(row, "text", default=""))
    _docx_text(document, f"{number}. {text}（{points:g} 分）", bold=True, keep=True)
    for option in _question_value(row, "options", default=[]) or []:
        _docx_text(document, f"{_value(option, 'label', default='')}. {_value(option, 'text', default='')}")
    for formula in _iter_formulas(row):
        _docx_text(document, f"公式：{formula}", italic=True, keep=True)
    for table_rows in _iter_tables(row):
        _docx_table(document, table_rows)
    for image, alt in _iter_images(row, options):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.keep_together = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(io.BytesIO(image), width=Cm(5))
        _docx_text(document, alt, italic=True, size=9)


def _render_docx(paper: Any, variant: ExportVariant, options: ExportOptions) -> bytes:
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(1.8)
    section.left_margin = section.right_margin = Cm(2.2)
    section.header_distance = Cm(1)
    section.footer_distance = Cm(1)
    normal = document.styles["Normal"]
    _set_docx_style_font(normal)
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25
    title_style = document.styles.add_style("ExamTitle", WD_STYLE_TYPE.PARAGRAPH)
    _set_docx_style_font(title_style)
    title_style.font.size = Pt(18)
    title_style.font.bold = True
    title_style.paragraph_format.space_after = Pt(8)
    title = document.add_paragraph(style="ExamTitle")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(_paper_title(paper, variant))
    if options.include_student_fields:
        info = document.add_table(rows=1, cols=3)
        info.style = "Table Grid"
        _set_table_widths(info, [Cm(5.5), Cm(5.5), Cm(5.5)])
        for cell, text in zip(info.rows[0].cells, ["姓名：____________", "学号：____________", "班级：____________"]):
            _set_cell_text(cell, text)
        _prevent_row_split(info.rows[0])
    _docx_text(
        document,
        "  ".join(
            item
            for item in [
                f"课程：{_subject_name(paper)}" if _subject_name(paper) else "",
                f"考试时间：{_value(paper, 'duration_minutes', 'durationMinutes', default='未限定')} 分钟",
                f"满分：{_value(paper, 'total_points', 'totalPoints', default=0):g} 分",
            ]
            if item
        ),
        size=10,
    )
    rows = _paper_questions(paper)
    if variant == "answer-sheet":
        for row in rows:
            _docx_text(document, f"{_value(row, 'sequence', default=0)}. （{_value(row, 'points', default=0):g} 分）", bold=True)
            for _ in range(3 if _question_value(row, "question_type", "questionType", default="") in {"简答题", "计算题"} else 1):
                _docx_text(document, "________________________________________________________________________")
    else:
        previous_section = None
        for row in rows:
            section_title = str(_value(row, "section_title", "sectionTitle", default=""))
            if section_title and section_title != previous_section:
                _docx_text(document, section_title, bold=True, size=13, keep=True)
                previous_section = section_title
            _add_docx_question(document, row, options)
    if variant == "answers":
        _docx_text(document, "参考答案", bold=True, size=13, keep=True)
        for row in rows:
            answer = _answer_text(_question_value(row, "correct_answer", "correctAnswer"))
            _docx_text(document, f"{_value(row, 'sequence', default=0)}. 正确答案：{answer}", bold=True)
            explanation = _question_value(row, "explanation")
            if explanation:
                _docx_text(document, f"解析：{explanation}")
    output = io.BytesIO()
    document.save(output)
    return output.getvalue()


def _pdf_styles() -> dict[str, ParagraphStyle]:
    # Keep the requested CID registration for consumers that expect it, but use
    # an embedded Unicode font so all PDF viewers can paint Chinese glyphs.
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    if PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        for font_path, subfont_index in PDF_FONT_CANDIDATES:
            if not font_path.is_file():
                continue
            pdfmetrics.registerFont(
                TTFont(PDF_FONT_NAME, str(font_path), subfontIndex=subfont_index)
            )
            break
        else:
            raise RuntimeError("未找到可嵌入的中文字体，不能安全导出 PDF")
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("ExamTitle", parent=base["Title"], fontName=PDF_FONT_NAME, fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=8),
        "body": ParagraphStyle("ExamBody", parent=base["BodyText"], fontName=PDF_FONT_NAME, fontSize=10.5, leading=16, spaceAfter=4),
        "section": ParagraphStyle("ExamSection", parent=base["Heading2"], fontName=PDF_FONT_NAME, fontSize=13, leading=18, spaceBefore=8, spaceAfter=5),
        "question": ParagraphStyle("ExamQuestion", parent=base["BodyText"], fontName=PDF_FONT_NAME, fontSize=10.5, leading=16, spaceAfter=3, keepWithNext=True),
        "small": ParagraphStyle("ExamSmall", parent=base["BodyText"], fontName=PDF_FONT_NAME, fontSize=9, leading=12, textColor=colors.HexColor("#555555"), spaceAfter=3),
    }


def _pdf_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _pdf_table(rows: list[list[Any]], styles: dict[str, ParagraphStyle]) -> Table | None:
    if not rows:
        return None
    column_count = max(len(row) for row in rows)
    data = [
        [_pdf_paragraph(str(row[index]) if index < len(row) else "", styles["body"]) for index in range(column_count)]
        for row in rows
    ]
    table = Table(data, colWidths=[16.6 * cm / column_count] * column_count, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _add_pdf_question(story: list[Any], row: Any, options: ExportOptions, styles: dict[str, ParagraphStyle]) -> None:
    number = _value(row, "sequence", default=0)
    points = _value(row, "points", default=0)
    block: list[Any] = [
        _pdf_paragraph(f"{number}. {_question_value(row, 'text', default='')}（{points:g} 分）", styles["question"])
    ]
    for option in _question_value(row, "options", default=[]) or []:
        block.append(_pdf_paragraph(f"{_value(option, 'label', default='')}. {_value(option, 'text', default='')}", styles["body"]))
    for formula in _iter_formulas(row):
        block.append(_pdf_paragraph(f"公式：{formula}", styles["small"]))
    for table_rows in _iter_tables(row):
        table = _pdf_table(table_rows, styles)
        if table:
            block.append(table)
            block.append(Spacer(1, 3))
    for image, alt in _iter_images(row, options):
        picture = PdfImage(io.BytesIO(image), width=10 * cm, height=6 * cm, kind="proportional")
        picture.hAlign = "CENTER"
        block.extend([picture, _pdf_paragraph(alt, styles["small"])])
    story.append(KeepTogether(block))


def _render_pdf(paper: Any, variant: ExportVariant, options: ExportOptions) -> bytes:
    styles = _pdf_styles()
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    story: list[Any] = [_pdf_paragraph(_paper_title(paper, variant), styles["title"])]
    if options.include_student_fields:
        info = Table([["姓名：____________", "学号：____________", "班级：____________"]], colWidths=[5.53 * cm] * 3)
        info.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")), ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_NAME), ("FONTSIZE", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        story.extend([info, Spacer(1, 6)])
    metadata = "  ".join(item for item in [f"课程：{_subject_name(paper)}" if _subject_name(paper) else "", f"考试时间：{_value(paper, 'duration_minutes', 'durationMinutes', default='未限定')} 分钟", f"满分：{_value(paper, 'total_points', 'totalPoints', default=0):g} 分"] if item)
    story.append(_pdf_paragraph(metadata, styles["body"]))
    rows = _paper_questions(paper)
    if variant == "answer-sheet":
        for row in rows:
            story.append(_pdf_paragraph(f"{_value(row, 'sequence', default=0)}. （{_value(row, 'points', default=0):g} 分）", styles["question"]))
            lines = 3 if _question_value(row, "question_type", "questionType", default="") in {"简答题", "计算题"} else 1
            for _ in range(lines):
                story.append(_pdf_paragraph("________________________________________________________________________", styles["body"]))
    else:
        previous_section = None
        for row in rows:
            section_title = str(_value(row, "section_title", "sectionTitle", default=""))
            if section_title and section_title != previous_section:
                story.append(_pdf_paragraph(section_title, styles["section"]))
                previous_section = section_title
            _add_pdf_question(story, row, options, styles)
    if variant == "answers":
        story.append(_pdf_paragraph("参考答案", styles["section"]))
        for row in rows:
            story.append(_pdf_paragraph(f"{_value(row, 'sequence', default=0)}. 正确答案：{_answer_text(_question_value(row, 'correct_answer', 'correctAnswer'))}", styles["question"]))
            explanation = _question_value(row, "explanation")
            if explanation:
                story.append(_pdf_paragraph(f"解析：{explanation}", styles["body"]))

    def add_page_number(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont(PDF_FONT_NAME, 9)
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.0 * cm, f"第 {doc.page} 页")
        canvas.restoreState()

    document.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return output.getvalue()
