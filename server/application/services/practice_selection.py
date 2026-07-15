from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from random import Random
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..errors import APIError
from ..models import KnowledgePoint, PracticeAttempt, PracticeSession, PracticeSessionQuestion, Question, QuestionKnowledgePoint, Subject


SOLUTION_FIELDS = {"correctAnswer", "correct_answer", "rubric", "explanation"}


def sanitize_snapshot(snapshot: dict[str, Any], include_solutions: bool = False) -> dict[str, Any]:
    payload = deepcopy(snapshot)
    if not include_solutions:
        for field in SOLUTION_FIELDS:
            payload.pop(field, None)
    return payload


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
        recency = attempted_at.timestamp() if status and attempted_at.tzinfo else (attempted_at.timestamp() if status else 0)
        return status, -recency if status == 2 else randomized[question.id], randomized[question.id], question.id
    return sorted(questions, key=rank)[:count]
