"""Add persisted independent practice attempts."""

from alembic import op
from sqlalchemy import inspect

from server.application.models import PracticeAttempt


revision = "002_practice_attempts"
down_revision = "001_three_role_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table(PracticeAttempt.__tablename__):
        PracticeAttempt.__table__.create(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table(PracticeAttempt.__tablename__):
        PracticeAttempt.__table__.drop(bind=bind)
