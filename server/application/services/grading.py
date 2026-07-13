from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .assessment_validation import normalize_boolean, normalize_choice_set, normalize_fill_answers, normalize_text


@dataclass(frozen=True)
class GradeResult:
    status: Literal["graded", "pending_review"]
    score: float | None
    max_score: float
    criteria_scores: dict[str, float]
    confidence: float
    feedback: str


def _snapshot_value(snapshot: dict, snake_name: str, camel_name: str, default=None):
    return snapshot.get(camel_name, snapshot.get(snake_name, default))


def _graded_result(correct: bool, points: float, feedback: str | None) -> GradeResult:
    return GradeResult(
        status="graded",
        score=points if correct else 0.0,
        max_score=points,
        criteria_scores={},
        confidence=1.0,
        feedback=feedback or ("回答正确" if correct else "答案不正确，请复习对应知识点"),
    )


def _pending_result(points: float) -> GradeResult:
    return GradeResult(
        status="pending_review",
        score=None,
        max_score=points,
        criteria_scores={},
        confidence=0.0,
        feedback="该题需教师复核后评分。",
    )


def grade_objective(question_snapshot: dict, answer: object) -> GradeResult:
    points = float(_snapshot_value(question_snapshot, "points", "points", 0) or 0)
    question_type = _snapshot_value(question_snapshot, "question_type", "questionType")
    correct_answer = _snapshot_value(question_snapshot, "correct_answer", "correctAnswer")
    feedback = _snapshot_value(question_snapshot, "explanation", "explanation")

    if question_type == "单项选择题":
        return _graded_result(normalize_text(answer) == normalize_text(correct_answer), points, feedback)
    if question_type == "多项选择题":
        expected = normalize_choice_set(correct_answer)
        actual = normalize_choice_set(answer)
        return _graded_result(expected is not None and actual == expected, points, feedback)
    if question_type == "判断题":
        expected = normalize_boolean(correct_answer)
        actual = normalize_boolean(answer)
        return _graded_result(expected is not None and actual == expected, points, feedback)
    if question_type == "填空题":
        return _graded_result(normalize_text(answer) in normalize_fill_answers(correct_answer), points, feedback)
    return _pending_result(points)
