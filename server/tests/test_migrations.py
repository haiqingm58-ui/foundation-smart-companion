from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sqlalchemy import select


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
