"""Add resumable student practice sessions and formal submission start times.

Revision ID: 007_practice_sessions
Revises: 006_papers_and_snapshots
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "007_practice_sessions"
down_revision = "006_papers_and_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("practice_sessions"):
        op.create_table(
            "practice_sessions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("student_id", sa.String(length=64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("subject_id", sa.String(length=64), sa.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("selection_mode", sa.String(length=32), nullable=False),
            sa.Column("chapter", sa.String(length=160), nullable=True),
            sa.Column("knowledge_point_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("requested_count", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="in_progress"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("max_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_practice_sessions_student_id", "practice_sessions", ["student_id"])
        op.create_index("ix_practice_sessions_subject_id", "practice_sessions", ["subject_id"])
        op.create_index("ix_practice_sessions_chapter", "practice_sessions", ["chapter"])
        op.create_index("ix_practice_sessions_status", "practice_sessions", ["status"])
        op.create_index("ix_practice_sessions_submitted_at", "practice_sessions", ["submitted_at"])
    if not inspect(bind).has_table("practice_session_questions"):
        op.create_table(
            "practice_session_questions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("session_id", sa.String(length=64), sa.ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("question_id", sa.String(length=96), sa.ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("question_snapshot", sa.JSON(), nullable=False),
            sa.Column("grading_snapshot", sa.JSON(), nullable=False),
            sa.Column("answer", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="unanswered"),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("max_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("criteria_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("feedback", sa.Text(), nullable=True),
            sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("session_id", "question_id", name="uq_practice_session_question"),
            sa.UniqueConstraint("session_id", "sequence", name="uq_practice_session_sequence"),
        )
        op.create_index("ix_practice_session_questions_session_id", "practice_session_questions", ["session_id"])
        op.create_index("ix_practice_session_questions_question_id", "practice_session_questions", ["question_id"])
    columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
    if "started_at" not in columns:
        with op.batch_alter_table("submissions") as batch_op:
            batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
            batch_op.create_index("ix_submissions_started_at", ["started_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("submissions"):
        columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
        indexes = {index["name"] for index in inspect(bind).get_indexes("submissions")}
        if "started_at" in columns:
            with op.batch_alter_table("submissions") as batch_op:
                if "ix_submissions_started_at" in indexes:
                    batch_op.drop_index("ix_submissions_started_at")
                batch_op.drop_column("started_at")
    for table_name in ("practice_session_questions", "practice_sessions"):
        if inspect(bind).has_table(table_name):
            op.drop_table(table_name)
