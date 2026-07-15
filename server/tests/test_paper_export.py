from __future__ import annotations

import base64
import io
import json
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from server.tests.test_teacher import teacher_context
from server.tests.test_teacher_papers import create_manual_paper, csrf, seed_question


FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "export_expected.json").read_text())
PNG_DATA_URI = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAgCAIAAADbtmxLAAAAaUlEQVR4nO3XsQ3DQAzAQD7hebKK50iR"
    "KTKCCy+VKhNlhHeRggb+agEi1Gns7w8lEiMxEiMxEiMxErNdGTpfj78sex7f+11IYiRGYiRGYiRGYiRG"
    "YiRGYiRGYiRmrL9sYgXNrKCZFcTED+GoBn1Ws7ToAAAAAElFTkSuQmCC"
)


@pytest.fixture()
def sample_paper() -> dict:
    return {
        "title": FIXTURE["title"],
        "subject": {"name": FIXTURE["subject"]},
        "durationMinutes": 90,
        "totalPoints": 30,
        "paperQuestions": [
            {
                "sectionTitle": "一、选择题",
                "sequence": 1,
                "points": 5,
                "question": {
                    "text": "达西定律适用于下列哪种渗流状态？",
                    "questionType": "单项选择题",
                    "options": [{"label": "A", "text": "层流"}, {"label": "B", "text": "紊流"}],
                    "correctAnswer": "A",
                    "explanation": "达西定律描述层流渗透。",
                    "attachments": [{"kind": "image", "url": PNG_DATA_URI, "alt": "渗流示意图"}],
                    "sourceMetadata": {"formulas": ["q = k A i"]},
                },
            },
            {
                "sectionTitle": "二、综合题",
                "sequence": 2,
                "points": 25,
                "question": {
                    "text": "说明渗透系数的物理意义，并根据下表计算渗流量。",
                    "questionType": "计算题",
                    "options": [],
                    "correctAnswer": {"value": "0.002 m3/s"},
                    "explanation": "先确定水力坡降，再代入 q = kAi。",
                    "rubric": [{"criterion": "列出公式", "points": 10}, {"criterion": "计算结果", "points": 15}],
                    "attachments": [{"kind": "table", "rows": [["参数", "数值"], ["k", "1e-4 m/s"], ["A", "20 m2"]]}],
                    "sourceMetadata": {"tables": [[["参数", "数值"], ["i", "0.01"]]], "formulas": ["q = k A i"]},
                },
            },
        ],
    }


def extract_docx_text(content: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs) + "\n" + "\n".join(
        cell.text for table in document.tables for row in table.rows for cell in row.cells
    )


def extract_pdf_text(content: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)


@pytest.mark.parametrize("format", ["docx", "pdf"])
def test_question_exports_include_structured_question_content_without_answers(sample_paper, format: str) -> None:
    from server.application.services.paper_export import ExportOptions, render_paper

    content = render_paper(sample_paper, "questions", format, ExportOptions())
    text = extract_docx_text(content) if format == "docx" else extract_pdf_text(content)
    assert FIXTURE["title"] in text
    assert FIXTURE["duration"] in text
    assert FIXTURE["total"] in text
    assert "一、选择题" in text
    assert "二、综合题" in text
    assert "A. 层流" in text
    assert "q = k A i" in text
    assert FIXTURE["answer_heading"] not in text
    assert FIXTURE["correct_answer"] not in text
    assert "0.002 m3/s" not in text


def test_docx_question_export_has_embedded_media_and_tables(sample_paper) -> None:
    from server.application.services.paper_export import ExportOptions, render_paper

    content = render_paper(sample_paper, "questions", "docx", ExportOptions())
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = set(archive.namelist())
        document_xml = archive.read("word/document.xml")
        styles_xml = archive.read("word/styles.xml")
    assert any(name.startswith("word/media/") for name in names)
    assert b"<w:tbl" in document_xml
    assert b"<w:hyperlink" not in document_xml
    assert b'cx="1800000"' in document_xml
    for slot in (b"ascii", b"hAnsi", b"eastAsia", b"cs"):
        assert slot + b'="Arial Unicode MS"' in document_xml + styles_xml


def test_pdf_question_export_embeds_a_chinese_font_for_portable_rendering(sample_paper) -> None:
    from server.application.services.paper_export import ExportOptions, render_paper

    content = render_paper(sample_paper, "questions", "pdf", ExportOptions())
    assert b"/FontFile2" in content


def test_answer_sheet_and_answers_variants_are_intentionally_distinct(sample_paper) -> None:
    from server.application.services.paper_export import ExportOptions, render_paper

    answer_sheet = extract_docx_text(
        render_paper(sample_paper, "answer-sheet", "docx", ExportOptions())
    )
    answers = extract_docx_text(render_paper(sample_paper, "answers", "docx", ExportOptions()))
    assert answer_sheet.count(FIXTURE["answer_sheet_heading"]) == 1
    assert "正确答案：A" not in answer_sheet
    assert FIXTURE["answer_heading"] in answers
    assert FIXTURE["correct_answer"] in answers
    assert "0.002 m3/s" in answers


def test_export_endpoint_requires_owner_streams_rfc5987_filename_and_audits(teacher_context) -> None:
    from server.application.models import OperationLog
    from server.tests.test_teacher_catalog import teacher2_client

    client, database, _ = teacher_context
    paper = create_manual_paper(client, [seed_question(database, "export-owned-question")])
    response = client.get(
        f"/api/teacher/papers/{paper['id']}/export?format=pdf&variant=answers",
        headers=csrf(),
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/pdf")
    assert "filename*=UTF-8''" in response.headers["content-disposition"]
    assert "%E5%9C%9F" in response.headers["content-disposition"]
    assert extract_pdf_text(response.content).count("参考答案") == 1

    other = teacher2_client(client, database)
    denied = other.get(
        f"/api/teacher/papers/{paper['id']}/export?format=docx&variant=questions",
        headers=csrf("teacher-2-csrf"),
    )
    assert denied.status_code == 404
    assert denied.json()["code"] == "PAPER_NOT_FOUND"

    with database.session() as session:
        logs = session.scalars(
            select(OperationLog).where(
                OperationLog.action == "paper.export", OperationLog.target_id == paper["id"]
            )
        ).all()
    assert len(logs) == 1
    assert logs[0].detail == {"format": "pdf", "variant": "answers"}
