from __future__ import annotations

from collections import Counter
from hashlib import sha256
from random import Random

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from ..models import Question, QuestionKnowledgePoint
from ..schemas.paper import (
    AssemblyPreview,
    AssemblyQuestion,
    AssemblyShortage,
    Blueprint,
)


def _row_candidates(session: Session, blueprint: Blueprint, row, selected_ids: set[str]) -> list[Question]:
    filters = [
        Question.subject_id == blueprint.subject_id,
        Question.status == "active",
        Question.id.not_in(selected_ids),
    ]
    if blueprint._actor_id is None:
        filters.append(Question.created_by.is_(None))
    else:
        filters.append(or_(Question.created_by.is_(None), Question.created_by == blueprint._actor_id))
    if row.chapter_ids:
        filters.append(Question.chapter.in_(row.chapter_ids))
    if row.question_types:
        filters.append(Question.question_type.in_(row.question_types))
    if row.difficulties:
        filters.append(Question.difficulty.in_(row.difficulties))
    if row.knowledge_point_ids:
        filters.append(
            Question.knowledge_point_links.any(
                QuestionKnowledgePoint.knowledge_point_id.in_(row.knowledge_point_ids)
            )
        )
    return session.scalars(
        select(Question)
        .options(selectinload(Question.knowledge_point_links))
        .where(*filters)
        .order_by(Question.id)
    ).all()


def _seeded_shuffle(items: list[Question], seed: int, row_index: int) -> list[Question]:
    stable_seed = int.from_bytes(
        sha256(f"{seed}:{row_index}".encode("ascii")).digest()[:8], "big"
    )
    shuffled = list(items)
    Random(stable_seed).shuffle(shuffled)
    return shuffled


def assemble_paper(session: Session, blueprint: Blueprint) -> AssemblyPreview:
    selected_ids: set[str] = set()
    assembled: list[AssemblyQuestion] = []
    shortages: list[AssemblyShortage] = []
    coverage: Counter[str] = Counter()
    type_distribution: Counter[str] = Counter()
    difficulty_distribution: Counter[str] = Counter()

    for row_index, row in enumerate(blueprint.rows, start=1):
        candidates = _seeded_shuffle(
            _row_candidates(session, blueprint, row, selected_ids), blueprint.seed, row_index
        )
        selected = candidates[: row.count]
        if len(selected) < row.count:
            shortages.append(
                AssemblyShortage(
                    row=row_index,
                    requested=row.count,
                    available=len(candidates),
                    missing=row.count - len(selected),
                    criteria={
                        "chapterIds": row.chapter_ids,
                        "knowledgePointIds": row.knowledge_point_ids,
                        "questionTypes": row.question_types,
                        "difficulties": row.difficulties,
                    },
                )
            )
        for question in selected:
            selected_ids.add(question.id)
            point_ids = [link.knowledge_point_id for link in question.knowledge_point_links]
            coverage.update(point_ids)
            type_distribution[question.question_type] += 1
            difficulty_distribution[question.difficulty] += 1
            assembled.append(
                AssemblyQuestion(
                    question_id=question.id,
                    text=question.text,
                    question_type=question.question_type,
                    difficulty=question.difficulty,
                    chapter=question.chapter,
                    knowledge_point_ids=point_ids,
                    section_title=row.section_title,
                    sequence=len(assembled) + 1,
                    points=row.points_each,
                )
            )

    return AssemblyPreview(
        questions=assembled,
        coverage=dict(coverage),
        type_distribution=dict(type_distribution),
        difficulty_distribution=dict(difficulty_distribution),
        duplicate_risk=len(assembled) - len(selected_ids),
        shortages=shortages,
    )
