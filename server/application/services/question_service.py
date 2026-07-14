from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import APIError
from ..models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject
from .assessment_validation import AssessmentValidationError, ValidatedQuestion, normalize_text, validate_question


@dataclass(frozen=True)
class PreparedQuestion:
    validated: ValidatedQuestion
    explanation: str | None
    rubric: list[dict[str, Any]]
    attachments: list[dict[str, Any]]


def _legacy_payload(payload: dict[str, Any], session: Session, actor_id: str) -> dict[str, Any]:
    knowledge_point_name = payload.get("knowledgePoint")
    if not isinstance(knowledge_point_name, str) or not knowledge_point_name.strip():
        raise APIError(422, "旧题目载荷必须提供知识点", "KNOWLEDGE_POINT_REQUIRED")
    point = resolve_or_create_legacy_point(session, knowledge_point_name, payload.get("chapter"), actor_id)
    question_type = payload.get("questionType")
    converted = {
        "subjectId": "foundation-engineering",
        "knowledgePointIds": [point.id],
        "text": payload.get("text"),
        "questionType": question_type,
        "chapter": payload.get("chapter"),
        "difficulty": payload.get("difficulty", "基础"),
        "options": payload.get("options", []),
        "correctAnswer": payload.get("correctAnswer"),
        "points": payload.get("points", 10),
        "answerWordLimit": payload.get("answerWordLimit"),
        "gradingMode": payload.get("gradingMode", "auto"),
    }
    if question_type == "简答题":
        converted["correctAnswer"] = None
        converted["answerWordLimit"] = converted["answerWordLimit"] or 200
    return converted


def resolve_or_create_legacy_point(session: Session, name: str, chapter: object, actor_id: str) -> KnowledgePoint:
    normalized_name = normalize_text(name)
    if not normalized_name:
        raise APIError(422, "知识点不能为空", "KNOWLEDGE_POINT_REQUIRED")
    point = session.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.subject_id == "foundation-engineering",
            KnowledgePoint.normalized_name == normalized_name,
        )
    )
    if point is not None:
        return point
    point = KnowledgePoint(
        id=str(uuid4()), subject_id="foundation-engineering",
        chapter=chapter.strip() if isinstance(chapter, str) and chapter.strip() else "未分章",
        name=" ".join(name.split()), normalized_name=normalized_name, created_by=actor_id,
    )
    session.add(point)
    session.flush()
    return point


def prepare_question(payload: dict[str, Any], session: Session, actor_id: str) -> PreparedQuestion:
    raw = dict(payload)
    explanation = raw.pop("explanation", None)
    rubric = raw.pop("rubric", [])
    attachments = raw.pop("attachments", [])
    if "knowledgePointIds" not in raw and "knowledgePoint" in raw:
        raw = _legacy_payload({**raw, "knowledgePoint": raw["knowledgePoint"]}, session, actor_id)
    elif "knowledgePoint" in raw:
        raw.pop("knowledgePoint")
    if not isinstance(explanation, str | type(None)):
        raise APIError(422, "题目解析格式无效", "QUESTION_PAYLOAD_INVALID")
    if not isinstance(rubric, list) or not isinstance(attachments, list):
        raise APIError(422, "题目扩展字段格式无效", "QUESTION_PAYLOAD_INVALID")
    try:
        validated = validate_question(raw)
    except AssessmentValidationError as exc:
        raise APIError(422, str(exc), exc.code) from exc
    subject = session.get(Subject, validated.subject_id)
    if subject is None:
        raise APIError(404, "课程不存在", "SUBJECT_NOT_FOUND")
    if subject.status != "active":
        raise APIError(409, "课程当前不可用于出题", "SUBJECT_INACTIVE")
    points = session.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(validated.knowledge_point_ids))).all()
    by_id = {point.id: point for point in points}
    if len(by_id) != len(validated.knowledge_point_ids):
        raise APIError(404, "知识点不存在", "KNOWLEDGE_POINT_NOT_FOUND")
    if any(point.subject_id != validated.subject_id for point in by_id.values()):
        raise APIError(422, "知识点必须属于同一课程", "KNOWLEDGE_POINT_SUBJECT_MISMATCH")
    if any(point.status != "active" for point in by_id.values()):
        raise APIError(409, "只能关联启用的知识点", "KNOWLEDGE_POINT_INACTIVE")
    return PreparedQuestion(
        validated=validated,
        explanation=explanation.strip() if isinstance(explanation, str) else None,
        rubric=rubric,
        attachments=attachments,
    )


def apply_prepared_question(question: Question, prepared: PreparedQuestion, session: Session) -> None:
    value = prepared.validated
    question.text = value.text
    question.question_type = value.question_type
    question.subject_id = value.subject_id
    question.chapter = value.chapter
    question.difficulty = value.difficulty
    question.options = value.options
    question.correct_answer = value.correct_answer
    question.points = value.points
    question.answer_word_limit = value.answer_word_limit
    question.grading_mode = value.grading_mode
    question.explanation = prepared.explanation
    question.rubric = prepared.rubric
    question.attachments = prepared.attachments
    question.knowledge_point = None
    had_links = bool(question.knowledge_point_links)
    question.knowledge_point_links.clear()
    if had_links:
        question.status = "review_required"
        session.flush()
    question.status = "active"
    for point_id in value.knowledge_point_ids:
        question.knowledge_point_links.append(
            QuestionKnowledgePoint(id=str(uuid4()), knowledge_point_id=point_id, weight=1.0)
        )


def create_question(payload: dict[str, Any], session: Session, actor_id: str, source: str = "teacher") -> Question:
    prepared = prepare_question(payload, session, actor_id)
    question = Question(id=str(uuid4()), source=source, created_by=actor_id)
    session.add(question)
    apply_prepared_question(question, prepared, session)
    return question


def normalize_question_link_weights(session: Session, question_ids: set[str]) -> None:
    if not question_ids:
        return
    links = session.scalars(
        select(QuestionKnowledgePoint)
        .where(QuestionKnowledgePoint.question_id.in_(question_ids))
        .order_by(QuestionKnowledgePoint.question_id, QuestionKnowledgePoint.id)
    ).all()
    by_question: dict[str, list[QuestionKnowledgePoint]] = {}
    for link in links:
        by_question.setdefault(link.question_id, []).append(link)
    for records in by_question.values():
        weights = [max(float(record.weight), 0.0) for record in records]
        total = sum(weights)
        normalized = [1.0 / len(records)] * len(records) if total <= 0 else [weight / total for weight in weights]
        for record, weight in zip(records, normalized):
            record.weight = weight


def question_payload(question: Question, actor_id: str) -> dict[str, Any]:
    return {
        "id": question.id,
        "subjectId": question.subject_id,
        "chapter": question.chapter,
        "knowledgePoints": [
            {"id": link.knowledge_point.id, "name": link.knowledge_point.name, "weight": link.weight}
            for link in question.knowledge_point_links
        ],
        "questionType": question.question_type,
        "text": question.text,
        "options": question.options,
        "correctAnswer": question.correct_answer,
        "explanation": question.explanation,
        "rubric": question.rubric,
        "difficulty": question.difficulty,
        "points": question.points,
        "attachments": question.attachments,
        "answerWordLimit": question.answer_word_limit,
        "gradingMode": question.grading_mode,
        "status": question.status,
        "source": question.source,
        "createdBy": question.created_by,
        "editable": question.created_by == actor_id,
    }
