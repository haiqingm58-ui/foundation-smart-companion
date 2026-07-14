from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import Database
from ..models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject
from .assessment_validation import AssessmentValidationError, normalize_text, validate_question
from .audit import add_log


QUESTION_BANK_SOURCE = "soil-mechanics-bank"
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")


class QuestionBankImportError(ValueError):
    pass


@dataclass(frozen=True)
class ImportSummary:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    review: int = 0
    subject_id: str = ""

    def to_dict(self) -> dict[str, int | str]:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "review": self.review,
            "subjectId": self.subject_id,
        }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise QuestionBankImportError(message)


def _string(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip(), f"{label} 必须是非空字符串")
    return value.strip()


def _integer(value: object, label: str) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool), f"{label} 必须是整数")
    return value


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise QuestionBankImportError(f"无法读取题库清单：{manifest_path}") from error
    _require(isinstance(payload, dict), "题库清单根节点必须是对象")
    return payload


def _validate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    _require(manifest.get("schemaVersion") == 1, "题库清单 schemaVersion 必须为 1")

    subject = manifest.get("subject")
    _require(isinstance(subject, dict), "subject 必须是对象")
    subject_id = _string(subject.get("id"), "subject.id")
    _string(subject.get("title"), "subject.title")
    _string(subject.get("slug"), "subject.slug")
    _require(subject.get("status") in {"active", "inactive"}, "subject.status 无效")
    _integer(subject.get("sortOrder"), "subject.sortOrder")

    points = manifest.get("knowledgePoints")
    _require(isinstance(points, list), "knowledgePoints 必须是数组")
    point_ids: set[str] = set()
    normalized_names: set[str] = set()
    for point in points:
        _require(isinstance(point, dict), "知识点必须是对象")
        point_id = _string(point.get("id"), "knowledgePoint.id")
        _require(point_id not in point_ids, f"知识点 ID 重复：{point_id}")
        point_ids.add(point_id)
        _require(point.get("subjectId") == subject_id, f"{point_id}: 知识点课程无效")
        _string(point.get("chapter"), f"{point_id}.chapter")
        name = _string(point.get("name"), f"{point_id}.name")
        _string(point.get("description"), f"{point_id}.description")
        _require(point.get("status") in {"active", "inactive"}, f"{point_id}: 知识点状态无效")
        _integer(point.get("sortOrder"), f"{point_id}.sortOrder")
        normalized_name = normalize_text(name)
        _require(normalized_name and normalized_name not in normalized_names, f"{point_id}: 知识点名称重复")
        normalized_names.add(normalized_name)

    questions = manifest.get("questions")
    _require(isinstance(questions, list), "questions 必须是数组")
    question_ids: set[str] = set()
    fingerprints: set[str] = set()
    payload_keys = {
        "subjectId", "knowledgePointIds", "text", "questionType", "chapter", "difficulty",
        "options", "correctAnswer", "points", "answerWordLimit", "gradingMode",
    }
    for question in questions:
        _require(isinstance(question, dict), "题目必须是对象")
        question_id = _string(question.get("id"), "question.id")
        _require(question_id not in question_ids, f"题目 ID 重复：{question_id}")
        question_ids.add(question_id)
        fingerprint = question.get("contentFingerprint")
        _require(isinstance(fingerprint, str) and _FINGERPRINT.fullmatch(fingerprint) is not None, f"{question_id}: 内容指纹无效")
        _require(fingerprint not in fingerprints, f"{question_id}: 内容指纹重复")
        fingerprints.add(fingerprint)
        _require(question.get("subjectId") == subject_id, f"{question_id}: 题目课程无效")
        _require(question.get("status") == "active", f"{question_id}: 题库只能导入 active 题目")
        linked_point_ids = question.get("knowledgePointIds")
        _require(
            isinstance(linked_point_ids, list)
            and 1 <= len(linked_point_ids) <= 3
            and len(set(linked_point_ids)) == len(linked_point_ids)
            and all(point_id in point_ids for point_id in linked_point_ids),
            f"{question_id}: 题目引用了未编目知识点",
        )
        _require(question.get("explanation") is None or isinstance(question.get("explanation"), str), f"{question_id}: explanation 无效")
        _require(isinstance(question.get("rubric"), list) and all(isinstance(item, dict) for item in question["rubric"]), f"{question_id}: rubric 无效")
        _require(isinstance(question.get("attachments"), list) and all(isinstance(item, dict) for item in question["attachments"]), f"{question_id}: attachments 无效")
        _require(isinstance(question.get("sourceMetadata"), dict), f"{question_id}: sourceMetadata 无效")
        try:
            validate_question({key: question.get(key) for key in payload_keys})
        except AssessmentValidationError as error:
            raise QuestionBankImportError(f"{question_id}: {error.code}: {error}") from error
    return manifest


def _link_id(question_id: str, knowledge_point_id: str) -> str:
    digest = hashlib.sha256(f"{question_id}:{knowledge_point_id}".encode("utf-8")).hexdigest()
    return f"question-knowledge-point-{digest}"


def _set_value(record: object, attribute: str, value: object) -> bool:
    if getattr(record, attribute) == value:
        return False
    setattr(record, attribute, value)
    return True


def _prepare_existing_records(session, manifest: dict[str, Any]) -> tuple[dict[str, Question], dict[str, Question]]:
    question_ids = [question["id"] for question in manifest["questions"]]
    fingerprints = [question["contentFingerprint"] for question in manifest["questions"]]
    by_id = {
        question.id: question
        for question in session.scalars(
            select(Question)
            .options(selectinload(Question.knowledge_point_links))
            .where(Question.id.in_(question_ids))
        )
    }
    by_fingerprint = {
        question.content_fingerprint: question
        for question in session.scalars(
            select(Question)
            .options(selectinload(Question.knowledge_point_links))
            .where(Question.source == QUESTION_BANK_SOURCE, Question.content_fingerprint.in_(fingerprints))
        )
        if question.content_fingerprint is not None
    }
    for payload in manifest["questions"]:
        identified = by_id.get(payload["id"])
        fingerprinted = by_fingerprint.get(payload["contentFingerprint"])
        _require(
            identified is None or identified.source == QUESTION_BANK_SOURCE,
            f"{payload['id']}: 稳定题目 ID 已由其他来源占用",
        )
        _require(
            identified is None or fingerprinted is None or identified.id == fingerprinted.id,
            f"{payload['id']}: 题目 ID 与内容指纹指向不同共享题目",
        )
    return by_id, by_fingerprint


def _upsert_subject(session, payload: dict[str, Any]) -> None:
    subject = session.get(Subject, payload["id"])
    if subject is None:
        session.add(Subject(id=payload["id"], title=payload["title"], slug=payload["slug"], status=payload["status"], sort_order=payload["sortOrder"]))
        return
    _set_value(subject, "title", payload["title"])
    _set_value(subject, "slug", payload["slug"])
    _set_value(subject, "status", payload["status"])
    _set_value(subject, "sort_order", payload["sortOrder"])


def _upsert_points(session, payloads: list[dict[str, Any]], subject_id: str) -> None:
    existing = {
        point.id: point
        for point in session.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_([payload["id"] for payload in payloads])))
    }
    occupied_names = {
        point.normalized_name: point.id
        for point in session.scalars(select(KnowledgePoint).where(KnowledgePoint.subject_id == subject_id))
    }
    for payload in payloads:
        point = existing.get(payload["id"])
        normalized_name = normalize_text(payload["name"])
        _require(point is None or point.subject_id == subject_id, f"{payload['id']}: 稳定知识点 ID 已由其他课程占用")
        _require(occupied_names.get(normalized_name) in {None, payload["id"]}, f"{payload['id']}: 知识点名称已由其他记录占用")
        if point is None:
            session.add(
                KnowledgePoint(
                    id=payload["id"], subject_id=subject_id, chapter=payload["chapter"], name=payload["name"],
                    normalized_name=normalized_name, description=payload["description"], status=payload["status"],
                    sort_order=payload["sortOrder"], created_by=None,
                )
            )
            continue
        _set_value(point, "chapter", payload["chapter"])
        _set_value(point, "name", payload["name"])
        _set_value(point, "normalized_name", normalized_name)
        _set_value(point, "description", payload["description"])
        _set_value(point, "status", payload["status"])
        _set_value(point, "sort_order", payload["sortOrder"])
        _set_value(point, "created_by", None)


def _apply_question(question: Question, payload: dict[str, Any]) -> bool:
    changed = False
    values = {
        "text": payload["text"], "question_type": payload["questionType"], "options": payload["options"],
        "correct_answer": payload["correctAnswer"], "explanation": payload["explanation"], "rubric": payload["rubric"],
        "difficulty": payload["difficulty"], "points": float(payload["points"]), "chapter": payload["chapter"],
        "knowledge_point": None, "subject_id": payload["subjectId"], "attachments": payload["attachments"],
        "answer_word_limit": payload["answerWordLimit"], "grading_mode": payload["gradingMode"], "status": "active",
        "source_metadata": payload["sourceMetadata"], "content_fingerprint": payload["contentFingerprint"],
        "source": QUESTION_BANK_SOURCE, "created_by": None,
    }
    for attribute, value in values.items():
        changed = _set_value(question, attribute, value) or changed
    desired_point_ids = payload["knowledgePointIds"]
    desired_weights = {point_id: 1.0 / len(desired_point_ids) for point_id in desired_point_ids}
    existing_links = {link.knowledge_point_id: link for link in question.knowledge_point_links}
    for point_id, link in list(existing_links.items()):
        if point_id not in desired_weights:
            question.knowledge_point_links.remove(link)
            changed = True
    for point_id, weight in desired_weights.items():
        link = existing_links.get(point_id)
        if link is None:
            question.knowledge_point_links.append(
                QuestionKnowledgePoint(id=_link_id(question.id, point_id), knowledge_point_id=point_id, weight=weight)
            )
            changed = True
            continue
        changed = _set_value(link, "weight", weight) or changed
    return changed


def import_question_bank(database: Database, manifest_path: Path, actor_id: str | None) -> ImportSummary:
    """Validate one manifest, then atomically upsert its shared catalog records."""
    manifest_path = Path(manifest_path)
    manifest = _validate_manifest(manifest_path)
    subject_id = manifest["subject"]["id"]
    created = updated = unchanged = 0

    with database.session() as session:
        with session.begin():
            existing_by_id, existing_by_fingerprint = _prepare_existing_records(session, manifest)
            _upsert_subject(session, manifest["subject"])
            _upsert_points(session, manifest["knowledgePoints"], subject_id)
            for payload in manifest["questions"]:
                question = existing_by_id.get(payload["id"]) or existing_by_fingerprint.get(payload["contentFingerprint"])
                if question is None:
                    question = Question(id=payload["id"])
                    session.add(question)
                    _apply_question(question, payload)
                    created += 1
                elif _apply_question(question, payload):
                    updated += 1
                else:
                    unchanged += 1
            summary = ImportSummary(created=created, updated=updated, unchanged=unchanged, subject_id=subject_id)
            add_log(session, actor_id, "question_bank.import", "question_bank", subject_id, summary.to_dict())
        session.commit()
    return summary
