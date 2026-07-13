from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sqlalchemy import select


def make_legacy_database(path: Path) -> None:
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
            "桩侧阻力",
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
        assert len(links) == 1


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
