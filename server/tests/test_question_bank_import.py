from __future__ import annotations

import json
import os
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
from alembic.util import CommandError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from server.application.database import create_database
from server.application.importers.question_normalization import content_fingerprint
from server.application.migrations import upgrade_database
from server.application.models import KnowledgePoint, OperationLog, Question, QuestionKnowledgePoint, Subject, User


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_MANIFEST = PROJECT_ROOT / "content/question-banks/soil-mechanics/manifest.json"
POSTGRES_TEST_URL = os.getenv("FOUNDATION_TEST_POSTGRES_URL")


@pytest.fixture()
def database(database_url: str):
    upgrade_database(database_url)
    return create_database(database_url)


@pytest.fixture()
def soil_manifest(tmp_path: Path) -> Path:
    def source_block(text: str, block_index: int) -> list[dict]:
        return [{
            "kind": "paragraph", "role": "stem", "sourcePosition": {"blockIndex": block_index, "paragraphIndex": block_index},
            "text": text, "textWithPlaceholders": text, "inlineContent": [{"kind": "text", "text": text}],
        }]

    def question(identifier: str, text: str, question_type: str, options: list[dict], answer: object, point_ids: list[str], block_index: int) -> dict:
        attachments: list[dict] = []
        return {
            "id": identifier, "subjectId": "soil-mechanics", "knowledgePointIds": point_ids,
            "text": text, "questionType": question_type, "chapter": "第一章" if block_index == 1 else "第三章",
            "difficulty": "基础" if block_index == 1 else "中等", "options": options, "correctAnswer": answer,
            "points": 10, "answerWordLimit": None, "gradingMode": "auto", "explanation": None, "rubric": [],
            "attachments": attachments, "sourceBlocks": source_block(text, block_index),
            "sourceMetadata": {"file": "fixture.docx", "position": {"blockIndex": block_index}, "sequence": block_index},
            "contentFingerprint": content_fingerprint(text, options, attachments), "status": "active",
        }

    manifest = {
        "schemaVersion": 1,
        "subject": {"id": "soil-mechanics", "title": "土力学", "slug": "soil-mechanics", "status": "active", "sortOrder": 1},
        "knowledgePoints": [
            {"id": "sm-effective-stress", "subjectId": "soil-mechanics", "chapter": "第一章", "name": "有效应力", "description": "土中有效应力原理。", "status": "active", "sortOrder": 1},
            {"id": "sm-shear-strength", "subjectId": "soil-mechanics", "chapter": "第三章", "name": "抗剪强度", "description": "土的抗剪强度。", "status": "active", "sortOrder": 2},
        ],
        "questions": [
            question("soil-effective-stress-choice", "有效应力原理中的有效应力由什么承担？", "单项选择题", [{"label": "A", "text": "土骨架"}, {"label": "B", "text": "孔隙水"}], "A", ["sm-effective-stress"], 1),
            question("soil-shear-strength-choice", "土的抗剪强度主要由哪些因素决定？", "多项选择题", [{"label": "A", "text": "黏聚力"}, {"label": "B", "text": "内摩擦角"}], ["A", "B"], ["sm-effective-stress", "sm-shear-strength"], 2),
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")


def database_counts(database) -> dict[str, int]:
    with database.session() as session:
        return {
            "subjects": session.scalar(select(func.count(Subject.id))),
            "points": session.scalar(select(func.count(KnowledgePoint.id))),
            "questions": session.scalar(select(func.count(Question.id))),
            "links": session.scalar(select(func.count(QuestionKnowledgePoint.id))),
            "logs": session.scalar(select(func.count(OperationLog.id))),
        }


def replace_with_missing_image(manifest: dict) -> None:
    question = manifest["questions"][0]
    attachment = {
        "kind": "image", "sha256": "0" * 64,
        "src": "/foundation-smart-companion/question-assets/soil-mechanics/" + "0" * 64 + ".png",
        "sourcePosition": {"blockIndex": 1}, "inlineOrdinal": 1, "placeholder": "[[attachment:1]]",
    }
    question["attachments"] = [attachment]
    question["contentFingerprint"] = content_fingerprint(question["text"], question["options"], question["attachments"])


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
    assert imported.attachments == []
    assert imported.source_metadata["sourceEvidence"] == "richer"
    assert imported.content_fingerprint == content_fingerprint(imported.text, imported.options, imported.attachments)


def test_invalid_manifest_link_rolls_back_without_persisting_any_records(database, soil_manifest: Path) -> None:
    from server.application.services.question_bank_import import QuestionBankImportError, import_question_bank

    manifest = load_manifest(soil_manifest)
    manifest["questions"][1]["knowledgePointIds"] = ["missing-point"]
    write_manifest(soil_manifest, manifest)
    before = database_counts(database)

    with pytest.raises(QuestionBankImportError, match="未编目知识点"):
        import_question_bank(database, soil_manifest, None)

    assert database_counts(database) == before


@pytest.mark.parametrize(("mutate", "message"), [
    (lambda manifest: manifest["questions"][0].__setitem__("contentFingerprint", "0" * 64), "内容指纹不匹配"),
    (lambda manifest: manifest["subject"].__setitem__("sortOrder", "1"), "subject.sortOrder"),
    (lambda manifest: manifest.__setitem__("sourceArchiveSha256", "not-a-sha256"), "sourceArchiveSha256"),
    (lambda manifest: manifest["questions"][0]["sourceMetadata"].pop("sequence"), "缺少源顺序"),
    (lambda manifest: manifest["questions"][0]["sourceBlocks"][0].__setitem__("textWithPlaceholders", "损坏的来源块"), "无法按顺序重构"),
    (lambda manifest: manifest["questions"][0].__setitem__("explanation", ["invalid"]), "explanation"),
    (lambda manifest: manifest["questions"][0].__setitem__("rubric", ["invalid"]), "rubric"),
    (replace_with_missing_image, "图像资产不存在"),
])
def test_manifest_schema_v1_rejections_write_nothing(database, soil_manifest: Path, mutate, message: str) -> None:
    from server.application.services.question_bank_import import QuestionBankImportError, import_question_bank

    manifest = load_manifest(soil_manifest)
    mutate(manifest)
    write_manifest(soil_manifest, manifest)
    before = database_counts(database)

    with pytest.raises(QuestionBankImportError, match=message):
        import_question_bank(database, soil_manifest, None)

    assert database_counts(database) == before


def test_invalid_manifest_is_rejected_before_opening_a_database_session(database, soil_manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from server.application.services.question_bank_import import QuestionBankImportError, import_question_bank

    manifest = load_manifest(soil_manifest)
    manifest["questions"][0]["sourceMetadata"].pop("sequence")
    write_manifest(soil_manifest, manifest)

    def session_must_not_open():
        raise AssertionError("invalid manifest opened a database session")

    monkeypatch.setattr(database, "session", session_must_not_open)
    with pytest.raises(QuestionBankImportError, match="缺少源顺序"):
        import_question_bank(database, soil_manifest, None)


@pytest.mark.parametrize(("created_by", "description"), [("teacher-user", "教师专用知识点"), (None, "同 ID 的未知共享知识点")])
def test_knowledge_point_collision_never_overwrites_existing_records(database, soil_manifest: Path, created_by: str | None, description: str) -> None:
    from server.application.services.question_bank_import import QuestionBankImportError, import_question_bank

    with database.session() as session:
        if created_by is not None:
            session.add(User(id=created_by, username=created_by, password_hash="hash", password_algorithm="argon2", role="teacher", role_label="教师", name="教师"))
            session.flush()
        session.add(KnowledgePoint(id="sm-effective-stress", subject_id="soil-mechanics", chapter="自定义章节", name="自定义知识点", normalized_name="自定义知识点", description=description, status="inactive", sort_order=99, created_by=created_by))
        session.commit()
    before = database_counts(database)

    with pytest.raises(QuestionBankImportError, match="无法确认属于共享题库"):
        import_question_bank(database, soil_manifest, None)

    with database.session() as session:
        point = session.get(KnowledgePoint, "sm-effective-stress")
    assert point is not None
    assert (point.chapter, point.name, point.description, point.status, point.sort_order, point.created_by) == ("自定义章节", "自定义知识点", description, "inactive", 99, created_by)
    assert database_counts(database) == before


def test_post_flush_failure_rolls_back_all_staged_records(database, soil_manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from server.application.services.question_bank_import import import_question_bank

    with database.session() as session:
        session.delete(session.get(Subject, "soil-mechanics"))
        session.commit()
    original_flush = Session.flush

    def fail_after_staging(self, *args, **kwargs):
        if any(isinstance(record, OperationLog) for record in self.new):
            raise SQLAlchemyError("injected flush failure")
        return original_flush(self, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", fail_after_staging)
    before = database_counts(database)

    with pytest.raises(SQLAlchemyError, match="injected flush failure"):
        import_question_bank(database, soil_manifest, None)

    assert database_counts(database) == before


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="FOUNDATION_TEST_POSTGRES_URL is not configured")
def test_postgresql_flush_failure_uses_the_same_transaction_path(tmp_path: Path, soil_manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from server.application.services.question_bank_import import import_question_bank

    upgrade_database(POSTGRES_TEST_URL)
    postgres_database = create_database(POSTGRES_TEST_URL)
    with postgres_database.session() as session:
        session.delete(session.get(Subject, "soil-mechanics"))
        session.commit()
    original_flush = Session.flush

    def fail_after_staging(self, *args, **kwargs):
        if any(isinstance(record, OperationLog) for record in self.new):
            raise SQLAlchemyError("injected flush failure")
        return original_flush(self, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", fail_after_staging)
    before = database_counts(postgres_database)
    with pytest.raises(SQLAlchemyError, match="injected flush failure"):
        import_question_bank(postgres_database, soil_manifest, None)
    assert database_counts(postgres_database) == before


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


@pytest.mark.parametrize("contents", ["{", json.dumps({"schemaVersion": 2})])
def test_cli_import_errors_are_structured_json_without_tracebacks(tmp_path: Path, database_url: str, contents: str) -> None:
    manifest_path = tmp_path / "invalid-manifest.json"
    manifest_path.write_text(contents, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "server.manage", "import-question-bank", str(manifest_path)],
        cwd=PROJECT_ROOT, env={**os.environ, "FOUNDATION_DATABASE_URL": database_url}, capture_output=True, text=True,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["error"]["code"] == "QUESTION_BANK_IMPORT_INVALID"
    assert "Traceback" not in result.stderr


def test_cli_formats_injected_import_and_database_failures(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    import server.manage as manage
    from server.application.services.question_bank_import import QuestionBankImportError

    monkeypatch.setattr(manage, "upgrade_database", lambda _url: None)
    monkeypatch.setattr(manage, "create_database", lambda _url: SimpleNamespace())
    monkeypatch.setattr(manage, "import_question_bank", lambda *_args: (_ for _ in ()).throw(QuestionBankImportError("injected import failure")))
    assert manage.main(["import-question-bank", str(tmp_path / "manifest.json")]) == 2
    assert json.loads(capsys.readouterr().out) == {"error": {"code": "QUESTION_BANK_IMPORT_INVALID", "message": "injected import failure"}}

    monkeypatch.setattr(manage, "upgrade_database", lambda _url: (_ for _ in ()).throw(SQLAlchemyError("injected database failure")))
    assert manage.main(["import-question-bank", str(tmp_path / "manifest.json")]) == 3
    assert json.loads(capsys.readouterr().out) == {"error": {"code": "QUESTION_BANK_DATABASE_FAILED", "message": "题库导入数据库操作失败"}}

    monkeypatch.setattr(manage, "upgrade_database", lambda _url: (_ for _ in ()).throw(CommandError("injected migration failure")))
    assert manage.main(["import-question-bank", str(tmp_path / "manifest.json")]) == 3
    assert json.loads(capsys.readouterr().out) == {"error": {"code": "QUESTION_BANK_DATABASE_FAILED", "message": "题库导入数据库操作失败"}}
