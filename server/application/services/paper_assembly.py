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


def _row_candidates(session: Session, blueprint: Blueprint, row) -> list[Question]:
    filters = [
        Question.subject_id == blueprint.subject_id,
        Question.status == "active",
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
    assembled: list[AssemblyQuestion] = []
    shortages: list[AssemblyShortage] = []
    coverage: Counter[str] = Counter()
    type_distribution: Counter[str] = Counter()
    difficulty_distribution: Counter[str] = Counter()

    candidates_by_row: dict[int, list[Question]] = {}
    questions_by_id: dict[str, Question] = {}
    for row_index, row in enumerate(blueprint.rows, start=1):
        candidates = _seeded_shuffle(
            _row_candidates(session, blueprint, row), blueprint.seed, row_index
        )
        candidates_by_row[row_index] = candidates
        questions_by_id.update((question.id, question) for question in candidates)

    slots = [
        (row_index, slot_index)
        for row_index, row in enumerate(blueprint.rows, start=1)
        for slot_index in range(1, row.count + 1)
    ]
    slots.sort(
        key=lambda slot: (
            len(candidates_by_row[slot[0]]),
            slot[0],
            slot[1],
        )
    )
    question_to_slot: dict[str, tuple[int, int]] = {}
    slot_to_question: dict[tuple[int, int], str] = {}

    def augment(slot: tuple[int, int], seen_question_ids: set[str]) -> bool:
        for question in candidates_by_row[slot[0]]:
            if question.id in seen_question_ids:
                continue
            seen_question_ids.add(question.id)
            owner = question_to_slot.get(question.id)
            if owner is None or augment(owner, seen_question_ids):
                question_to_slot[question.id] = slot
                slot_to_question[slot] = question.id
                return True
        return False

    for slot in slots:
        augment(slot, set())

    for row_index, row in enumerate(blueprint.rows, start=1):
        selected = [
            questions_by_id[slot_to_question[(row_index, slot_index)]]
            for slot_index in range(1, row.count + 1)
            if (row_index, slot_index) in slot_to_question
        ]
        if len(selected) != row.count:
            shortages.append(
                AssemblyShortage(
                    row=row_index,
                    requested=row.count,
                    available=len(selected),
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
        duplicate_risk=len(assembled) - len({item.question_id for item in assembled}),
        shortages=shortages,
    )
