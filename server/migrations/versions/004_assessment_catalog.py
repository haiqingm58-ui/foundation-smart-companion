"""Add the subject-scoped assessment catalog and backfill legacy questions.

Revision ID: 004_assessment_catalog
Revises: 003_submission_feedback
"""

from hashlib import sha256

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "004_assessment_catalog"
down_revision = "003_submission_feedback"
branch_labels = None
depends_on = None


FOUNDATION_SUBJECT_ID = "foundation-engineering"


def normalize_knowledge_point_name(value: str) -> str:
    return " ".join(value.split())


def knowledge_point_id(subject_id: str, normalized_name: str) -> str:
    digest = sha256(f"{subject_id}:{normalized_name}".encode("utf-8")).hexdigest()
    return f"knowledge-point-{digest}"


def question_knowledge_point_id(question_id: str, knowledge_point_id: str) -> str:
    digest = sha256(f"{question_id}:{knowledge_point_id}".encode("utf-8")).hexdigest()
    return f"question-knowledge-point-{digest}"


def ensure_catalog_tables(bind) -> None:
    inspector = inspect(bind)
    if not inspector.has_table("subjects"):
        op.create_table(
            "subjects",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("title", sa.String(length=120), nullable=False, unique=True),
            sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
    if not inspector.has_table("knowledge_points"):
        op.create_table(
            "knowledge_points",
            sa.Column("id", sa.String(length=96), primary_key=True),
            sa.Column("subject_id", sa.String(length=64), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chapter", sa.String(length=160), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("normalized_name", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=True),
            sa.UniqueConstraint("subject_id", "normalized_name", name="uq_subject_knowledge_name"),
        )
    if not inspector.has_table("question_knowledge_points"):
        op.create_table(
            "question_knowledge_points",
            sa.Column("id", sa.String(length=96), primary_key=True),
            sa.Column("question_id", sa.String(length=96), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("knowledge_point_id", sa.String(length=96), sa.ForeignKey("knowledge_points.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.UniqueConstraint("question_id", "knowledge_point_id", name="uq_question_knowledge_point"),
        )
    for table_name, index_name, columns in (
        ("knowledge_points", "ix_knowledge_points_subject_id", ["subject_id"]),
        ("knowledge_points", "ix_knowledge_points_chapter", ["chapter"]),
        ("knowledge_points", "ix_knowledge_points_created_by", ["created_by"]),
        ("question_knowledge_points", "ix_question_knowledge_points_question_id", ["question_id"]),
        ("question_knowledge_points", "ix_question_knowledge_points_knowledge_point_id", ["knowledge_point_id"]),
    ):
        indexes = {index["name"] for index in inspect(bind).get_indexes(table_name)}
        if index_name not in indexes:
            op.create_index(index_name, table_name, columns)


def ensure_question_columns(bind) -> None:
    columns = {column["name"] for column in inspect(bind).get_columns("questions")}
    if "subject_id" not in columns:
        with op.batch_alter_table("questions") as batch_op:
            batch_op.add_column(sa.Column("subject_id", sa.String(length=64), nullable=True))
            batch_op.create_foreign_key(
                "fk_questions_subject_id_subjects",
                "subjects",
                ["subject_id"],
                ["id"],
            )
        columns.add("subject_id")
    additions = (
        ("attachments", sa.Column("attachments", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))),
        ("answer_word_limit", sa.Column("answer_word_limit", sa.Integer(), nullable=True)),
        ("grading_mode", sa.Column("grading_mode", sa.String(length=24), nullable=False, server_default="auto")),
        ("status", sa.Column("status", sa.String(length=24), nullable=False, server_default="review_required")),
        ("source_metadata", sa.Column("source_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))),
        ("content_fingerprint", sa.Column("content_fingerprint", sa.String(length=96), nullable=True)),
    )
    for name, column in additions:
        if name not in columns:
            op.add_column("questions", column)

    indexes = {index["name"] for index in inspect(bind).get_indexes("questions")}
    if "ix_questions_subject_id" not in indexes:
        op.create_index("ix_questions_subject_id", "questions", ["subject_id"])
    if "ix_questions_content_fingerprint" not in indexes:
        op.create_index("ix_questions_content_fingerprint", "questions", ["content_fingerprint"])


def seed_subjects(bind) -> None:
    subjects = sa.table(
        "subjects",
        sa.column("id", sa.String),
        sa.column("title", sa.String),
        sa.column("slug", sa.String),
        sa.column("status", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    for values in (
        {"id": FOUNDATION_SUBJECT_ID, "title": "基础工程", "slug": FOUNDATION_SUBJECT_ID, "status": "active", "sort_order": 0},
        {"id": "soil-mechanics", "title": "土力学", "slug": "soil-mechanics", "status": "active", "sort_order": 1},
    ):
        if bind.execute(sa.select(subjects.c.id).where(subjects.c.id == values["id"])).scalar_one_or_none() is None:
            bind.execute(subjects.insert().values(**values))


def backfill_legacy_questions(bind) -> None:
    metadata = sa.MetaData()
    questions = sa.Table("questions", metadata, autoload_with=bind)
    knowledge_points = sa.Table("knowledge_points", metadata, autoload_with=bind)
    links = sa.Table("question_knowledge_points", metadata, autoload_with=bind)

    existing_points = {
        row.normalized_name: row.id
        for row in bind.execute(
            sa.select(knowledge_points.c.id, knowledge_points.c.normalized_name).where(
                knowledge_points.c.subject_id == FOUNDATION_SUBJECT_ID
            )
        )
    }
    existing_links = {
        (row.question_id, row.knowledge_point_id)
        for row in bind.execute(sa.select(links.c.question_id, links.c.knowledge_point_id))
    }
    rows = bind.execute(sa.select(questions.c.id, questions.c.chapter, questions.c.knowledge_point, questions.c.subject_id)).mappings()
    for row in rows:
        status = "review_required"
        if not row["knowledge_point"]:
            bind.execute(
                questions.update().where(questions.c.id == row["id"]).values(
                    subject_id=FOUNDATION_SUBJECT_ID,
                    status=status,
                )
            )
            continue
        name = row["knowledge_point"].strip()
        normalized_name = normalize_knowledge_point_name(name)
        if normalized_name:
            point_id = existing_points.get(normalized_name)
            if point_id is None:
                point_id = knowledge_point_id(FOUNDATION_SUBJECT_ID, normalized_name)
                bind.execute(
                    knowledge_points.insert().values(
                        id=point_id,
                        subject_id=FOUNDATION_SUBJECT_ID,
                        chapter=row["chapter"] or "",
                        name=name,
                        normalized_name=normalized_name,
                        description="",
                        status="active",
                        sort_order=0,
                        created_by=None,
                    )
                )
                existing_points[normalized_name] = point_id
            link_key = (row["id"], point_id)
            if link_key not in existing_links:
                bind.execute(
                    links.insert().values(
                        id=question_knowledge_point_id(*link_key),
                        question_id=row["id"],
                        knowledge_point_id=point_id,
                        weight=1.0,
                    )
                )
                existing_links.add(link_key)
            status = "active"
        bind.execute(
            questions.update().where(questions.c.id == row["id"]).values(
                subject_id=FOUNDATION_SUBJECT_ID,
                status=status,
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    ensure_catalog_tables(bind)
    ensure_question_columns(bind)
    seed_subjects(bind)
    backfill_legacy_questions(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if inspector.has_table("questions"):
        indexes = {index["name"] for index in inspector.get_indexes("questions")}
        for index_name in ("ix_questions_content_fingerprint", "ix_questions_subject_id"):
            if index_name in indexes:
                op.drop_index(index_name, table_name="questions")
        columns = {column["name"] for column in inspector.get_columns("questions")}
        for column_name in (
            "content_fingerprint",
            "source_metadata",
            "status",
            "grading_mode",
            "answer_word_limit",
            "attachments",
            "subject_id",
        ):
            if column_name in columns:
                op.drop_column("questions", column_name)
    for table_name in ("question_knowledge_points", "knowledge_points", "subjects"):
        if inspect(bind).has_table(table_name):
            op.drop_table(table_name)
