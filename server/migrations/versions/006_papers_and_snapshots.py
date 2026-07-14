"""Add reusable papers and immutable assignment question snapshots.

Revision ID: 006_papers_and_snapshots
Revises: 005_subject_mastery
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "006_papers_and_snapshots"
down_revision = "005_subject_mastery"
branch_labels = None
depends_on = None


def create_paper_tables(bind) -> None:
    inspector = inspect(bind)
    if not inspector.has_table("papers"):
        op.create_table(
            "papers",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column(
                "subject_id",
                sa.String(length=64),
                sa.ForeignKey("subjects.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("total_points", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("assembly_mode", sa.String(length=24), nullable=False, server_default="manual"),
            sa.Column("assembly_blueprint", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("assembly_seed", sa.Integer(), nullable=True),
            sa.Column("shortages", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not inspect(bind).has_table("paper_questions"):
        op.create_table(
            "paper_questions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column(
                "paper_id",
                sa.String(length=64),
                sa.ForeignKey("papers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "question_id",
                sa.String(length=96),
                sa.ForeignKey("questions.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("section_title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("points", sa.Float(), nullable=False),
            sa.UniqueConstraint("paper_id", "question_id", name="uq_paper_question"),
            sa.UniqueConstraint("paper_id", "sequence", name="uq_paper_sequence"),
        )
    for table_name, index_name, columns in (
        ("papers", "ix_papers_subject_id", ["subject_id"]),
        ("papers", "ix_papers_status", ["status"]),
        ("papers", "ix_papers_created_by", ["created_by"]),
        ("paper_questions", "ix_paper_questions_paper_id", ["paper_id"]),
        ("paper_questions", "ix_paper_questions_question_id", ["question_id"]),
    ):
        if index_name not in {index["name"] for index in inspect(bind).get_indexes(table_name)}:
            op.create_index(index_name, table_name, columns)


def add_assignment_snapshot_columns(bind) -> None:
    assignment_columns = {column["name"] for column in inspect(bind).get_columns("assignments")}
    if not {"paper_id", "duration_minutes", "show_answers_mode"}.issubset(assignment_columns):
        with op.batch_alter_table("assignments") as batch_op:
            if "paper_id" not in assignment_columns:
                batch_op.add_column(sa.Column("paper_id", sa.String(length=64), nullable=True))
                batch_op.create_foreign_key(
                    "fk_assignments_paper_id_papers",
                    "papers",
                    ["paper_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
                batch_op.create_index("ix_assignments_paper_id", ["paper_id"])
            if "duration_minutes" not in assignment_columns:
                batch_op.add_column(sa.Column("duration_minutes", sa.Integer(), nullable=True))
            if "show_answers_mode" not in assignment_columns:
                batch_op.add_column(
                    sa.Column(
                        "show_answers_mode",
                        sa.String(length=24),
                        nullable=False,
                        server_default="after_submission",
                    )
                )
    question_columns = {
        column["name"] for column in inspect(bind).get_columns("assignment_questions")
    }
    if "question_snapshot" not in question_columns:
        with op.batch_alter_table("assignment_questions") as batch_op:
            batch_op.add_column(sa.Column("question_snapshot", sa.JSON(), nullable=True))


def upgrade() -> None:
    bind = op.get_bind()
    create_paper_tables(bind)
    add_assignment_snapshot_columns(bind)


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("assignment_questions"):
        question_columns = {
            column["name"] for column in inspect(bind).get_columns("assignment_questions")
        }
        if "question_snapshot" in question_columns:
            with op.batch_alter_table("assignment_questions") as batch_op:
                batch_op.drop_column("question_snapshot")

    if inspect(bind).has_table("assignments"):
        assignment_inspector = inspect(bind)
        assignment_columns = {
            column["name"] for column in assignment_inspector.get_columns("assignments")
        }
        assignment_indexes = {
            index["name"] for index in assignment_inspector.get_indexes("assignments")
        }
        assignment_foreign_keys = {
            foreign_key["name"] for foreign_key in assignment_inspector.get_foreign_keys("assignments")
        }
        with op.batch_alter_table("assignments") as batch_op:
            if "fk_assignments_paper_id_papers" in assignment_foreign_keys:
                batch_op.drop_constraint("fk_assignments_paper_id_papers", type_="foreignkey")
            if "ix_assignments_paper_id" in assignment_indexes:
                batch_op.drop_index("ix_assignments_paper_id")
            for column_name in ("show_answers_mode", "duration_minutes", "paper_id"):
                if column_name in assignment_columns:
                    batch_op.drop_column(column_name)

    for table_name in ("paper_questions", "papers"):
        if inspect(bind).has_table(table_name):
            op.drop_table(table_name)
