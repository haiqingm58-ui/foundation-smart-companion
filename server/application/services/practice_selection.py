from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from random import Random
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..errors import APIError
from ..models import KnowledgePoint, PracticeAttempt, PracticeSession, PracticeSessionQuestion, Question, QuestionKnowledgePoint, Subject


MAX_STUDENT_ANSWER_BYTES = 16 * 1024


def _safe_attachment(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    kind = item.get("kind")
    if kind == "image" and isinstance(item.get("src"), str):
        result = {"kind": "image", "src": item["src"]}
        for key in ("alt", "altText", "width", "height"):
            if isinstance(item.get(key), (str, int, float)):
                result[key] = item[key]
        return result
    if kind == "table" and isinstance(item.get("rows"), list):
        rows = item["rows"]
        if all(isinstance(row, list) and all(isinstance(cell, (str, int, float, bool)) or cell is None for cell in row) for row in rows):
            result = {"kind": "table", "rows": deepcopy(rows)}
            if isinstance(item.get("caption"), str):
                result["caption"] = item["caption"]
            return result
    if kind == "formula":
        formula = item.get("latex", item.get("ommlText"))
        if isinstance(formula, str):
            return {"kind": "formula", "latex": formula}
    return None


def student_safe_snapshot(snapshot: dict[str, Any], include_solutions: bool = False) -> dict[str, Any]:
    """Project a private snapshot to fields that are intentionally student-visible."""
    options = snapshot.get("options") if isinstance(snapshot.get("options"), list) else []
    attachments = [_safe_attachment(item) for item in snapshot.get("attachments", [])]
    payload: dict[str, Any] = {
        "id": snapshot.get("id"),
        "subjectId": snapshot.get("subjectId"),
        "text": snapshot.get("text", ""),
        "questionType": snapshot.get("questionType"),
        "options": [
            {"label": item.get("label"), "text": item.get("text")}
            for item in options
            if isinstance(item, dict) and isinstance(item.get("label"), str) and isinstance(item.get("text"), str)
        ],
        "difficulty": snapshot.get("difficulty"),
        "chapter": snapshot.get("chapter"),
        "knowledgePointIds": list(snapshot.get("knowledgePointIds") or []),
        "answerWordLimit": snapshot.get("answerWordLimit"),
        "sequence": snapshot.get("sequence"),
        "sectionTitle": snapshot.get("sectionTitle"),
        "points": snapshot.get("points"),
        "attachments": [item for item in attachments if item is not None],
    }
    if include_solutions:
        payload.update({
            "correctAnswer": deepcopy(snapshot.get("correctAnswer")),
            "explanation": snapshot.get("explanation"),
            "rubric": deepcopy(snapshot.get("rubric") or []),
        })
    return {key: value for key, value in payload.items() if value is not None}


def sanitize_snapshot(snapshot: dict[str, Any], include_solutions: bool = False) -> dict[str, Any]:
    """Backward-compatible name for the explicit student-safe projection."""
    return student_safe_snapshot(snapshot, include_solutions)


def validate_student_answer(snapshot: dict[str, Any], answer: Any) -> None:
    try:
        size = len(json.dumps(answer, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise APIError(422, "答案必须是有效 JSON", "ANSWER_INVALID") from exc
    if size > MAX_STUDENT_ANSWER_BYTES:
        raise APIError(413, "答案不能超过 16KB", "ANSWER_TOO_LARGE")
    if answer is None:
        return
    question_type = snapshot.get("questionType")
    labels = {
        str(option.get("label")).strip()
        for option in snapshot.get("options", [])
        if isinstance(option, dict) and isinstance(option.get("label"), str)
    }
    if question_type == "单项选择题":
        if not isinstance(answer, str) or answer.strip() not in labels:
            raise APIError(422, "请选择一个有效选项", "ANSWER_INVALID_SINGLE_CHOICE")
    elif question_type == "多项选择题":
        if not isinstance(answer, list) or not answer or not all(isinstance(item, str) and item.strip() in labels for item in answer) or len({item.strip() for item in answer}) != len(answer):
            raise APIError(422, "请选择不重复的有效选项", "ANSWER_INVALID_MULTIPLE_CHOICE")
    elif question_type == "判断题":
        if type(answer) is not bool:
            raise APIError(422, "判断题答案必须为布尔值", "ANSWER_INVALID_BOOLEAN")
    elif question_type == "填空题":
        if not isinstance(answer, str) or not answer.strip():
            raise APIError(422, "填空题答案必须是非空文本", "ANSWER_INVALID_FILL")
    elif question_type in {"简答题", "计算题"}:
        limit = snapshot.get("answerWordLimit") or 2000
        if not isinstance(answer, str) or len(answer.strip()) > int(limit):
            raise APIError(422, "答案文本无效或超过字数限制", "ANSWER_INVALID_TEXT")


def question_snapshot(question: Question, *, sequence: int | None = None, points: float | None = None) -> dict[str, Any]:
    snapshot = {
        "id": question.id,
        "subjectId": question.subject_id,
        "text": question.text,
        "questionType": question.question_type,
        "options": deepcopy(question.options),
        "correctAnswer": deepcopy(question.correct_answer),
        "explanation": question.explanation,
        "rubric": deepcopy(question.rubric),
        "difficulty": question.difficulty,
        "chapter": question.chapter,
        "knowledgePointIds": [link.knowledge_point_id for link in question.knowledge_point_links],
        "knowledgePointWeights": {link.knowledge_point_id: link.weight for link in question.knowledge_point_links},
        "attachments": deepcopy(question.attachments),
        "answerWordLimit": question.answer_word_limit,
        "gradingMode": question.grading_mode,
        "sourceMetadata": deepcopy(question.source_metadata),
        "points": points if points is not None else question.points,
    }
    if sequence is not None:
        snapshot["sequence"] = sequence
    return snapshot


def select_practice_questions(
    session: Session,
    *,
    student_id: str,
    subject_id: str,
    mode: str,
    chapter: str | None,
    knowledge_point_ids: list[str],
    question_types: list[str] | None = None,
    difficulties: list[str] | None = None,
    count: int,
    seed: int,
) -> list[Question]:
    subject = session.get(Subject, subject_id)
    if not subject or subject.status != "active":
        raise APIError(404, "课程不存在或不可用", "PRACTICE_SUBJECT_NOT_FOUND")
    if knowledge_point_ids:
        points = list(session.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(knowledge_point_ids))))
        if len(points) != len(knowledge_point_ids) or any(point.subject_id != subject_id for point in points):
            raise APIError(422, "知识点必须属于所选课程", "PRACTICE_KNOWLEDGE_POINT_SUBJECT_MISMATCH")
    statement = (
        select(Question)
        .options(selectinload(Question.knowledge_point_links))
        .where(Question.subject_id == subject_id, Question.status == "active")
    )
    if mode == "chapter":
        statement = statement.where(Question.chapter == chapter)
    else:
        statement = statement.join(QuestionKnowledgePoint).where(
            QuestionKnowledgePoint.knowledge_point_id.in_(knowledge_point_ids)
        )
    if question_types:
        statement = statement.where(Question.question_type.in_(question_types))
    if difficulties:
        statement = statement.where(Question.difficulty.in_(difficulties))
    questions = list(session.scalars(statement.distinct()).all())
    if len(questions) < count:
        raise APIError(409, f"符合条件的题目不足，需要 {count} 题，当前仅有 {len(questions)} 题", "PRACTICE_QUESTION_SHORTAGE")

    history: dict[str, tuple[int, datetime]] = {}
    for attempt in session.scalars(
        select(PracticeAttempt).where(PracticeAttempt.student_id == student_id).order_by(PracticeAttempt.submitted_at.desc())
    ):
        if attempt.question_id not in history:
            history[attempt.question_id] = (2 if attempt.score is not None and attempt.score >= attempt.max_score else 1, attempt.submitted_at)
    for item, practice in session.execute(
        select(PracticeSessionQuestion, PracticeSession)
        .join(PracticeSession, PracticeSession.id == PracticeSessionQuestion.session_id)
        .where(PracticeSession.student_id == student_id, PracticeSession.status.in_(("graded", "pending_review")))
        .order_by(PracticeSession.submitted_at.desc())
    ):
        if item.question_id not in history and practice.submitted_at is not None:
            history[item.question_id] = (2 if item.score is not None and item.score >= item.max_score else 1, practice.submitted_at)

    randomizer = Random(seed)
    randomized = {question.id: randomizer.random() for question in questions}
    def rank(question: Question) -> tuple[int, float, float, str]:
        status, attempted_at = history.get(question.id, (0, datetime.min))
        recency = attempted_at.timestamp() if status else 0
        return status, recency if status == 2 else randomized[question.id], randomized[question.id], question.id
    return sorted(questions, key=rank)[:count]
