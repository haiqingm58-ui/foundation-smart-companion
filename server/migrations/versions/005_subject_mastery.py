"""Normalize knowledge mastery against the subject catalog.

Revision ID: 005_subject_mastery
Revises: 004_assessment_catalog
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "005_subject_mastery"
down_revision = "004_assessment_catalog"
branch_labels = None
depends_on = None


def normalize_knowledge_point_name(value: str) -> str:
    return " ".join(value.split())


def add_practice_attempt_review_status(bind) -> None:
    columns = {column["name"]: column for column in inspect(bind).get_columns("practice_attempts")}
    needs_status = "status" not in columns
    needs_nullable_score = not columns["score"]["nullable"]
    if needs_status or needs_nullable_score:
        with op.batch_alter_table("practice_attempts") as batch_op:
            if needs_status:
                batch_op.add_column(
                    sa.Column("status", sa.String(length=24), nullable=False, server_default="graded")
                )
                batch_op.create_index("ix_practice_attempts_status", ["status"])
            if needs_nullable_score:
                batch_op.alter_column("score", existing_type=sa.Float(), nullable=True)


def add_mastery_columns(bind) -> None:
    columns = {column["name"] for column in inspect(bind).get_columns("knowledge_mastery")}
    if "knowledge_point_id" not in columns or "subject_id" not in columns:
        with op.batch_alter_table("knowledge_mastery") as batch_op:
            if "knowledge_point_id" not in columns:
                batch_op.add_column(sa.Column("knowledge_point_id", sa.String(length=96), nullable=True))
                batch_op.create_foreign_key(
                    "fk_knowledge_mastery_knowledge_point_id_knowledge_points",
                    "knowledge_points",
                    ["knowledge_point_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if "subject_id" not in columns:
                batch_op.add_column(sa.Column("subject_id", sa.String(length=64), nullable=True))
                batch_op.create_foreign_key(
                    "fk_knowledge_mastery_subject_id_subjects",
                    "subjects",
                    ["subject_id"],
                    ["id"],
                    ondelete="SET NULL",
                )


def backfill_normalized_mastery(bind) -> None:
    metadata = sa.MetaData()
    mastery = sa.Table("knowledge_mastery", metadata, autoload_with=bind)
    points = sa.Table("knowledge_points", metadata, autoload_with=bind)
    point_rows = bind.execute(
        sa.select(points.c.id, points.c.subject_id, points.c.normalized_name).order_by(
            sa.case((points.c.subject_id == "foundation-engineering", 0), else_=1),
            points.c.id,
        )
    ).mappings()
    point_by_name: dict[str, tuple[str, str]] = {}
    for row in point_rows:
        point_by_name.setdefault(normalize_knowledge_point_name(row["normalized_name"]), (row["id"], row["subject_id"]))

    rows = bind.execute(
        sa.select(mastery).order_by(mastery.c.student_id, mastery.c.id)
    ).mappings().all()
    canonical_rows: dict[tuple[str, str], dict] = {}
    duplicate_ids: list[str] = []
    for row in rows:
        point = point_by_name.get(normalize_knowledge_point_name(row["knowledge_point"]))
        if point is None:
            continue
        point_id, subject_id = point
        key = (row["student_id"], point_id)
        canonical = canonical_rows.get(key)
        if canonical is None:
            bind.execute(
                mastery.update().where(mastery.c.id == row["id"]).values(
                    knowledge_point_id=point_id,
                    subject_id=subject_id,
                )
            )
            canonical_rows[key] = dict(row)
            continue
        canonical_attempts = canonical["attempts"]
        attempts = row["attempts"]
        combined_attempts = canonical_attempts + attempts
        combined_mastery = (
            (canonical["mastery"] * canonical_attempts + row["mastery"] * attempts) / combined_attempts
            if combined_attempts
            else canonical["mastery"]
        )
        bind.execute(
            mastery.update().where(mastery.c.id == canonical["id"]).values(
                mastery=combined_mastery,
                attempts=combined_attempts,
                knowledge_point_id=point_id,
                subject_id=subject_id,
            )
        )
        canonical["mastery"] = combined_mastery
        canonical["attempts"] = combined_attempts
        duplicate_ids.append(row["id"])
    if duplicate_ids:
        bind.execute(mastery.delete().where(mastery.c.id.in_(duplicate_ids)))


def add_mastery_indexes_and_unique(bind) -> None:
    inspector = inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("knowledge_mastery")}
    for index_name, columns in (
        ("ix_knowledge_mastery_knowledge_point_id", ["knowledge_point_id"]),
        ("ix_knowledge_mastery_subject_id", ["subject_id"]),
    ):
        if index_name not in indexes:
            op.create_index(index_name, "knowledge_mastery", columns)
    uniques = {constraint["name"] for constraint in inspect(bind).get_unique_constraints("knowledge_mastery")}
    if "uq_student_knowledge_point_id" not in uniques:
        with op.batch_alter_table("knowledge_mastery") as batch_op:
            batch_op.create_unique_constraint(
                "uq_student_knowledge_point_id", ["student_id", "knowledge_point_id"]
            )


def drop_legacy_mastery_unique(bind) -> None:
    uniques = {constraint["name"] for constraint in inspect(bind).get_unique_constraints("knowledge_mastery")}
    if "uq_student_knowledge" in uniques:
        with op.batch_alter_table("knowledge_mastery") as batch_op:
            batch_op.drop_constraint("uq_student_knowledge", type_="unique")


def consolidate_legacy_mastery_names(bind) -> None:
    metadata = sa.MetaData()
    mastery = sa.Table("knowledge_mastery", metadata, autoload_with=bind)
    rows = bind.execute(
        sa.select(mastery).order_by(mastery.c.student_id, mastery.c.knowledge_point, mastery.c.id)
    ).mappings().all()
    canonical_rows: dict[tuple[str, str], dict] = {}
    duplicate_ids: list[str] = []
    for row in rows:
        key = (row["student_id"], row["knowledge_point"])
        canonical = canonical_rows.get(key)
        if canonical is None:
            canonical_rows[key] = dict(row)
            continue
        combined_attempts = canonical["attempts"] + row["attempts"]
        combined_mastery = (
            (canonical["mastery"] * canonical["attempts"] + row["mastery"] * row["attempts"]) / combined_attempts
            if combined_attempts
            else canonical["mastery"]
        )
        bind.execute(
            mastery.update().where(mastery.c.id == canonical["id"]).values(
                mastery=combined_mastery,
                attempts=combined_attempts,
            )
        )
        canonical["mastery"] = combined_mastery
        canonical["attempts"] = combined_attempts
        duplicate_ids.append(row["id"])
    if duplicate_ids:
        bind.execute(mastery.delete().where(mastery.c.id.in_(duplicate_ids)))


def upgrade() -> None:
    bind = op.get_bind()
    add_practice_attempt_review_status(bind)
    add_mastery_columns(bind)
    backfill_normalized_mastery(bind)
    drop_legacy_mastery_unique(bind)
    add_mastery_indexes_and_unique(bind)


def downgrade() -> None:
    bind = op.get_bind()
    consolidate_legacy_mastery_names(bind)
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("knowledge_mastery")}
    indexes = {index["name"] for index in inspector.get_indexes("knowledge_mastery")}
    foreign_keys = {foreign_key["name"] for foreign_key in inspector.get_foreign_keys("knowledge_mastery")}
    uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("knowledge_mastery")}
    if "knowledge_point_id" in columns or "subject_id" in columns:
        with op.batch_alter_table("knowledge_mastery") as batch_op:
            if "uq_student_knowledge_point_id" in uniques:
                batch_op.drop_constraint("uq_student_knowledge_point_id", type_="unique")
            for index_name in ("ix_knowledge_mastery_knowledge_point_id", "ix_knowledge_mastery_subject_id"):
                if index_name in indexes:
                    batch_op.drop_index(index_name)
            if "fk_knowledge_mastery_knowledge_point_id_knowledge_points" in foreign_keys:
                batch_op.drop_constraint(
                    "fk_knowledge_mastery_knowledge_point_id_knowledge_points", type_="foreignkey"
                )
            if "fk_knowledge_mastery_subject_id_subjects" in foreign_keys:
                batch_op.drop_constraint("fk_knowledge_mastery_subject_id_subjects", type_="foreignkey")
            if "subject_id" in columns:
                batch_op.drop_column("subject_id")
            if "knowledge_point_id" in columns:
                batch_op.drop_column("knowledge_point_id")
            if "uq_student_knowledge" not in uniques:
                batch_op.create_unique_constraint("uq_student_knowledge", ["student_id", "knowledge_point"])

    practice_columns = {column["name"]: column for column in inspect(bind).get_columns("practice_attempts")}
    if "status" in practice_columns or practice_columns["score"]["nullable"]:
        bind.execute(sa.text("UPDATE practice_attempts SET score = 0 WHERE score IS NULL"))
        with op.batch_alter_table("practice_attempts") as batch_op:
            if "ix_practice_attempts_status" in {index["name"] for index in inspect(bind).get_indexes("practice_attempts")}:
                batch_op.drop_index("ix_practice_attempts_status")
            if "status" in practice_columns:
                batch_op.drop_column("status")
            if practice_columns["score"]["nullable"]:
                batch_op.alter_column("score", existing_type=sa.Float(), nullable=False)
