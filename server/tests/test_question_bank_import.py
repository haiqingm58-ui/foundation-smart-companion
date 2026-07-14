from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from server.application.database import create_database
from server.application.migrations import upgrade_database
from server.application.models import KnowledgePoint, OperationLog, Question, QuestionKnowledgePoint, Subject


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_MANIFEST = PROJECT_ROOT / "content/question-banks/soil-mechanics/manifest.json"


@pytest.fixture()
def database(database_url: str):
    upgrade_database(database_url)
    return create_database(database_url)


@pytest.fixture()
def soil_manifest(tmp_path: Path) -> Path:
    manifest = {
        "schemaVersion": 1,
        "subject": {"id": "soil-mechanics", "title": "土力学", "slug": "soil-mechanics", "status": "active", "sortOrder": 1},
        "knowledgePoints": [
            {"id": "sm-effective-stress", "subjectId": "soil-mechanics", "chapter": "第一章", "name": "有效应力", "description": "土中有效应力原理。", "status": "active", "sortOrder": 1},
            {"id": "sm-shear-strength", "subjectId": "soil-mechanics", "chapter": "第三章", "name": "抗剪强度", "description": "土的抗剪强度。", "status": "active", "sortOrder": 2},
        ],
        "questions": [
            {
                "id": "soil-effective-stress-choice", "subjectId": "soil-mechanics", "knowledgePointIds": ["sm-effective-stress"],
                "text": "有效应力原理中的有效应力由什么承担？", "questionType": "单项选择题", "chapter": "第一章",
                "difficulty": "基础", "options": [{"label": "A", "text": "土骨架"}, {"label": "B", "text": "孔隙水"}],
                "correctAnswer": "A", "points": 10, "answerWordLimit": None, "gradingMode": "auto",
                "explanation": None, "rubric": [], "attachments": [], "sourceMetadata": {"file": "fixture.docx", "position": {"blockIndex": 1}, "sequence": 1},
                "contentFingerprint": "a" * 64, "status": "active",
            },
            {
                "id": "soil-shear-strength-choice", "subjectId": "soil-mechanics", "knowledgePointIds": ["sm-effective-stress", "sm-shear-strength"],
                "text": "土的抗剪强度主要由哪些因素决定？", "questionType": "多项选择题", "chapter": "第三章",
                "difficulty": "中等", "options": [{"label": "A", "text": "黏聚力"}, {"label": "B", "text": "内摩擦角"}],
                "correctAnswer": ["A", "B"], "points": 10, "answerWordLimit": None, "gradingMode": "auto",
                "explanation": None, "rubric": [], "attachments": [], "sourceMetadata": {"file": "fixture.docx", "position": {"blockIndex": 2}, "sequence": 2},
                "contentFingerprint": "b" * 64, "status": "active",
            },
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")


def test_manifest_import_is_idempotent_and_records_shared_ownership(database, soil_manifest: Path) -> None:
    from server.application.services.question_bank_import import import_question_bank

    first = import_question_bank(database, soil_manifest, None)
    second = import_question_bank(database, soil_manifest, None)

    assert first.created == 2
    assert first.updated == first.unchanged == first.review == 0
    assert second.created == second.updated == second.review == 0
    assert second.unchanged == first.created
    with database.session() as session:
        subject = session.get(Subject, "soil-mechanics")
        questions = session.scalars(select(Question).order_by(Question.id)).all()
        points = session.scalars(select(KnowledgePoint).order_by(KnowledgePoint.id)).all()
        links = session.scalars(select(QuestionKnowledgePoint).order_by(QuestionKnowledgePoint.question_id, QuestionKnowledgePoint.knowledge_point_id)).all()
        logs = session.scalars(select(OperationLog).where(OperationLog.action == "question_bank.import").order_by(OperationLog.created_at)).all()

    assert subject is not None
    assert [(point.id, point.created_by) for point in points] == [("sm-effective-stress", None), ("sm-shear-strength", None)]
    assert [(question.id, question.source, question.status, question.created_by) for question in questions] == [
        ("soil-effective-stress-choice", "soil-mechanics-bank", "active", None),
        ("soil-shear-strength-choice", "soil-mechanics-bank", "active", None),
    ]
    assert [(link.question_id, link.knowledge_point_id, link.weight) for link in links] == [
        ("soil-effective-stress-choice", "sm-effective-stress", 1.0),
        ("soil-shear-strength-choice", "sm-effective-stress", 0.5),
        ("soil-shear-strength-choice", "sm-shear-strength", 0.5),
    ]
    assert len(logs) == 2
    assert logs[0].actor_id is None
    assert logs[0].detail == {"created": 2, "updated": 0, "unchanged": 0, "review": 0, "subjectId": "soil-mechanics"}
    assert logs[1].detail == {"created": 0, "updated": 0, "unchanged": 2, "review": 0, "subjectId": "soil-mechanics"}


def test_manifest_import_updates_a_richer_record_without_duplication(database, soil_manifest: Path) -> None:
    from server.application.services.question_bank_import import import_question_bank

    first = import_question_bank(database, soil_manifest, None)
    manifest = load_manifest(soil_manifest)
    question = manifest["questions"][0]
    question["explanation"] = "有效应力由土骨架承担。"
    question["attachments"] = [{"kind": "table", "rows": [["项目", "含义"]]}]
    question["sourceMetadata"]["sourceEvidence"] = "richer"
    write_manifest(soil_manifest, manifest)

    second = import_question_bank(database, soil_manifest, None)

    assert first.created == 2
    assert second.created == 0
    assert second.updated == 1
    assert second.unchanged == 1
    with database.session() as session:
        imported = session.get(Question, "soil-effective-stress-choice")
        assert session.scalar(select(func.count(Question.id))) == 2

    assert imported is not None
    assert imported.explanation == "有效应力由土骨架承担。"
    assert imported.attachments == [{"kind": "table", "rows": [["项目", "含义"]]}]
    assert imported.source_metadata["sourceEvidence"] == "richer"
    assert imported.content_fingerprint == "a" * 64


def test_invalid_manifest_link_rolls_back_without_persisting_any_records(database, soil_manifest: Path) -> None:
    from server.application.services.question_bank_import import QuestionBankImportError, import_question_bank

    manifest = load_manifest(soil_manifest)
    manifest["questions"][1]["knowledgePointIds"] = ["missing-point"]
    write_manifest(soil_manifest, manifest)
    with database.session() as session:
        before = {
            "subjects": session.scalar(select(func.count(Subject.id))),
            "points": session.scalar(select(func.count(KnowledgePoint.id))),
            "questions": session.scalar(select(func.count(Question.id))),
            "links": session.scalar(select(func.count(QuestionKnowledgePoint.id))),
            "logs": session.scalar(select(func.count(OperationLog.id))),
        }

    with pytest.raises(QuestionBankImportError, match="未编目知识点"):
        import_question_bank(database, soil_manifest, None)

    with database.session() as session:
        after = {
            "subjects": session.scalar(select(func.count(Subject.id))),
            "points": session.scalar(select(func.count(KnowledgePoint.id))),
            "questions": session.scalar(select(func.count(Question.id))),
            "links": session.scalar(select(func.count(QuestionKnowledgePoint.id))),
            "logs": session.scalar(select(func.count(OperationLog.id))),
        }
    assert after == before


def test_cli_import_reports_counts_derived_from_the_supplied_manifest(tmp_path: Path, database_url: str) -> None:
    manifest = load_manifest(REAL_MANIFEST)
    environment = {**os.environ, "FOUNDATION_DATABASE_URL": database_url}

    result = subprocess.run(
        [sys.executable, "-m", "server.manage", "import-question-bank", str(REAL_MANIFEST)],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == {
        "created": len(manifest["questions"]), "updated": 0, "unchanged": 0, "review": 0, "subjectId": manifest["subject"]["id"],
    }
