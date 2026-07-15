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
    submission_inspector = inspect(bind)
    columns = {column["name"] for column in submission_inspector.get_columns("submissions")}
    submission_uniques = {constraint["name"] for constraint in submission_inspector.get_unique_constraints("submissions")}
    submission_indexes = {index["name"] for index in submission_inspector.get_indexes("submissions")}
    with op.batch_alter_table("submissions") as batch_op:
        if "started_at" not in columns:
            batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
            batch_op.create_index("ix_submissions_started_at", ["started_at"])
        if "submitted_at" in columns:
            batch_op.alter_column("submitted_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        if "uq_submission_assignment_student_attempt" not in submission_uniques:
            batch_op.create_unique_constraint(
                "uq_submission_assignment_student_attempt",
                ["assignment_id", "student_id", "attempt_number"],
            )
    if "uq_submission_one_in_progress" not in submission_indexes:
        op.create_index(
            "uq_submission_one_in_progress",
            "submissions",
            ["assignment_id", "student_id"],
            unique=True,
            sqlite_where=sa.text("status = 'in_progress'"),
            postgresql_where=sa.text("status = 'in_progress'"),
        )
    answer_inspector = inspect(bind)
    answer_uniques = {constraint["name"] for constraint in answer_inspector.get_unique_constraints("submission_answers")}
    if "uq_submission_answer_question" not in answer_uniques:
        with op.batch_alter_table("submission_answers") as batch_op:
            batch_op.create_unique_constraint("uq_submission_answer_question", ["submission_id", "question_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("submissions"):
        columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
        indexes = {index["name"] for index in inspect(bind).get_indexes("submissions")}
        uniques = {constraint["name"] for constraint in inspect(bind).get_unique_constraints("submissions")}
        if "submitted_at" in columns:
            bind.execute(sa.text("UPDATE submissions SET submitted_at = COALESCE(submitted_at, started_at, CURRENT_TIMESTAMP)"))
        if "started_at" in columns:
            with op.batch_alter_table("submissions") as batch_op:
                if "uq_submission_assignment_student_attempt" in uniques:
                    batch_op.drop_constraint("uq_submission_assignment_student_attempt", type_="unique")
                if "ix_submissions_started_at" in indexes:
                    batch_op.drop_index("ix_submissions_started_at")
                batch_op.drop_column("started_at")
        if "uq_submission_one_in_progress" in indexes:
            op.drop_index("uq_submission_one_in_progress", table_name="submissions")
        if "submitted_at" in columns:
            with op.batch_alter_table("submissions") as batch_op:
                batch_op.alter_column("submitted_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    if inspect(bind).has_table("submission_answers"):
        uniques = {constraint["name"] for constraint in inspect(bind).get_unique_constraints("submission_answers")}
        if "uq_submission_answer_question" in uniques:
            with op.batch_alter_table("submission_answers") as batch_op:
                batch_op.drop_constraint("uq_submission_answer_question", type_="unique")
    for table_name in ("practice_session_questions", "practice_sessions"):
        if inspect(bind).has_table(table_name):
            op.drop_table(table_name)
