"""Add persisted independent practice attempts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "002_practice_attempts"
down_revision = "001_three_role_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("practice_attempts"):
        op.create_table(
            "practice_attempts",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("student_id", sa.String(length=64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("question_id", sa.String(length=96), sa.ForeignKey("questions.id"), nullable=False, index=True),
            sa.Column("answer", sa.JSON(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("max_score", sa.Float(), nullable=False),
            sa.Column("criteria_scores", sa.JSON(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("feedback", sa.Text(), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, index=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("practice_attempts"):
        op.drop_table("practice_attempts")
