from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import KnowledgeMastery, KnowledgePoint


@dataclass(frozen=True)
class MasteryAllocation:
    knowledge_point_id: str
    subject_id: str
    score: float
    weight: float | None = None


def apply_mastery(session: Session, student_id: str, allocations: list[MasteryAllocation]) -> None:
    if not allocations:
        return
    if not isinstance(student_id, str) or not student_id:
        raise ValueError("Mastery student ID must be a nonblank string")
    if not all(isinstance(allocation, MasteryAllocation) for allocation in allocations):
        raise ValueError("Mastery allocations must use MasteryAllocation")

    point_ids = [allocation.knowledge_point_id for allocation in allocations]
    if any(not isinstance(point_id, str) or not point_id for point_id in point_ids):
        raise ValueError("Mastery allocation knowledge-point IDs must be nonblank strings")
    if len(point_ids) != len(set(point_ids)):
        raise ValueError("Mastery allocations contain duplicate knowledge-point IDs")

    weights: list[float] = []
    scores: list[float] = []
    for allocation in allocations:
        if not isinstance(allocation.subject_id, str) or not allocation.subject_id:
            raise ValueError("Mastery allocation subject IDs must be nonblank strings")
        if isinstance(allocation.score, bool) or not isinstance(allocation.score, (int, float)) or not isfinite(allocation.score):
            raise ValueError("Mastery allocation scores must be finite numbers")
        score = float(allocation.score)
        if not 0 <= score <= 100:
            raise ValueError("Mastery allocation scores must be between zero and one hundred")
        scores.append(score)
        weight = 1.0 if allocation.weight is None else allocation.weight
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not isfinite(weight) or weight <= 0:
            raise ValueError("Mastery allocation weights must be positive finite numbers")
        weights.append(float(weight))

    points = {
        point.id: point
        for point in session.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(point_ids)))
    }
    if len(points) != len(set(point_ids)):
        raise ValueError("Mastery allocation references an unknown knowledge point")
    for allocation in allocations:
        if points[allocation.knowledge_point_id].subject_id != allocation.subject_id:
            raise ValueError("Mastery allocation subject does not match its knowledge point")

    total_weight = sum(weights)
    existing_rows = {
        row.knowledge_point_id: row
        for row in session.scalars(
            select(KnowledgeMastery).where(
                KnowledgeMastery.student_id == student_id,
                KnowledgeMastery.knowledge_point_id.in_(point_ids),
            )
        )
    }

    for allocation, weight, score in zip(allocations, weights, scores, strict=True):
        point = points[allocation.knowledge_point_id]
        normalized_weight = weight / total_weight
        row = existing_rows.get(allocation.knowledge_point_id)
        allocation_score = score * normalized_weight
        if row is None:
            row = KnowledgeMastery(
                id=str(uuid4()),
                student_id=student_id,
                subject_id=allocation.subject_id,
                knowledge_point_id=allocation.knowledge_point_id,
                knowledge_point=point.name,
                mastery=allocation_score,
                attempts=1,
            )
            session.add(row)
            continue
        row.mastery = (row.mastery * row.attempts + allocation_score) / (row.attempts + 1)
        row.attempts += 1
        row.subject_id = allocation.subject_id
