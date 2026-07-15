from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Assignment, Student, Submission


FORMAL_HISTORY_STATUSES = ("published", "closed")


def recalculate_formal_average(session: Session, student_id: str) -> float:
    """Persist the latest graded formal result for each published or closed assignment."""
    rows = session.execute(
        select(Submission, Assignment)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(
            Submission.student_id == student_id,
            Submission.status == "graded",
            Submission.score.is_not(None),
            Assignment.status.in_(FORMAL_HISTORY_STATUSES),
        )
    ).all()
    latest: dict[str, tuple[Submission, Assignment]] = {}
    for submission, assignment in rows:
        current = latest.get(assignment.id)
        if current is None or submission.attempt_number > current[0].attempt_number:
            latest[assignment.id] = (submission, assignment)
    values = [
        submission.score / assignment.total_points * 100
        for submission, assignment in latest.values()
        if assignment.total_points > 0
    ]
    average = sum(values) / len(values) if values else 0.0
    student = session.get(Student, student_id)
    if student is not None:
        student.average_score = average
    return average
