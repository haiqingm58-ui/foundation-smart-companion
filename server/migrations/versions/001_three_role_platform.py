"""Create the three-role teaching platform schema."""

from alembic import op

from server.application.models import Base


revision = "001_three_role_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
