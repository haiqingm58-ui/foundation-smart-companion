from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import Database
from ..importers.report import ReportValidationError, validate_manifest
from ..models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject
from .assessment_validation import normalize_text
from .audit import add_log


QUESTION_BANK_SOURCE = "soil-mechanics-bank"


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


def _validate_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        return validate_manifest(manifest_path)
    except ReportValidationError as error:
        raise QuestionBankImportError(str(error)) from error


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


def _prepare_existing_points(session, payloads: list[dict[str, Any]], subject_id: str) -> dict[str, KnowledgePoint]:
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
        if point is not None:
            _require(
                point.created_by is None
                and (point.chapter, point.name, point.normalized_name, point.description, point.status, point.sort_order)
                == (payload["chapter"], payload["name"], normalize_text(payload["name"]), payload["description"], payload["status"], payload["sortOrder"]),
                f"{payload['id']}: 无法确认属于共享题库，拒绝覆盖现有知识点",
            )
    return existing


def _upsert_points(session, payloads: list[dict[str, Any]], subject_id: str, existing: dict[str, KnowledgePoint]) -> None:
    for payload in payloads:
        if payload["id"] in existing:
            continue
        session.add(
            KnowledgePoint(
                id=payload["id"], subject_id=subject_id, chapter=payload["chapter"], name=payload["name"],
                normalized_name=normalize_text(payload["name"]), description=payload["description"], status=payload["status"],
                sort_order=payload["sortOrder"], created_by=None,
            )
        )


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
            existing_points = _prepare_existing_points(session, manifest["knowledgePoints"], subject_id)
            _upsert_subject(session, manifest["subject"])
            _upsert_points(session, manifest["knowledgePoints"], subject_id, existing_points)
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
    return summary
