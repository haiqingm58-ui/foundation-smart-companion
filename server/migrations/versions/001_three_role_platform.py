"""Create the frozen pre-practice three-role teaching platform schema."""

from alembic import op
import sqlalchemy as sa


revision = "001_three_role_platform"
down_revision = None
branch_labels = None
depends_on = None


def platform_metadata() -> sa.MetaData:
    metadata = sa.MetaData()

    sa.Table(
        "users", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("password_salt", sa.String(128)),
        sa.Column("password_algorithm", sa.String(32), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, index=True),
        sa.Column("role_label", sa.String(24), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("avatar", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False, index=True),
        sa.Column("student_no", sa.String(64)),
        sa.Column("college", sa.String(120), nullable=False),
        sa.Column("school", sa.String(120), nullable=False),
        sa.Column("mentor", sa.String(80)),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "classes", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("grade", sa.String(32)),
        sa.Column("major", sa.String(120), nullable=False),
        sa.Column("college", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "teachers", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("teacher_no", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("college", sa.String(120), nullable=False),
        sa.Column("course", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(160)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "students", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("student_no", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("class_id", sa.String(64), sa.ForeignKey("classes.id", ondelete="SET NULL"), index=True),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False),
        sa.Column("last_study_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "teacher_student_bindings", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("teacher_id", sa.String(64), sa.ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("student_id", sa.String(64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("class_id", sa.String(64), sa.ForeignKey("classes.id", ondelete="SET NULL"), index=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("teacher_id", "student_id", "class_id", name="uq_teacher_student_class"),
    )
    sa.Table(
        "sessions", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "captcha_records", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("answer_hash", sa.String(64), nullable=False),
        sa.Column("client_ip", sa.String(64), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "login_attempts", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, index=True),
        sa.Column("client_ip", sa.String(64), nullable=False, index=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    sa.Table(
        "documents", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("uploaded_by", sa.String(64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "exercises", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "settings", metadata,
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "resources", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, index=True),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("uploaded_by", sa.String(64), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("chapter", sa.String(120), index=True),
        sa.Column("knowledge_point", sa.String(160), index=True),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("class_scope", sa.JSON(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "knowledge_chunks", metadata,
        sa.Column("id", sa.String(96), primary_key=True),
        sa.Column("resource_id", sa.String(64), sa.ForeignKey("resources.id", ondelete="CASCADE"), index=True),
        sa.Column("source_type", sa.String(32), nullable=False, index=True),
        sa.Column("heading", sa.String(300), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("chapter", sa.String(120), index=True),
        sa.Column("page", sa.Integer()),
        sa.Column("sequence", sa.Integer(), nullable=False),
    )
    sa.Table(
        "questions", metadata,
        sa.Column("id", sa.String(96), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(32), nullable=False, index=True),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("correct_answer", sa.JSON()),
        sa.Column("explanation", sa.Text()),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("difficulty", sa.String(24), nullable=False, index=True),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("chapter", sa.String(120), index=True),
        sa.Column("knowledge_point", sa.String(160), index=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("users.id"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "assignments", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("teacher_id", sa.String(64), sa.ForeignKey("teachers.id"), nullable=False, index=True),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("total_points", sa.Float(), nullable=False),
        sa.Column("allow_resubmit", sa.Boolean(), nullable=False),
        sa.Column("auto_grade", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "assignment_questions", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("assignment_id", sa.String(64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question_id", sa.String(96), sa.ForeignKey("questions.id"), nullable=False, index=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.UniqueConstraint("assignment_id", "question_id", name="uq_assignment_question"),
    )
    sa.Table(
        "assignment_targets", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("assignment_id", sa.String(64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("class_id", sa.String(64), sa.ForeignKey("classes.id", ondelete="SET NULL"), index=True),
        sa.Column("student_id", sa.String(64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),
    )
    sa.Table(
        "submissions", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("assignment_id", sa.String(64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("student_id", sa.String(64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, index=True),
        sa.Column("score", sa.Float()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("graded_at", sa.DateTime(timezone=True)),
        sa.Column("graded_by", sa.String(64), sa.ForeignKey("users.id")),
    )
    sa.Table(
        "submission_answers", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("submission_id", sa.String(64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("question_id", sa.String(96), sa.ForeignKey("questions.id"), nullable=False, index=True),
        sa.Column("answer", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("criteria_scores", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("feedback", sa.Text()),
    )
    sa.Table(
        "learning_progress", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("student_id", sa.String(64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chapter_id", sa.String(64), nullable=False, index=True),
        sa.Column("percent", sa.Float(), nullable=False),
        sa.Column("last_section", sa.String(160)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("student_id", "chapter_id", name="uq_student_chapter_progress"),
    )
    sa.Table(
        "knowledge_mastery", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("student_id", sa.String(64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("knowledge_point", sa.String(160), nullable=False, index=True),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("student_id", "knowledge_point", name="uq_student_knowledge"),
    )
    sa.Table(
        "notices", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("publisher_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("audience", sa.String(32), nullable=False),
        sa.Column("class_scope", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "operation_logs", metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("actor_id", sa.String(64), sa.ForeignKey("users.id"), index=True),
        sa.Column("action", sa.String(120), nullable=False, index=True),
        sa.Column("target_type", sa.String(64)),
        sa.Column("target_id", sa.String(96)),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    return metadata


def upgrade() -> None:
    platform_metadata().create_all(bind=op.get_bind())


def downgrade() -> None:
    platform_metadata().drop_all(bind=op.get_bind())
