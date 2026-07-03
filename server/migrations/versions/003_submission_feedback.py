"""Add teacher feedback to assignment submissions.

Revision ID: 003_submission_feedback
Revises: 002_practice_attempts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "003_submission_feedback"
down_revision = "002_practice_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
    if "feedback" not in columns:
        op.add_column("submissions", sa.Column("feedback", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("submissions")}
    if "feedback" in columns:
        op.drop_column("submissions", "feedback")
