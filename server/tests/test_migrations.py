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
