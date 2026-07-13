from __future__ import annotations

from dataclasses import dataclass
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
    weights = [allocation.weight if allocation.weight is not None else 1.0 for allocation in allocations]
    if any(weight <= 0 for weight in weights):
        raise ValueError("Mastery allocation weights must be positive")
    total_weight = sum(weights)
    point_ids = [allocation.knowledge_point_id for allocation in allocations]
    points = {
        point.id: point
        for point in session.scalars(select(KnowledgePoint).where(KnowledgePoint.id.in_(point_ids)))
    }
    if len(points) != len(set(point_ids)):
        raise ValueError("Mastery allocation references an unknown knowledge point")
    existing_rows = {
        row.knowledge_point_id: row
        for row in session.scalars(
            select(KnowledgeMastery).where(
                KnowledgeMastery.student_id == student_id,
                KnowledgeMastery.knowledge_point_id.in_(point_ids),
            )
        )
    }

    for allocation, weight in zip(allocations, weights, strict=True):
        point = points[allocation.knowledge_point_id]
        if point.subject_id != allocation.subject_id:
            raise ValueError("Mastery allocation subject does not match its knowledge point")
        normalized_weight = weight / total_weight
        row = existing_rows.get(allocation.knowledge_point_id)
        allocation_score = max(0.0, min(100.0, float(allocation.score))) * normalized_weight
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
