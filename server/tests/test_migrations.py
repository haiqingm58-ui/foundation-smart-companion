from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sqlalchemy import inspect, select, text


def test_migration_revision_ids_fit_production_version_column() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "server" / "migrations"))
    revisions = list(ScriptDirectory.from_config(config).walk_revisions())

    assert revisions
    assert {revision.revision for revision in revisions if len(revision.revision) > 32} == set()


REVISION_003_TABLE_COLUMNS = {
    "users": {"id", "username", "password_hash", "password_salt", "password_algorithm", "role", "role_label", "name", "avatar", "status", "student_no", "college", "school", "mentor", "must_change_password", "last_login_at", "created_at", "updated_at"},
    "classes": {"id", "name", "grade", "major", "college", "created_at"},
    "teachers": {"id", "user_id", "teacher_no", "college", "course", "phone", "email", "created_at"},
    "students": {"id", "user_id", "student_no", "class_id", "progress", "average_score", "last_study_at", "created_at"},
    "teacher_student_bindings": {"id", "teacher_id", "student_id", "class_id", "status", "created_by", "created_at"},
    "sessions": {"id", "user_id", "token_hash", "csrf_hash", "expires_at", "revoked_at", "created_at"},
    "captcha_records": {"id", "answer_hash", "client_ip", "expires_at", "used_at", "created_at"},
    "login_attempts": {"id", "username", "client_ip", "success", "reason", "created_at"},
    "documents": {"id", "title", "text", "source_type", "uploaded_by", "uploaded_at"},
    "exercises": {"id", "payload", "source", "created_by", "created_at"},
    "settings": {"key", "value", "updated_at"},
    "resources": {"id", "name", "title", "storage_path", "file_size", "mime_type", "source_type", "uploaded_by", "chapter", "knowledge_point", "visibility", "class_scope", "extracted_text", "created_at", "updated_at"},
    "knowledge_chunks": {"id", "resource_id", "source_type", "heading", "text", "chapter", "page", "sequence"},
    "questions": {"id", "text", "question_type", "options", "correct_answer", "explanation", "rubric", "difficulty", "points", "chapter", "knowledge_point", "source", "created_by", "created_at", "updated_at"},
    "assignments": {"id", "title", "description", "teacher_id", "starts_at", "due_at", "total_points", "allow_resubmit", "auto_grade", "status", "created_at"},
    "assignment_questions": {"id", "assignment_id", "question_id", "sequence", "points"},
    "assignment_targets": {"id", "assignment_id", "class_id", "student_id"},
    "submissions": {"id", "assignment_id", "student_id", "attempt_number", "status", "score", "feedback", "submitted_at", "graded_at", "graded_by"},
    "submission_answers": {"id", "submission_id", "question_id", "answer", "score", "criteria_scores", "confidence", "feedback"},
    "practice_attempts": {"id", "student_id", "question_id", "answer", "score", "max_score", "criteria_scores", "confidence", "feedback", "attempt_number", "submitted_at"},
    "learning_progress": {"id", "student_id", "chapter_id", "percent", "last_section", "updated_at"},
    "knowledge_mastery": {"id", "student_id", "knowledge_point", "mastery", "attempts", "updated_at"},
    "notices": {"id", "title", "content", "publisher_id", "audience", "class_scope", "published_at"},
    "operation_logs": {"id", "actor_id", "action", "target_type", "target_id", "detail", "client_ip", "created_at"},
}
REVISION_003_PRIMARY_KEYS = {
    table_name: ("key",) if table_name == "settings" else ("id",)
    for table_name in REVISION_003_TABLE_COLUMNS
}
REVISION_003_NAMED_UNIQUES = {
    ("teacher_student_bindings", "uq_teacher_student_class", ("teacher_id", "student_id", "class_id")),
    ("assignment_questions", "uq_assignment_question", ("assignment_id", "question_id")),
    ("assignment_targets", "uq_assignment_student", ("assignment_id", "student_id")),
    ("learning_progress", "uq_student_chapter_progress", ("student_id", "chapter_id")),
    ("knowledge_mastery", "uq_student_knowledge", ("student_id", "knowledge_point")),
}


def assert_revision_003_schema(database) -> None:
    inspector = inspect(database.engine)
    actual_tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert actual_tables == set(REVISION_003_TABLE_COLUMNS)
    actual_named_uniques = set()
    actual_named_foreign_keys = set()
    actual_named_checks = set()
    for table_name, expected_columns in REVISION_003_TABLE_COLUMNS.items():
        assert {column["name"] for column in inspector.get_columns(table_name)} == expected_columns
        assert tuple(inspector.get_pk_constraint(table_name)["constrained_columns"]) == REVISION_003_PRIMARY_KEYS[table_name]
        actual_named_uniques.update(
            (table_name, constraint["name"], tuple(constraint["column_names"]))
            for constraint in inspector.get_unique_constraints(table_name)
            if constraint["name"]
        )
        actual_named_foreign_keys.update(
            (table_name, foreign_key["name"], tuple(foreign_key["constrained_columns"]))
            for foreign_key in inspector.get_foreign_keys(table_name)
            if foreign_key["name"]
        )
        actual_named_checks.update(
            (table_name, check["name"], check["sqltext"])
            for check in inspector.get_check_constraints(table_name)
            if check["name"]
        )
    assert actual_named_uniques == REVISION_003_NAMED_UNIQUES
    assert actual_named_foreign_keys == set()
    assert actual_named_checks == set()


def make_legacy_database(path: Path, knowledge_point: str = "桩侧阻力") -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE users (
          id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, password_salt TEXT NOT NULL,
          role TEXT NOT NULL, role_label TEXT NOT NULL, name TEXT NOT NULL,
          student_no TEXT NOT NULL, college TEXT NOT NULL, school TEXT NOT NULL,
          mentor TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE documents (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, text TEXT NOT NULL,
          source_type TEXT NOT NULL, uploaded_by TEXT NOT NULL, uploaded_at TEXT NOT NULL
        );
        CREATE TABLE exercises (
          id TEXT PRIMARY KEY, payload TEXT NOT NULL, source TEXT NOT NULL,
          created_by TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE questions (
          id TEXT PRIMARY KEY, text TEXT NOT NULL, question_type TEXT NOT NULL,
          options TEXT NOT NULL, correct_answer TEXT, explanation TEXT,
          rubric TEXT NOT NULL, difficulty TEXT NOT NULL, points REAL NOT NULL,
          chapter TEXT, knowledge_point TEXT, source TEXT NOT NULL,
          created_by TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE settings (
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "student-old", "old-student", "legacy-hash", "legacy-salt", "student", "学生",
            "旧学生", "20260001", "土木工程学院", "湖南大学", "李老师", "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.execute(
        "INSERT INTO documents VALUES (?,?,?,?,?,?)",
        ("doc-old", "桩基础讲义", "桩侧阻力与桩端阻力", "teacher-upload", "teacher-old", "2026-01-01T00:00:00+00:00"),
    )
    connection.execute(
        "INSERT INTO exercises VALUES (?,?,?,?,?)",
        (
            "exercise-old",
            json.dumps({"text": "说明桩侧阻力。", "chapter": "第3章 桩基础", "type": "简答题"}, ensure_ascii=False),
            "textbook",
            "seed",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.execute(
        "INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "exercise-old",
            "说明桩侧阻力。",
            "简答题",
            "[]",
            None,
            None,
            "[]",
            "基础",
            10,
            "第3章 桩基础",
            knowledge_point,
            "textbook",
            None,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    connection.execute(
        "INSERT INTO settings VALUES (?,?,?)",
        ("qa.answerStyle", "先给结论", "2026-01-01T00:00:00+00:00"),
    )
    connection.commit()
    connection.close()


def task1_schema_signature(database) -> dict:
    inspector = inspect(database.engine)
    tables = tuple(sorted(inspector.get_table_names()))
    catalog_tables = ("subjects", "knowledge_points", "question_knowledge_points", "questions")
    table_details = {}
    for table_name in catalog_tables:
        table_details[table_name] = {
            "columns": tuple(
                sorted(
                    (column["name"], str(column["type"]), column["nullable"], str(column["default"]))
                    for column in inspector.get_columns(table_name)
                )
            ),
            "unique_constraints": tuple(
                sorted(
                    (constraint["name"], tuple(constraint["column_names"]))
                    for constraint in inspector.get_unique_constraints(table_name)
                )
            ),
            "foreign_keys": tuple(
                sorted(
                    (
                        tuple(foreign_key["constrained_columns"]),
                        foreign_key["referred_table"],
                        tuple(foreign_key["referred_columns"]),
                        foreign_key["options"].get("ondelete"),
                    )
                    for foreign_key in inspector.get_foreign_keys(table_name)
                )
            ),
            "indexes": tuple(
                sorted((index["name"], tuple(index["column_names"]), index["unique"]) for index in inspector.get_indexes(table_name))
            ),
        }
    return {"tables": tables, "catalog": table_details}


TASK6_SCHEMA_TABLES = ("papers", "paper_questions", "assignments", "assignment_questions")


def task6_database_schema_signature(database, table_names=TASK6_SCHEMA_TABLES) -> dict:
    inspector = inspect(database.engine)
    signature = {}
    for table_name in table_names:
        signature[table_name] = {
            "columns": tuple(
                sorted(
                    (
                        column["name"],
                        str(column["type"]),
                        column["nullable"],
                        column["name"] in inspector.get_pk_constraint(table_name)["constrained_columns"],
                    )
                    for column in inspector.get_columns(table_name)
                )
            ),
            "indexes": tuple(
                sorted(
                    (index["name"], tuple(index["column_names"]), index["unique"])
                    for index in inspector.get_indexes(table_name)
                )
            ),
            "foreign_keys": tuple(
                sorted(
                    (
                        tuple(foreign_key["constrained_columns"]),
                        foreign_key["referred_table"],
                        tuple(foreign_key["referred_columns"]),
                        foreign_key["options"].get("ondelete"),
                    )
                    for foreign_key in inspector.get_foreign_keys(table_name)
                )
            ),
            "uniques": tuple(
                sorted(
                    (constraint["name"], tuple(constraint["column_names"]))
                    for constraint in inspector.get_unique_constraints(table_name)
                )
            ),
        }
    return signature


def task6_model_schema_signature() -> dict:
    from server.application.models import Base

    signature = {}
    for table_name in TASK6_SCHEMA_TABLES:
        table = Base.metadata.tables[table_name]
        signature[table_name] = {
            "columns": tuple(
                sorted(
                    (column.name, str(column.type), column.nullable, column.primary_key)
                    for column in table.columns
                )
            ),
            "indexes": tuple(
                sorted(
                    (index.name, tuple(column.name for column in index.columns), index.unique)
                    for index in table.indexes
                )
            ),
            "foreign_keys": tuple(
                sorted(
                    (
                        tuple(column.name for column in constraint.columns),
                        next(iter(constraint.elements)).column.table.name,
                        tuple(element.column.name for element in constraint.elements),
                        constraint.ondelete,
                    )
                    for constraint in table.foreign_key_constraints
                )
            ),
            "uniques": tuple(
                sorted(
                    (constraint.name, tuple(column.name for column in constraint.columns))
                    for constraint in table.constraints
                    if constraint.__class__.__name__ == "UniqueConstraint"
                )
            ),
        }
    return signature


def insert_revision_005_assignment_rows(connection) -> None:
    now = "2026-07-14 00:00:00"
    connection.execute(
        text(
            """
            INSERT INTO users (
                id, username, password_hash, password_algorithm, role, role_label, name,
                status, college, school, must_change_password, created_at, updated_at
            ) VALUES (
                'task6-teacher-user', 'task6-teacher', 'hash', 'argon2', 'teacher', '指导老师', '试卷教师',
                'active', '土木工程学院', '湖南大学', 0, :now, :now
            )
            """
        ),
        {"now": now},
    )
    connection.execute(
        text(
            "INSERT INTO teachers (id, user_id, teacher_no, college, course, created_at) "
            "VALUES ('task6-teacher', 'task6-teacher-user', 'TP6', '土木工程学院', '土力学', :now)"
        ),
        {"now": now},
    )
    connection.execute(
        text(
            """
            INSERT INTO questions (
                id, text, question_type, options, rubric, difficulty, points, subject_id,
                attachments, grading_mode, status, source_metadata, source, created_at, updated_at
            ) VALUES (
                'task6-question', '迁移保留题干', '简答题', '[]', '[]', '基础', 12, 'soil-mechanics',
                '[]', 'manual', 'review_required', '{}', 'textbook', :now, :now
            )
            """
        ),
        {"now": now},
    )
    connection.execute(
        text(
            """
            INSERT INTO assignments (
                id, title, description, teacher_id, total_points, allow_resubmit,
                auto_grade, status, created_at
            ) VALUES (
                'task6-assignment', '迁移保留作业', '保留的描述', 'task6-teacher', 12, 0, 0, 'published', :now
            )
            """
        ),
        {"now": now},
    )
    connection.execute(
        text(
            "INSERT INTO assignment_questions (id, assignment_id, question_id, sequence, points) "
            "VALUES ('task6-assignment-question', 'task6-assignment', 'task6-question', 1, 12)"
        )
    )


def test_fresh_and_historical_migrations_have_task1_schema_parity(tmp_path: Path, database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database

    historical_url = f"sqlite:///{tmp_path / 'historical.db'}"
    upgrade_database(database_url)
    upgrade_database(historical_url, "003_submission_feedback")

    historical_database = create_database(historical_url)
    historical_inspector = inspect(historical_database.engine)
    assert_revision_003_schema(historical_database)
    assert {"subjects", "knowledge_points", "question_knowledge_points"}.isdisjoint(historical_inspector.get_table_names())
    assert "practice_attempts" in historical_inspector.get_table_names()
    assert "feedback" in {column["name"] for column in historical_inspector.get_columns("submissions")}
    historical_question_columns = {column["name"] for column in historical_inspector.get_columns("questions")}
    assert {"subject_id", "attachments", "answer_word_limit", "grading_mode", "status", "source_metadata", "content_fingerprint"}.isdisjoint(historical_question_columns)

    upgrade_database(historical_url)
    fresh_signature = task1_schema_signature(create_database(database_url))
    historical_signature = task1_schema_signature(create_database(historical_url))
    assert fresh_signature == historical_signature


def test_fresh_and_historical_task6_schema_matches_models(tmp_path: Path) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database

    fresh_url = f"sqlite:///{tmp_path / 'task6-fresh.db'}"
    historical_url = f"sqlite:///{tmp_path / 'task6-historical.db'}"
    upgrade_database(fresh_url)
    upgrade_database(historical_url, "005_subject_mastery")
    historical_database = create_database(historical_url)
    with historical_database.engine.begin() as connection:
        insert_revision_005_assignment_rows(connection)
    upgrade_database(historical_url)

    fresh_signature = task6_database_schema_signature(create_database(fresh_url))
    historical_signature = task6_database_schema_signature(create_database(historical_url))
    model_signature = task6_model_schema_signature()
    assert fresh_signature == historical_signature
    assert fresh_signature == model_signature


def test_migration_006_populated_downgrade_preserves_revision_005_rows_and_schema(tmp_path: Path) -> None:
    from server.application.database import create_database
    from server.application.migrations import downgrade_database, upgrade_database

    database_url = f"sqlite:///{tmp_path / 'task6-roundtrip.db'}"
    upgrade_database(database_url, "005_subject_mastery")
    database = create_database(database_url)
    with database.engine.begin() as connection:
        insert_revision_005_assignment_rows(connection)
    revision_005_signature = task6_database_schema_signature(
        database, ("assignments", "assignment_questions")
    )

    upgrade_database(database_url)
    database = create_database(database_url)
    now = "2026-07-14 01:00:00"
    with database.engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO papers (
                    id, subject_id, title, description, duration_minutes, total_points,
                    status, version, assembly_mode, assembly_blueprint, assembly_seed,
                    shortages, created_by, created_at, updated_at
                ) VALUES (
                    'task6-paper', 'soil-mechanics', '迁移回滚试卷', '回滚时仅移除新实体', 60, 12,
                    'published', 1, 'manual', '[]', 7, '[]', 'task6-teacher-user', :now, :now
                )
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO paper_questions (
                    id, paper_id, question_id, section_title, sequence, points
                ) VALUES (
                    'task6-paper-question', 'task6-paper', 'task6-question', '一、简答题', 1, 12
                )
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE assignments
                SET paper_id = 'task6-paper', duration_minutes = 60, show_answers_mode = 'after_close'
                WHERE id = 'task6-assignment'
                """
            )
        )
        connection.execute(
            text(
                "UPDATE assignment_questions SET question_snapshot = :snapshot "
                "WHERE id = 'task6-assignment-question'"
            ),
            {"snapshot": json.dumps({"text": "迁移快照", "correctAnswer": "答案"}, ensure_ascii=False)},
        )

    downgrade_database(database_url, "005_subject_mastery")
    database = create_database(database_url)
    inspector = inspect(database.engine)
    assert {"papers", "paper_questions"}.isdisjoint(inspector.get_table_names())
    assert task6_database_schema_signature(
        database, ("assignments", "assignment_questions")
    ) == revision_005_signature
    with database.engine.connect() as connection:
        assignment = connection.execute(
            text(
                "SELECT id, title, description, teacher_id, total_points, allow_resubmit, auto_grade, status "
                "FROM assignments WHERE id = 'task6-assignment'"
            )
        ).one()
        assignment_question = connection.execute(
            text(
                "SELECT id, assignment_id, question_id, sequence, points "
                "FROM assignment_questions WHERE id = 'task6-assignment-question'"
            )
        ).one()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert assignment == (
        "task6-assignment", "迁移保留作业", "保留的描述", "task6-teacher", 12.0, 0, 0, "published"
    )
    assert assignment_question == (
        "task6-assignment-question", "task6-assignment", "task6-question", 1, 12.0
    )
    assert revision == "005_subject_mastery"

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.engine.connect() as connection:
        upgraded_assignment = connection.execute(
            text(
                "SELECT title, paper_id, duration_minutes, show_answers_mode "
                "FROM assignments WHERE id = 'task6-assignment'"
            )
        ).one()
        upgraded_question = connection.execute(
            text(
                "SELECT question_id, sequence, points, question_snapshot "
                "FROM assignment_questions WHERE id = 'task6-assignment-question'"
            )
        ).one()
    assert upgraded_assignment == ("迁移保留作业", None, None, "after_submission")
    assert upgraded_question[:3] == ("task6-question", 1, 12.0)
    upgraded_snapshot = upgraded_question.question_snapshot
    if isinstance(upgraded_snapshot, str):
        upgraded_snapshot = json.loads(upgraded_snapshot)
    assert upgraded_snapshot["id"] == "task6-question"
    assert upgraded_snapshot["text"] == "迁移保留题干"
    assert upgraded_snapshot["sequence"] == 1
    assert upgraded_snapshot["points"] == 12


def test_fresh_revision_003_schema_matches_frozen_signature(tmp_path: Path) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database

    database_url = f"sqlite:///{tmp_path / 'revision-three.db'}"
    upgrade_database(database_url, "003_submission_feedback")
    assert_revision_003_schema(create_database(database_url))


def test_assessment_catalog_downgrade_restores_revision_003_schema_and_rows(tmp_path: Path, database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import downgrade_database, upgrade_database

    upgrade_database(database_url, "003_submission_feedback")
    database = create_database(database_url)
    with database.engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO questions (
                    id, text, question_type, options, correct_answer, explanation, rubric,
                    difficulty, points, chapter, knowledge_point, source, created_by,
                    created_at, updated_at
                ) VALUES (
                    :id, :text, :question_type, :options, :correct_answer, :explanation, :rubric,
                    :difficulty, :points, :chapter, :knowledge_point, :source, :created_by,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "id": "exercise-old",
                "text": "说明桩侧阻力。",
                "question_type": "简答题",
                "options": "[]",
                "correct_answer": None,
                "explanation": None,
                "rubric": "[]",
                "difficulty": "基础",
                "points": 10,
                "chapter": "第3章 桩基础",
                "knowledge_point": "桩侧阻力",
                "source": "textbook",
                "created_by": None,
                "created_at": "2026-01-01 00:00:00",
                "updated_at": "2026-01-01 00:00:00",
            },
    )
    upgrade_database(database_url)
    head_inspector = inspect(database.engine)
    assert {"subjects", "knowledge_points", "question_knowledge_points"}.issubset(head_inspector.get_table_names())
    assert any(
        foreign_key["name"] == "fk_questions_subject_id_subjects"
        for foreign_key in head_inspector.get_foreign_keys("questions")
    )
    downgrade_database(database_url, "003_submission_feedback")

    database = create_database(database_url)
    assert_revision_003_schema(database)
    inspector = inspect(database.engine)
    assert {"subjects", "knowledge_points", "question_knowledge_points"}.isdisjoint(inspector.get_table_names())
    question_columns = {column["name"] for column in inspector.get_columns("questions")}
    assert {"subject_id", "attachments", "answer_word_limit", "grading_mode", "status", "source_metadata", "content_fingerprint"}.isdisjoint(question_columns)
    assert all("subject_id" not in foreign_key["constrained_columns"] for foreign_key in inspector.get_foreign_keys("questions"))
    with database.engine.connect() as connection:
        legacy_question = connection.execute(
            text("SELECT id, text, knowledge_point FROM questions WHERE id = :id"),
            {"id": "exercise-old"},
        ).one()
    assert legacy_question == ("exercise-old", "说明桩侧阻力。", "桩侧阻力")


def test_assessment_catalog_migration_backfills_legacy_questions(tmp_path: Path, database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import Question, QuestionKnowledgePoint, Subject

    make_legacy_database(tmp_path / "test.db")
    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        question = session.get(Question, "exercise-old")
        links = session.scalars(
            select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question.id)
        ).all()
        assert foundation.title == "基础工程"
        assert question.subject_id == foundation.id
        assert question.knowledge_point == "桩侧阻力"
        assert question.status == "active"
        assert len(links) == 1


def test_assessment_catalog_migration_marks_blank_legacy_knowledge_points_for_review(tmp_path: Path, database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import Question, QuestionKnowledgePoint

    make_legacy_database(tmp_path / "test.db", knowledge_point="   ")
    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        question = session.get(Question, "exercise-old")
        links = session.scalars(
            select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question.id)
        ).all()
        assert question.subject_id == "foundation-engineering"
        assert question.status == "review_required"
        assert links == []


def test_direct_active_question_without_subject_or_links_is_marked_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import Question

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        question = Question(
            id="question-incomplete",
            text="说明桩侧阻力。",
            question_type="简答题",
            status="active",
        )
        session.add(question)
        session.commit()
        assert question.status == "review_required"


def test_flush_persists_incomplete_active_question_review_status(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import Question

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        question = Question(
            id="flush-incomplete-question",
            text="说明桩侧阻力。",
            question_type="简答题",
            status="active",
        )
        session.add(question)
        session.flush()
        persisted_status = session.connection().execute(
            select(Question.status).where(Question.id == question.id)
        ).scalar_one()
        assert question.status == "review_required"
        assert persisted_status == "review_required"
        assert question not in session.dirty
        session.rollback()


def test_collection_removal_marks_active_question_for_review_within_flush(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        point = KnowledgePoint(
            id="collection-removal-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="桩基础",
            normalized_name="桩基础",
        )
        question = Question(
            id="collection-removal-question",
            text="说明桩基础。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="collection-removal-link", knowledge_point=point),
            ],
        )
        session.add(question)
        session.commit()

    with database.session() as session:
        question = session.get(Question, "collection-removal-question")
        question.knowledge_point_links.remove(question.knowledge_point_links[0])
        session.flush()
        persisted_status = session.connection().execute(
            select(Question.status).where(Question.id == question.id)
        ).scalar_one()
        assert question.status == "review_required"
        assert persisted_status == "review_required"
        session.rollback()


def test_deleted_link_marks_active_question_for_review_within_flush(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        point = KnowledgePoint(
            id="deleted-link-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基基础",
            normalized_name="地基基础",
        )
        question = Question(
            id="deleted-link-question",
            text="说明地基基础。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="deleted-link", knowledge_point=point),
            ],
        )
        session.add(question)
        session.commit()

    with database.session() as session:
        question = session.get(Question, "deleted-link-question")
        session.delete(question.knowledge_point_links[0])
        session.flush()
        persisted_status = session.connection().execute(
            select(Question.status).where(Question.id == question.id)
        ).scalar_one()
        assert question.status == "review_required"
        assert persisted_status == "review_required"
        session.rollback()


def test_question_knowledge_points_proxy_exposes_multiple_matching_points(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        points = [
            KnowledgePoint(
                id="foundation-point-1",
                subject_id=foundation.id,
                chapter="第1章",
                name="土的物理性质",
                normalized_name="土的物理性质",
            ),
            KnowledgePoint(
                id="foundation-point-2",
                subject_id=foundation.id,
                chapter="第1章",
                name="土的渗透性",
                normalized_name="土的渗透性",
            ),
        ]
        question = Question(
            id="question-multiple-points",
            text="说明土的物理性质和渗透性。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="question-point-link-1", knowledge_point=points[0]),
                QuestionKnowledgePoint(id="question-point-link-2", knowledge_point=points[1]),
            ],
        )
        session.add(question)
        session.commit()
        assert question.status == "active"
        assert [point.id for point in question.knowledge_points] == [point.id for point in points]
        assert [link.question_id for link in question.knowledge_point_links] == [question.id, question.id]
        assert points[0].question_links[0].question is question

        extra_points = [
            KnowledgePoint(
                id="foundation-point-3",
                subject_id=foundation.id,
                chapter="第1章",
                name="土的压缩性",
                normalized_name="土的压缩性",
            ),
            KnowledgePoint(
                id="foundation-point-4",
                subject_id=foundation.id,
                chapter="第1章",
                name="土的抗剪强度",
                normalized_name="土的抗剪强度",
            ),
        ]
        session.add_all(extra_points)
        session.add_all(
            [
                QuestionKnowledgePoint(
                    id="question-point-link-3",
                    question_id=question.id,
                    knowledge_point=extra_points[0],
                ),
                QuestionKnowledgePoint(
                    id="question-point-link-4",
                    question_id=question.id,
                    knowledge_point=extra_points[1],
                ),
            ]
        )
        session.commit()
        assert question.status == "review_required"

        soil = session.get(Subject, "soil-mechanics")
        mismatched_point = KnowledgePoint(
            id="soil-point-1",
            subject_id=soil.id,
            chapter="第1章",
            name="土的压缩性",
            normalized_name="土的压缩性",
        )
        mismatched_question = Question(
            id="question-mismatched-point",
            text="说明土的压缩性。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="question-point-link-mismatched", knowledge_point=mismatched_point),
            ],
        )
        session.add(mismatched_question)
        session.commit()
        assert mismatched_question.status == "review_required"


def test_loaded_link_point_id_reassignment_marks_question_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        soil = session.get(Subject, "soil-mechanics")
        foundation_point = KnowledgePoint(
            id="loaded-foundation-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基变形",
            normalized_name="地基变形",
        )
        soil_point = KnowledgePoint(
            id="loaded-soil-point",
            subject_id=soil.id,
            chapter="第1章",
            name="土的压缩性",
            normalized_name="土的压缩性",
        )
        question = Question(
            id="loaded-link-question",
            text="说明地基变形。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="loaded-link", knowledge_point=foundation_point),
            ],
        )
        session.add_all([question, soil_point])
        session.commit()

    with database.session() as session:
        question = session.get(Question, "loaded-link-question")
        link = question.knowledge_point_links[0]
        assert link.knowledge_point.id == "loaded-foundation-point"
        link.knowledge_point_id = "loaded-soil-point"
        session.commit()
        assert question.status == "review_required"


def test_loaded_link_question_id_reassignment_marks_previous_question_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        point = KnowledgePoint(
            id="reassigned-foundation-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基承载力",
            normalized_name="地基承载力",
        )
        source = Question(
            id="reassignment-source-question",
            text="说明地基承载力。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="reassigned-link", knowledge_point=point),
            ],
        )
        target = Question(
            id="reassignment-target-question",
            text="说明地基承载力的影响因素。",
            question_type="简答题",
            subject_id=foundation.id,
        )
        session.add_all([source, target])
        session.commit()

    with database.session() as session:
        source = session.get(Question, "reassignment-source-question")
        link = source.knowledge_point_links[0]
        link.question_id = "reassignment-target-question"
        session.commit()
        assert source.status == "review_required"


def test_link_question_relationship_reassignment_marks_source_and_overfull_target_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        points = [
            KnowledgePoint(
                id=f"relationship-question-point-{index}",
                subject_id=foundation.id,
                chapter="第1章",
                name=f"知识点{index}",
                normalized_name=f"知识点{index}",
            )
            for index in range(1, 5)
        ]
        source = Question(
            id="relationship-source-question",
            text="说明知识点 4。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="relationship-source-link", knowledge_point=points[3]),
            ],
        )
        target = Question(
            id="relationship-target-question",
            text="说明知识点 1 到 3。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id=f"relationship-target-link-{index}", knowledge_point=point)
                for index, point in enumerate(points[:3], start=1)
            ],
        )
        session.add_all([source, target])
        session.commit()

    with database.session() as session:
        source = session.get(Question, "relationship-source-question")
        target = session.get(Question, "relationship-target-question")
        link = source.knowledge_point_links[0]
        assert link.question is source
        link.question = target
        session.commit()
        assert source.status == "review_required"
        assert target.status == "review_required"


def test_link_knowledge_point_relationship_reassignment_marks_question_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        soil = session.get(Subject, "soil-mechanics")
        foundation_point = KnowledgePoint(
            id="relationship-foundation-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基变形",
            normalized_name="地基变形",
        )
        alternate_foundation_point = KnowledgePoint(
            id="relationship-alternate-foundation-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基承载力",
            normalized_name="地基承载力",
        )
        soil_point = KnowledgePoint(
            id="relationship-soil-point",
            subject_id=soil.id,
            chapter="第1章",
            name="土的压缩性",
            normalized_name="土的压缩性",
        )
        question = Question(
            id="relationship-point-question",
            text="说明地基变形。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="relationship-point-link", knowledge_point=foundation_point),
            ],
        )
        session.add_all([question, alternate_foundation_point, soil_point])
        session.commit()

    with database.session() as session:
        question = session.get(Question, "relationship-point-question")
        link = question.knowledge_point_links[0]
        alternate_foundation_point = session.get(KnowledgePoint, "relationship-alternate-foundation-point")
        soil_point = session.get(KnowledgePoint, "relationship-soil-point")
        assert link.knowledge_point.id == "relationship-foundation-point"
        link.knowledge_point = alternate_foundation_point
        session.commit()
        assert question.status == "active"
        link.knowledge_point = soil_point
        session.commit()
        assert question.status == "review_required"


def test_question_subject_relationship_reassignment_marks_question_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        foundation_point = KnowledgePoint(
            id="relationship-subject-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基承载力",
            normalized_name="地基承载力",
        )
        question = Question(
            id="relationship-subject-question",
            text="说明地基承载力。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="relationship-subject-link", knowledge_point=foundation_point),
            ],
        )
        session.add(question)
        session.commit()

    with database.session() as session:
        question = session.get(Question, "relationship-subject-question")
        soil = session.get(Subject, "soil-mechanics")
        assert question.subject.id == "foundation-engineering"
        question.subject = soil
        session.commit()
        assert question.status == "review_required"


def test_question_subject_id_reassignment_marks_question_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        point = KnowledgePoint(
            id="scalar-question-subject-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基承载力",
            normalized_name="地基承载力",
        )
        question = Question(
            id="scalar-question-subject-question",
            text="说明地基承载力。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="scalar-question-subject-link", knowledge_point=point),
            ],
        )
        session.add(question)
        session.commit()

    with database.session() as session:
        question = session.get(Question, "scalar-question-subject-question")
        question.subject_id = "soil-mechanics"
        session.flush()
        assert question.status == "review_required"
        session.rollback()


def test_knowledge_point_subject_relationship_reassignment_marks_linked_questions_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        point = KnowledgePoint(
            id="relationship-point-subject-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基基础",
            normalized_name="地基基础",
        )
        question = Question(
            id="relationship-point-subject-question",
            text="说明地基基础。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="relationship-point-subject-link", knowledge_point=point),
            ],
        )
        session.add(question)
        session.commit()

    with database.session() as session:
        point = session.get(KnowledgePoint, "relationship-point-subject-point")
        soil = session.get(Subject, "soil-mechanics")
        assert point.subject.id == "foundation-engineering"
        point.subject = soil
        session.commit()
        question = session.get(Question, "relationship-point-subject-question")
        assert question.status == "review_required"


def test_knowledge_point_subject_id_reassignment_marks_linked_questions_for_review(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        point = KnowledgePoint(
            id="scalar-point-subject-point",
            subject_id=foundation.id,
            chapter="第1章",
            name="地基基础",
            normalized_name="地基基础",
        )
        question = Question(
            id="scalar-point-subject-question",
            text="说明地基基础。",
            question_type="简答题",
            subject_id=foundation.id,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="scalar-point-subject-link", knowledge_point=point),
            ],
        )
        session.add(question)
        session.commit()

    with database.session() as session:
        point = session.get(KnowledgePoint, "scalar-point-subject-point")
        point.subject_id = "soil-mechanics"
        session.flush()
        question = session.get(Question, "scalar-point-subject-question")
        assert question.status == "review_required"
        session.rollback()


def test_schema_upgrade_and_legacy_import_preserve_data(tmp_path: Path, database_url: str) -> None:
    from server.application.database import create_database
    from server.application.legacy_import import import_legacy_sqlite
    from server.application.migrations import upgrade_database
    from server.application.models import Question, Resource, Setting, Student, User

    legacy_path = tmp_path / "legacy.db"
    make_legacy_database(legacy_path)
    upgrade_database(database_url)
    database = create_database(database_url)

    first = import_legacy_sqlite(legacy_path, database)
    second = import_legacy_sqlite(legacy_path, database)

    assert first == {"users": 1, "resources": 1, "questions": 1, "settings": 1}
    assert second == {"users": 0, "resources": 0, "questions": 0, "settings": 0}
    with database.session() as session:
        assert session.scalar(select(User).where(User.username == "old-student")).name == "旧学生"
        assert session.scalar(select(Student).where(Student.student_no == "20260001")) is not None
        assert session.scalar(select(Resource).where(Resource.title == "桩基础讲义")) is not None
        assert session.scalar(select(Question).where(Question.id == "exercise-old")) is not None
        assert session.scalar(select(Setting).where(Setting.key == "qa.answerStyle")).value == "先给结论"
