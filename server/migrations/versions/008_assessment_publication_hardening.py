"""Harden assignment publication idempotency and backfill immutable snapshots.

Revision ID: 008_assessment_hardening
Revises: 007_practice_sessions
"""

from collections import defaultdict
from copy import deepcopy

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "008_assessment_hardening"
down_revision = "007_practice_sessions"
branch_labels = None
depends_on = None


def _backfill_assignment_snapshots(bind) -> None:
    metadata = sa.MetaData()
    assignments_questions = sa.Table("assignment_questions", metadata, autoload_with=bind)
    questions = sa.Table("questions", metadata, autoload_with=bind)
    links = sa.Table("question_knowledge_points", metadata, autoload_with=bind)

    link_rows = bind.execute(
        sa.select(links.c.question_id, links.c.knowledge_point_id, links.c.weight)
        .order_by(links.c.question_id, links.c.id)
    ).mappings()
    knowledge_ids: dict[str, list[str]] = defaultdict(list)
    knowledge_weights: dict[str, dict[str, float]] = defaultdict(dict)
    for row in link_rows:
        knowledge_ids[row["question_id"]].append(row["knowledge_point_id"])
        knowledge_weights[row["question_id"]][row["knowledge_point_id"]] = row["weight"]

    rows = bind.execute(
        sa.select(
            assignments_questions.c.id.label("assignment_question_id"),
            assignments_questions.c.sequence,
            assignments_questions.c.points.label("assignment_points"),
            *[column for column in questions.c],
        )
        .join(questions, questions.c.id == assignments_questions.c.question_id)
        .where(assignments_questions.c.question_snapshot.is_(None))
    ).mappings()
    for row in rows:
        question_id = row["id"]
        snapshot = {
            "id": question_id,
            "subjectId": row["subject_id"],
            "text": row["text"],
            "questionType": row["question_type"],
            "options": deepcopy(row["options"] or []),
            "correctAnswer": deepcopy(row["correct_answer"]),
            "explanation": row["explanation"],
            "rubric": deepcopy(row["rubric"] or []),
            "difficulty": row["difficulty"],
            "chapter": row["chapter"],
            "knowledgePointIds": knowledge_ids[question_id],
            "knowledgePointWeights": knowledge_weights[question_id],
            "attachments": deepcopy(row["attachments"] or []),
            "answerWordLimit": row["answer_word_limit"],
            "gradingMode": row["grading_mode"],
            "sourceMetadata": deepcopy(row["source_metadata"] or {}),
            "sequence": row["sequence"],
            "points": row["assignment_points"],
        }
        bind.execute(
            assignments_questions.update()
            .where(assignments_questions.c.id == row["assignment_question_id"])
            .values(question_snapshot=snapshot)
        )


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("assignments")}
    if "publication_key" not in columns:
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.add_column(sa.Column("publication_key", sa.String(length=96), nullable=True))
    indexes = {index["name"] for index in inspect(bind).get_indexes("assignments")}
    if "uq_assignment_teacher_publication_key" not in indexes:
        op.create_index(
            "uq_assignment_teacher_publication_key",
            "assignments",
            ["teacher_id", "publication_key"],
            unique=True,
        )
    _backfill_assignment_snapshots(bind)
    question_columns = {
        column["name"]: column
        for column in inspect(bind).get_columns("assignment_questions")
    }
    if question_columns["question_snapshot"]["nullable"]:
        with op.batch_alter_table("assignment_questions") as batch_op:
            batch_op.alter_column(
                "question_snapshot",
                existing_type=sa.JSON(),
                nullable=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    question_columns = {
        column["name"]: column
        for column in inspect(bind).get_columns("assignment_questions")
    }
    if not question_columns["question_snapshot"]["nullable"]:
        with op.batch_alter_table("assignment_questions") as batch_op:
            batch_op.alter_column(
                "question_snapshot",
                existing_type=sa.JSON(),
                nullable=True,
            )
    indexes = {index["name"] for index in inspect(bind).get_indexes("assignments")}
    if "uq_assignment_teacher_publication_key" in indexes:
        op.drop_index("uq_assignment_teacher_publication_key", table_name="assignments")
    columns = {column["name"] for column in inspect(bind).get_columns("assignments")}
    if "publication_key" in columns:
        with op.batch_alter_table("assignments") as batch_op:
            batch_op.drop_column("publication_key")
