from __future__ import annotations

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import time_ns

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from server.tests.test_student import student_context


CSRF = {"X-CSRF-Token": "student-csrf"}


def _seed_catalog(database, total: int = 25) -> None:
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject

    with database.session() as session:
        if not session.get(Subject, "soil-mechanics"):
            session.add(Subject(id="soil-mechanics", title="土力学", slug="soil-mechanics", status="active"))
        points = [
            KnowledgePoint(id="soil-kp-1", subject_id="soil-mechanics", chapter="第一章", name="渗流", normalized_name="渗流"),
            KnowledgePoint(id="soil-kp-2", subject_id="soil-mechanics", chapter="第二章", name="固结", normalized_name="固结"),
            KnowledgePoint(id="soil-kp-other", subject_id="other-subject", chapter="其他", name="其他点", normalized_name="其他点"),
        ]
        if not session.get(Subject, "other-subject"):
            session.add(Subject(id="other-subject", title="其他课程", slug="other-subject", status="active"))
        for point in points:
            if not session.get(KnowledgePoint, point.id):
                session.add(point)
        session.flush()
        for index in range(total):
            question_id = f"soil-question-{index:02d}"
            if session.get(Question, question_id):
                continue
            point_id = "soil-kp-1" if index % 2 == 0 else "soil-kp-2"
            session.add(
                Question(
                    id=question_id,
                    text=f"土力学题目 {index}",
                    question_type="单项选择题",
                    options=[{"label": "A", "text": "正确"}, {"label": "B", "text": "错误"}],
                    correct_answer="A",
                    explanation="服务器解析",
                    rubric=[{"criterion": "准确"}],
                    difficulty="基础",
                    points=10,
                    chapter="第一章" if point_id == "soil-kp-1" else "第二章",
                    subject_id="soil-mechanics",
                    status="active",
                    source="soil-mechanics-bank",
                    knowledge_point_links=[QuestionKnowledgePoint(id=f"soil-link-{index:02d}", knowledge_point_id=point_id)],
                )
            )
        session.add(
            Question(
                id="other-question",
                text="其他课程题目",
                question_type="单项选择题",
                options=[{"label": "A", "text": "正确"}],
                correct_answer="A",
                explanation="不应出现",
                rubric=[],
                difficulty="基础",
                points=10,
                chapter="其他",
                subject_id="other-subject",
                status="active",
                source="other-bank",
                knowledge_point_links=[QuestionKnowledgePoint(id="other-link", knowledge_point_id="soil-kp-other")],
            )
        )
        session.commit()


@pytest.fixture()
def assessment_context(student_context):
    client, database = student_context
    _seed_catalog(database)
    return client, database


def _practice(client, **body):
    payload = {"subjectId": "soil-mechanics", "mode": "chapter", "chapter": "第一章", "count": 5}
    payload.update(body)
    response = client.post("/api/student/practice-sessions", json=payload, headers=CSRF)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _assignment(database, *, due_at=None, starts_at=None, show_answers_mode="after_submission", allow_resubmit=False, subjective=False, student_id="student-profile", auto_grade=True):
    from server.application.models import Assignment, AssignmentQuestion, AssignmentTarget, Student, Teacher, User

    assignment_id = f"assignment-{show_answers_mode}-{int(subjective)}-{int(allow_resubmit)}-{time_ns()}"
    snapshot = {
        "id": "soil-question-00",
        "subjectId": "soil-mechanics",
        "text": "正式试题",
        "questionType": "简答题" if subjective else "单项选择题",
        "options": [] if subjective else [{"label": "A", "text": "正确"}, {"label": "B", "text": "错误"}],
        "correctAnswer": None if subjective else "A",
        "explanation": "正式解析",
        "rubric": [{"criterion": "过程"}],
        "sourceMetadata": {"sourceAnswer": "A", "nested": {"answer": "A", "provenance": "private"}},
        "knowledgePointIds": ["soil-kp-1"],
        "points": 10,
        "sequence": 1,
    }
    with database.session() as session:
        if not session.get(User, "formal-teacher-user"):
            session.add(User(id="formal-teacher-user", username="formal-teacher", password_hash="hash", password_algorithm="argon2", role="teacher", role_label="教师", name="正式教师", status="active"))
            session.flush()
            session.add(Teacher(id="teacher-any", user_id="formal-teacher-user", teacher_no="FT1", college="土木工程学院"))
            session.flush()
        if student_id != "student-profile" and not session.get(Student, student_id):
            user_id = f"{student_id}-user"
            session.add(User(id=user_id, username=user_id, password_hash="hash", password_algorithm="argon2", role="student", role_label="学生", name="受限学生", status="active"))
            session.flush()
            session.add(Student(id=student_id, user_id=user_id, student_no=f"{student_id}-no"))
            session.flush()
        session.add(Assignment(
            id=assignment_id, title="正式测验", teacher_id="teacher-any", total_points=10,
            starts_at=starts_at, due_at=due_at, duration_minutes=30,
            show_answers_mode=show_answers_mode, allow_resubmit=allow_resubmit, auto_grade=auto_grade, status="published",
        ))
        session.add(AssignmentTarget(id=f"target-{assignment_id}", assignment_id=assignment_id, student_id=student_id))
        session.add(AssignmentQuestion(id=f"aq-{assignment_id}", assignment_id=assignment_id, question_id="soil-question-00", sequence=1, points=10, question_snapshot=snapshot))
        session.commit()
    return assignment_id


def test_practice_selection_subject_filters_modes_counts_shortages_and_recency(assessment_context) -> None:
    from server.application.models import PracticeAttempt

    client, database = assessment_context
    chapter = _practice(client, count=10)
    assert len(chapter["questions"]) == 10
    assert len({item["id"] for item in chapter["questions"]}) == 10
    assert {item["chapter"] for item in chapter["questions"]} == {"第一章"}
    assert all("correctAnswer" not in item and "explanation" not in item and "rubric" not in item for item in chapter["questions"])
    points = _practice(client, mode="knowledge_points", knowledgePointIds=["soil-kp-1", "soil-kp-2"], count=20)
    assert len(points["questions"]) == 20
    assert all(item["subjectId"] == "soil-mechanics" for item in points["questions"])
    cross_subject = client.post("/api/student/practice-sessions", json={"subjectId": "soil-mechanics", "mode": "knowledge_points", "knowledgePointIds": ["soil-kp-1", "soil-kp-other"], "count": 5}, headers=CSRF)
    assert cross_subject.status_code == 422
    assert cross_subject.json()["code"] == "PRACTICE_KNOWLEDGE_POINT_SUBJECT_MISMATCH"
    assert len(_practice(client, count=5)["questions"]) == 5
    assert len(_practice(client, mode="knowledge_points", knowledgePointIds=["soil-kp-1", "soil-kp-2"], count=20)["questions"]) == 20
    assert _practice(client, count=7)["requestedCount"] == 7
    shortage = client.post("/api/student/practice-sessions", json={"subjectId": "soil-mechanics", "mode": "chapter", "chapter": "第一章", "count": 20}, headers=CSRF)
    assert shortage.status_code == 409
    assert shortage.json()["code"] == "PRACTICE_QUESTION_SHORTAGE"
    with database.session() as session:
        session.add(PracticeAttempt(id="recent-correct", student_id="student-profile", question_id="soil-question-00", answer="A", status="graded", score=10, max_score=10, attempt_number=1))
        session.add(PracticeAttempt(id="recent-wrong", student_id="student-profile", question_id="soil-question-02", answer="B", status="graded", score=0, max_score=10, attempt_number=1))
        session.commit()
    ranked = _practice(client, count=12)
    ids = [item["id"] for item in ranked["questions"]]
    assert "soil-question-02" in ids
    assert "soil-question-00" not in ids


def test_student_assessment_catalog_is_subject_scoped_and_reports_available_counts(assessment_context) -> None:
    client, _database = assessment_context

    response = client.get("/api/student/assessment-catalog?subjectId=soil-mechanics")

    assert response.status_code == 200
    data = response.json()["data"]
    soil = next(item for item in data["subjects"] if item["id"] == "soil-mechanics")
    assert soil["title"] == "土力学"
    assert soil["questionCount"] == 25
    assert data["selectedSubjectId"] == "soil-mechanics"
    assert data["chapters"] == [
        {"name": "第一章", "questionCount": 13},
        {"name": "第二章", "questionCount": 12},
    ]
    assert {item["id"]: item["questionCount"] for item in data["knowledgePoints"]} == {
        "soil-kp-1": 13,
        "soil-kp-2": 12,
    }
    assert data["questionTypes"] == [{"name": "单项选择题", "questionCount": 25}]
    assert data["difficulties"] == [{"name": "基础", "questionCount": 25}]


def test_random_practice_applies_question_type_and_difficulty_without_cross_subject_fallback(assessment_context) -> None:
    from server.application.models import Question

    client, database = assessment_context
    with database.session() as session:
        session.get(Question, "soil-question-00").question_type = "判断题"
        session.get(Question, "soil-question-00").options = []
        session.get(Question, "soil-question-00").correct_answer = True
        session.get(Question, "soil-question-00").difficulty = "提高"
        session.commit()

    selected = client.post(
        "/api/student/practice-sessions",
        json={
            "subjectId": "soil-mechanics",
            "mode": "chapter",
            "chapter": "第一章",
            "questionTypes": ["判断题"],
            "difficulties": ["提高"],
            "count": 1,
        },
        headers=CSRF,
    )
    assert selected.status_code == 200
    assert [item["id"] for item in selected.json()["data"]["questions"]] == ["soil-question-00"]

    shortage = client.post(
        "/api/student/practice-sessions",
        json={
            "subjectId": "soil-mechanics",
            "mode": "chapter",
            "chapter": "第一章",
            "questionTypes": ["计算题"],
            "difficulties": ["提高"],
            "count": 1,
        },
        headers=CSRF,
    )
    assert shortage.status_code == 409
    assert shortage.json()["code"] == "PRACTICE_QUESTION_SHORTAGE"


def test_practice_resume_autosave_uses_immutable_snapshot_and_updates_mastery_only(assessment_context) -> None:
    from server.application.models import KnowledgeMastery, Question, Student

    client, database = assessment_context
    created = _practice(client)
    question_id = created["questions"][0]["id"]
    saved = client.put(f"/api/student/practice-sessions/{created['id']}/answers/{question_id}", json={"answer": "A"}, headers=CSRF)
    assert saved.status_code == 200
    resumed = client.get(f"/api/student/practice-sessions/{created['id']}")
    assert resumed.status_code == 200
    assert next(item for item in resumed.json()["data"]["questions"] if item["id"] == question_id)["answer"] == "A"
    with database.session() as session:
        session.get(Question, question_id).correct_answer = "B"
        session.get(Question, question_id).explanation = "篡改后的解析"
        session.commit()
    submitted = client.post(f"/api/student/practice-sessions/{created['id']}/submit", headers=CSRF)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "graded"
    assert submitted.json()["data"]["score"] >= 10
    with database.session() as session:
        assert session.scalar(select(KnowledgeMastery).where(KnowledgeMastery.student_id == "student-profile")) is not None
        assert session.get(Student, "student-profile").average_score == 0


def test_formal_papers_authorize_target_resume_autosave_deadline_and_attempt_limit(assessment_context) -> None:
    client, database = assessment_context
    assignment_id = _assignment(database, due_at=datetime.now(timezone.utc) + timedelta(hours=1))
    listed = client.get("/api/student/papers")
    assert listed.status_code == 200
    metadata = listed.json()["data"]["items"][0]
    assert metadata["assignmentId"] == assignment_id
    assert metadata["teacherName"] == "正式教师"
    assert metadata["status"] == "pending"
    assert metadata["countdown"]["remainingSeconds"] is not None
    started = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF)
    assert started.status_code == 200
    submission_id = started.json()["data"]["submissionId"]
    assert "correctAnswer" not in started.json()["data"]["questions"][0]
    duplicate = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF)
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["submissionId"] == submission_id
    question_id = started.json()["data"]["questions"][0]["id"]
    assert client.put(f"/api/student/submissions/{submission_id}/answers/{question_id}", json={"answer": "A"}, headers=CSRF).status_code == 200
    resumed_list = client.get("/api/student/papers").json()["data"]["items"]
    assert next(item for item in resumed_list if item["assignmentId"] == assignment_id)["status"] == "in_progress"
    assert client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]["submissionId"] == submission_id
    inaccessible_id = _assignment(database, student_id="other-student")
    inaccessible = client.post(f"/api/student/assignments/{inaccessible_id}/start", headers=CSRF)
    assert inaccessible.status_code == 404
    assert client.post(f"/api/student/submissions/{submission_id}/submit", headers=CSRF).status_code == 200
    graded_list = client.get("/api/student/papers").json()["data"]["items"]
    graded_meta = next(item for item in graded_list if item["assignmentId"] == assignment_id)
    assert graded_meta["status"] == "graded"
    assert graded_meta["score"] == 10
    assert graded_meta["submittedAt"] is not None
    assert client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).status_code == 409
    overdue_id = _assignment(database, due_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    assert client.post(f"/api/student/assignments/{overdue_id}/start", headers=CSRF).status_code == 409


def test_formal_submission_grades_server_snapshot_preserves_secrecy_and_handles_manual_review(assessment_context) -> None:
    from server.application.models import Student

    client, database = assessment_context
    assignment_id = _assignment(database, show_answers_mode="never")
    start = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    submission_id, question_id = start["submissionId"], start["questions"][0]["id"]
    client.put(f"/api/student/submissions/{submission_id}/answers/{question_id}", json={"answer": "A"}, headers=CSRF)
    submitted = client.post(f"/api/student/submissions/{submission_id}/submit", headers=CSRF)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "graded"
    result = client.get(f"/api/student/submissions/{submission_id}/result")
    assert result.status_code == 200
    assert "correctAnswer" not in result.json()["data"]["questions"][0]
    with database.session() as session:
        assert session.get(Student, "student-profile").average_score == 100
    manual_id = _assignment(database, subjective=True)
    manual = client.post(f"/api/student/assignments/{manual_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{manual['submissionId']}/answers/{manual['questions'][0]['id']}", json={"answer": "过程"}, headers=CSRF)
    pending = client.post(f"/api/student/submissions/{manual['submissionId']}/submit", headers=CSRF)
    assert pending.status_code == 200
    assert pending.json()["data"]["status"] == "pending_review"
    manual_result = client.get(f"/api/student/submissions/{manual['submissionId']}/result")
    assert manual_result.status_code == 200
    assert manual_result.json()["data"]["showAnswers"] is True
    assert manual_result.json()["data"]["questions"][0]["explanation"] == "正式解析"


def test_migration_007_preserves_existing_submission_history(tmp_path) -> None:
    from sqlalchemy import text

    from server.application.database import create_database
    from server.application.migrations import downgrade_database, upgrade_database

    database_url = f"sqlite:///{tmp_path / 'assessment-migration.db'}"
    upgrade_database(database_url, "006_papers_and_snapshots")
    database = create_database(database_url)
    with database.engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, username, password_hash, password_algorithm, role, role_label, name, status, college, school, must_change_password, created_at, updated_at) VALUES ('migration-user', 'migration-user', 'hash', 'argon2', 'student', '学生', '迁移学生', 'active', '学院', '学校', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO students (id, user_id, student_no, progress, average_score, created_at) VALUES ('migration-student', 'migration-user', 'MS1', 0, 0, CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO users (id, username, password_hash, password_algorithm, role, role_label, name, status, college, school, must_change_password, created_at, updated_at) VALUES ('migration-teacher-user', 'migration-teacher', 'hash', 'argon2', 'teacher', '教师', '迁移教师', 'active', '学院', '学校', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO teachers (id, user_id, teacher_no, college, course, created_at) VALUES ('migration-teacher', 'migration-teacher-user', 'MT1', '学院', '课程', CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO questions (id, text, question_type, options, rubric, difficulty, points, attachments, grading_mode, status, source_metadata, source, created_at, updated_at) VALUES ('migration-question', '迁移题目', '简答题', '[]', '[]', '基础', 10, '[]', 'manual', 'review_required', '{}', 'legacy', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO assignments (id, title, description, teacher_id, total_points, allow_resubmit, auto_grade, status, created_at) VALUES ('migration-assignment', '迁移作业', '', 'migration-teacher', 10, 0, 0, 'published', CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO submissions (id, assignment_id, student_id, attempt_number, status, score, feedback, submitted_at) VALUES ('migration-submission', 'migration-assignment', 'migration-student', 1, 'graded', 8, '保留反馈', CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO submission_answers (id, submission_id, question_id, answer, score, criteria_scores, confidence, feedback) VALUES ('migration-answer', 'migration-submission', 'migration-question', '\"旧答案\"', 8, '{}', 1, '保留答案反馈')"))
    upgrade_database(database_url)
    with database.engine.connect() as connection:
        assert connection.execute(text("SELECT student_no FROM students WHERE id = 'migration-student'")).scalar_one() == "MS1"
        assert connection.execute(text("SELECT feedback FROM submissions WHERE id = 'migration-submission'")).scalar_one() == "保留反馈"
        assert connection.execute(text("SELECT answer FROM submission_answers WHERE id = 'migration-answer'")).scalar_one() == '"旧答案"'
        assert {"practice_sessions", "practice_session_questions"}.issubset(set(connection.dialect.get_table_names(connection)))
    downgrade_database(database_url, "006_papers_and_snapshots")
    legacy = create_database(database_url)
    with legacy.engine.connect() as connection:
        assert connection.execute(text("SELECT score FROM submissions WHERE id = 'migration-submission'")).scalar_one() == 8
        assert "started_at" not in {column["name"] for column in __import__("sqlalchemy", fromlist=["inspect"]).inspect(legacy.engine).get_columns("submissions")}
        assert {"practice_sessions", "practice_session_questions"}.isdisjoint(set(connection.dialect.get_table_names(connection)))


@pytest.mark.parametrize("mode", ["never", "after_close"])
def test_student_safe_snapshot_never_leaks_private_import_fields(assessment_context, mode: str) -> None:
    client, database = assessment_context
    assignment_id = _assignment(database, show_answers_mode=mode)
    practice = _practice(client)
    start = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    for question in (practice["questions"][0], start["questions"][0]):
        rendered = str(question)
        assert "sourceMetadata" not in question
        assert "sourceAnswer" not in rendered
        assert "provenance" not in rendered
        assert "correctAnswer" not in question
        assert "explanation" not in question
        assert "rubric" not in question
    client.put(f"/api/student/submissions/{start['submissionId']}/answers/{start['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{start['submissionId']}/submit", headers=CSRF)
    result = client.get(f"/api/student/submissions/{start['submissionId']}/result").json()["data"]
    assert result["showAnswers"] is False
    assert "feedback" not in result["questions"][0]
    assert "explanation" not in result["questions"][0]


def test_after_submission_reveals_and_autograde_false_stays_pending(assessment_context) -> None:
    client, database = assessment_context
    revealed_id = _assignment(database, show_answers_mode="after_submission")
    revealed = client.post(f"/api/student/assignments/{revealed_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{revealed['submissionId']}/answers/{revealed['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{revealed['submissionId']}/submit", headers=CSRF)
    assert client.get(f"/api/student/submissions/{revealed['submissionId']}/result").json()["data"]["questions"][0]["explanation"] == "正式解析"
    manual_id = _assignment(database, auto_grade=False)
    manual = client.post(f"/api/student/assignments/{manual_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{manual['submissionId']}/answers/{manual['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    pending = client.post(f"/api/student/submissions/{manual['submissionId']}/submit", headers=CSRF).json()["data"]
    assert pending["status"] == "pending_review"
    assert pending["score"] is None


@pytest.mark.parametrize("answer", [{"label": "A"}, "Z", ["A", "A"], ["A"], "x" * 17000])
def test_autosave_rejects_invalid_or_oversized_answers(assessment_context, answer) -> None:
    client, _database = assessment_context
    practice = _practice(client)
    response = client.put(f"/api/student/practice-sessions/{practice['id']}/answers/{practice['questions'][0]['id']}", json={"answer": answer}, headers=CSRF)
    assert response.status_code in {413, 422}
    assert response.json()["success"] is False
    assert client.put(f"/api/student/practice-sessions/{practice['id']}/answers/{practice['questions'][0]['id']}", json={"answer": None}, headers=CSRF).status_code == 200


def test_migration_007_constraints_and_nullable_start_state(tmp_path) -> None:
    from sqlalchemy import inspect
    from server.application.database import create_database
    from server.application.migrations import upgrade_database

    database_url = f"sqlite:///{tmp_path / 'constraints.db'}"
    upgrade_database(database_url)
    inspector = inspect(create_database(database_url).engine)
    assert "submitted_at" in {column["name"] for column in inspector.get_columns("submissions") if column["nullable"]}
    assert ("assignment_id", "student_id", "attempt_number") in {tuple(item["column_names"]) for item in inspector.get_unique_constraints("submissions")}
    assert ("submission_id", "question_id") in {tuple(item["column_names"]) for item in inspector.get_unique_constraints("submission_answers")}
    indexes = {item["name"]: item for item in inspector.get_indexes("submissions")}
    assert {"uq_submission_one_in_progress", "ix_submissions_submitted_at"}.issubset(indexes)


def test_after_close_boundary_and_all_student_object_routes_are_idor_safe(assessment_context) -> None:
    from server.application.models import SessionToken
    from server.application.security import token_digest

    client, database = assessment_context
    after_close_id = _assignment(database, show_answers_mode="after_close")
    _assignment(database, student_id="other-student")
    formal = client.post(f"/api/student/assignments/{after_close_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{formal['submissionId']}/answers/{formal['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{formal['submissionId']}/submit", headers=CSRF)
    assert client.get(f"/api/student/submissions/{formal['submissionId']}/result").json()["data"]["showAnswers"] is False
    with database.session() as session:
        session.execute(select(__import__("server.application.models", fromlist=["Assignment"]).Assignment).where(__import__("server.application.models", fromlist=["Assignment"]).Assignment.id == after_close_id)).scalar_one().status = "closed"
        session.add(SessionToken(id="other-session", user_id="other-student-user", token_hash=token_digest("other-token"), csrf_hash=token_digest("other-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        session.commit()
    assert client.get(f"/api/student/submissions/{formal['submissionId']}/result").json()["data"]["showAnswers"] is True
    practice = _practice(client)
    other = TestClient(client.app)
    other.cookies.set("foundation_session", "other-token")
    other.cookies.set("foundation_csrf", "other-csrf")
    other_headers = {"X-CSRF-Token": "other-csrf"}
    assert other.get(f"/api/student/practice-sessions/{practice['id']}").status_code == 404
    assert other.put(f"/api/student/practice-sessions/{practice['id']}/answers/{practice['questions'][0]['id']}", json={"answer": "A"}, headers=other_headers).status_code == 404
    assert other.post(f"/api/student/practice-sessions/{practice['id']}/submit", headers=other_headers).status_code == 404
    assert other.put(f"/api/student/submissions/{formal['submissionId']}/answers/{formal['questions'][0]['id']}", json={"answer": "A"}, headers=other_headers).status_code == 404
    assert other.post(f"/api/student/submissions/{formal['submissionId']}/submit", headers=other_headers).status_code == 404
    assert other.get(f"/api/student/submissions/{formal['submissionId']}/result").status_code == 404


def test_teacher_manual_grade_recalculates_average_and_hides_in_progress(assessment_context) -> None:
    from server.application.models import SessionToken, Student
    from server.application.security import token_digest

    client, database = assessment_context
    completed_id = _assignment(database)
    completed = client.post(f"/api/student/assignments/{completed_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{completed['submissionId']}/answers/{completed['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{completed['submissionId']}/submit", headers=CSRF)
    pending_id = _assignment(database, auto_grade=False)
    pending = client.post(f"/api/student/assignments/{pending_id}/start", headers=CSRF).json()["data"]
    with database.session() as session:
        session.add(SessionToken(id="formal-teacher-session", user_id="formal-teacher-user", token_hash=token_digest("formal-teacher-token"), csrf_hash=token_digest("formal-teacher-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        session.commit()
    teacher = TestClient(client.app)
    teacher.cookies.set("foundation_session", "formal-teacher-token")
    teacher.cookies.set("foundation_csrf", "formal-teacher-csrf")
    headers = {"X-CSRF-Token": "formal-teacher-csrf"}
    assert pending["submissionId"] not in {item["id"] for item in teacher.get("/api/teacher/submissions").json()["data"]["items"]}
    client.put(f"/api/student/submissions/{pending['submissionId']}/answers/{pending['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{pending['submissionId']}/submit", headers=CSRF)
    assert teacher.put(f"/api/teacher/submissions/{pending['submissionId']}/grade", json={"score": 5, "feedback": "人工评分"}, headers=headers).status_code == 200
    with database.session() as session:
        assert session.get(Student, "student-profile").average_score == 75


def test_submit_retries_are_idempotent_without_duplicate_history_or_answers(assessment_context) -> None:
    from server.application.models import PracticeAttempt, SubmissionAnswer

    client, database = assessment_context
    practice = _practice(client)
    client.put(f"/api/student/practice-sessions/{practice['id']}/answers/{practice['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    first_practice = client.post(f"/api/student/practice-sessions/{practice['id']}/submit", headers=CSRF)
    retry_practice = client.post(f"/api/student/practice-sessions/{practice['id']}/submit", headers=CSRF)
    assert retry_practice.status_code == 200
    assert retry_practice.json()["data"]["id"] == first_practice.json()["data"]["id"]
    formal_id = _assignment(database)
    formal = client.post(f"/api/student/assignments/{formal_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{formal['submissionId']}/answers/{formal['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    assert client.post(f"/api/student/submissions/{formal['submissionId']}/submit", headers=CSRF).status_code == 200
    assert client.post(f"/api/student/submissions/{formal['submissionId']}/submit", headers=CSRF).status_code == 200
    with database.session() as session:
        assert len(session.scalars(select(PracticeAttempt).where(PracticeAttempt.student_id == "student-profile")).all()) == len(practice["questions"])
        assert len(session.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == formal["submissionId"])).all()) == 1


def test_publication_times_require_offsets_and_normalize_to_utc() -> None:
    from server.application.schemas.paper import PaperPublishInput

    payload = PaperPublishInput.model_validate({
        "studentIds": ["student-profile"],
        "startsAt": "2026-07-15T16:00:00+08:00",
        "dueAt": "2026-07-15T17:00:00+08:00",
    })
    assert payload.starts_at.isoformat() == "2026-07-15T08:00:00+00:00"
    assert payload.due_at.isoformat() == "2026-07-15T09:00:00+00:00"
    with pytest.raises(ValidationError):
        PaperPublishInput.model_validate({"studentIds": ["student-profile"], "startsAt": "2026-07-15T16:00:00"})


def test_parallel_formal_starts_persist_one_in_progress_attempt(assessment_context) -> None:
    from server.application.models import Submission

    client, database = assessment_context
    assignment_id = _assignment(database, show_answers_mode="after_submission")

    def start_once():
        request_client = TestClient(client.app)
        request_client.cookies.set("foundation_session", "student-token")
        request_client.cookies.set("foundation_csrf", "student-csrf")
        return request_client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _unused: start_once(), range(2)))
    assert all(response.status_code == 200 for response in responses)
    assert len({response.json()["data"]["submissionId"] for response in responses}) == 1
    with database.session() as session:
        assert len(session.scalars(select(Submission).where(Submission.assignment_id == assignment_id, Submission.status == "in_progress")).all()) == 1


def test_parallel_first_autosaves_upsert_one_answer(assessment_context) -> None:
    from server.application.models import SubmissionAnswer

    client, database = assessment_context
    assignment_id = _assignment(database)
    started = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]

    def save_once():
        request_client = TestClient(client.app)
        request_client.cookies.set("foundation_session", "student-token")
        request_client.cookies.set("foundation_csrf", "student-csrf")
        return request_client.put(f"/api/student/submissions/{started['submissionId']}/answers/{started['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _unused: save_once(), range(2)))
    assert all(response.status_code == 200 for response in responses)
    with database.session() as session:
        assert len(session.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == started["submissionId"])).all()) == 1


def test_parallel_submits_commit_once_and_return_committed_result(assessment_context) -> None:
    from server.application.models import PracticeAttempt, SubmissionAnswer

    client, database = assessment_context
    practice = _practice(client)
    formal_id = _assignment(database)
    formal = client.post(f"/api/student/assignments/{formal_id}/start", headers=CSRF).json()["data"]

    def submit(path: str):
        request_client = TestClient(client.app)
        request_client.cookies.set("foundation_session", "student-token")
        request_client.cookies.set("foundation_csrf", "student-csrf")
        return request_client.post(path, headers=CSRF)

    with ThreadPoolExecutor(max_workers=2) as pool:
        practice_responses = list(pool.map(lambda _unused: submit(f"/api/student/practice-sessions/{practice['id']}/submit"), range(2)))
    with ThreadPoolExecutor(max_workers=2) as pool:
        formal_responses = list(pool.map(lambda _unused: submit(f"/api/student/submissions/{formal['submissionId']}/submit"), range(2)))
    assert all(response.status_code == 200 for response in practice_responses + formal_responses)
    with database.session() as session:
        assert len(session.scalars(select(PracticeAttempt).where(PracticeAttempt.student_id == "student-profile")).all()) == len(practice["questions"])
        assert len(session.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == formal["submissionId"])).all()) == 1


def test_after_close_never_uses_personal_duration_to_reveal(assessment_context) -> None:
    from server.application.models import AssignmentTarget, SessionToken, Submission
    from server.application.security import token_digest

    client, database = assessment_context
    assignment_id = _assignment(database, show_answers_mode="after_close", due_at=datetime.now(timezone.utc) + timedelta(hours=2))
    _assignment(database, student_id="other-student")
    first = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{first['submissionId']}/answers/{first['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{first['submissionId']}/submit", headers=CSRF)
    with database.session() as session:
        session.add(AssignmentTarget(id="second-target", assignment_id=assignment_id, student_id="other-student"))
        session.add(SessionToken(id="duration-other-session", user_id="other-student-user", token_hash=token_digest("duration-other-token"), csrf_hash=token_digest("duration-other-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        session.get(Submission, first["submissionId"]).started_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        session.commit()
    second = TestClient(client.app)
    second.cookies.set("foundation_session", "duration-other-token")
    second.cookies.set("foundation_csrf", "duration-other-csrf")
    assert second.post(f"/api/student/assignments/{assignment_id}/start", headers={"X-CSRF-Token": "duration-other-csrf"}).status_code == 200
    result = client.get(f"/api/student/submissions/{first['submissionId']}/result").json()["data"]
    assert result["showAnswers"] is False
    assert "explanation" not in result["questions"][0]


def test_student_payload_keeps_safe_image_table_and_formula_attachments(assessment_context) -> None:
    from server.application.models import AssignmentQuestion, Question

    client, database = assessment_context
    attachments = [
        {"kind": "image", "src": "/assets/figure.png", "altText": "渗流图", "sourcePosition": {"private": True}},
        {"kind": "table", "rows": [["a", 1], ["b", 2]], "caption": "数据表", "provenance": "private"},
        {"kind": "formula", "ommlText": "q=kiA", "ommlSource": "<private/>", "sourceMetadata": {"secret": True}},
    ]
    with database.session() as session:
        session.get(Question, "soil-question-00").attachments = attachments
        session.commit()
    practice = _practice(client, count=13)
    practice_question = next(item for item in practice["questions"] if item["id"] == "soil-question-00")
    assert practice_question["attachments"] == [
        {"kind": "image", "src": "/assets/figure.png", "altText": "渗流图"},
        {"kind": "table", "rows": [["a", 1], ["b", 2]], "caption": "数据表"},
        {"kind": "formula", "latex": "q=kiA"},
    ]
    assignment_id = _assignment(database)
    with database.session() as session:
        assignment_question = session.scalar(select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment_id))
        assignment_question.question_snapshot = {**assignment_question.question_snapshot, "attachments": attachments}
        session.commit()
    formal = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    assert formal["questions"][0]["attachments"] == practice_question["attachments"]
    resumed = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    assert resumed["questions"][0]["attachments"] == practice_question["attachments"]
    client.put(f"/api/student/submissions/{formal['submissionId']}/answers/{formal['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    client.post(f"/api/student/submissions/{formal['submissionId']}/submit", headers=CSRF)
    assert client.get(f"/api/student/submissions/{formal['submissionId']}/result").json()["data"]["questions"][0]["attachments"] == practice_question["attachments"]


@pytest.mark.parametrize("existing_answer", [False, True])
def test_barrier_autosave_then_submit_grades_the_committed_answer(assessment_context, monkeypatch, existing_answer: bool) -> None:
    import server.application.api.student_assessment as assessment_api
    from server.application.models import Submission, SubmissionAnswer

    client, database = assessment_context
    assignment_id = _assignment(database)
    started = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    submission_id, question_id = started["submissionId"], started["questions"][0]["id"]
    if existing_answer:
        assert client.put(f"/api/student/submissions/{submission_id}/answers/{question_id}", json={"answer": "B"}, headers=CSRF).status_code == 200
    entered, competing_at_lock, release = Event(), Event(), Event()
    original_validate = assessment_api.validate_student_answer

    def wait_after_claim(snapshot, answer):
        entered.set()
        assert release.wait(5)
        return original_validate(snapshot, answer)

    monkeypatch.setattr(assessment_api, "validate_student_answer", wait_after_claim)

    def checkpoint(event, checkpoint_submission_id):
        if event == "formal_submit_before_lock" and checkpoint_submission_id == submission_id:
            competing_at_lock.set()

    monkeypatch.setattr(client.app.state, "assessment_concurrency_hook", checkpoint, raising=False)

    def request_client():
        result = TestClient(client.app)
        result.cookies.set("foundation_session", "student-token")
        result.cookies.set("foundation_csrf", "student-csrf")
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        autosave = pool.submit(lambda: request_client().put(f"/api/student/submissions/{submission_id}/answers/{question_id}", json={"answer": "A"}, headers=CSRF))
        assert entered.wait(5)
        submit = pool.submit(lambda: request_client().post(f"/api/student/submissions/{submission_id}/submit", headers=CSRF))
        assert competing_at_lock.wait(5)
        release.set()
        autosave_response, submit_response = autosave.result(10), submit.result(10)
    assert autosave_response.status_code == 200
    assert submit_response.status_code == 200
    with database.session() as session:
        record = session.get(Submission, submission_id)
        answers = session.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission_id)).all()
        assert record.status == "graded"
        assert record.score == 10
        assert len(answers) == 1
        assert answers[0].answer == "A"
        assert answers[0].score == 10


@pytest.mark.parametrize("existing_answer", [False, True])
def test_barrier_submit_then_autosave_returns_closed_without_lock_error(assessment_context, monkeypatch, existing_answer: bool) -> None:
    import server.application.api.student_assessment as assessment_api
    from server.application.models import SubmissionAnswer

    client, database = assessment_context
    assignment_id = _assignment(database)
    started = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    submission_id, question_id = started["submissionId"], started["questions"][0]["id"]
    if existing_answer:
        saved = client.put(
            f"/api/student/submissions/{submission_id}/answers/{question_id}",
            json={"answer": "A"},
            headers=CSRF,
        )
        assert saved.status_code == 200
    entered, competing_at_lock, release = Event(), Event(), Event()
    original_grade = assessment_api.grade_objective

    def wait_after_submit_claim(snapshot, answer):
        entered.set()
        assert release.wait(5)
        return original_grade(snapshot, answer)

    monkeypatch.setattr(assessment_api, "grade_objective", wait_after_submit_claim)

    def checkpoint(event, checkpoint_submission_id):
        if event == "formal_autosave_before_lock" and checkpoint_submission_id == submission_id:
            competing_at_lock.set()

    monkeypatch.setattr(client.app.state, "assessment_concurrency_hook", checkpoint, raising=False)

    def request_client():
        result = TestClient(client.app)
        result.cookies.set("foundation_session", "student-token")
        result.cookies.set("foundation_csrf", "student-csrf")
        return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        submit = pool.submit(lambda: request_client().post(f"/api/student/submissions/{submission_id}/submit", headers=CSRF))
        assert entered.wait(5)
        autosave = pool.submit(lambda: request_client().put(f"/api/student/submissions/{submission_id}/answers/{question_id}", json={"answer": "B"}, headers=CSRF))
        assert competing_at_lock.wait(5)
        release.set()
        submit_response, autosave_response = submit.result(10), autosave.result(10)
    assert submit_response.status_code == 200
    assert autosave_response.status_code == 409
    assert autosave_response.json()["code"] == "SUBMISSION_CLOSED"
    with database.session() as session:
        answers = session.scalars(
            select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission_id)
        ).all()
        assert len(answers) == 1
        assert answers[0].answer == ("A" if existing_answer else None)
        assert answers[0].score == (10 if existing_answer else 0)


@pytest.mark.parametrize("question_type,valid,invalid", [
    ("单项选择题", "A", "Z"),
    ("多项选择题", ["A", "B"], ["A", "A"]),
    ("判断题", True, "true"),
    ("填空题", "渗流", []),
    ("简答题", "abc", "abcd"),
    ("计算题", "abc", "abcd"),
])
def test_all_answer_types_use_same_validation_on_practice_and_formal_autosave(assessment_context, question_type, valid, invalid) -> None:
    from server.application.models import AssignmentQuestion, Question

    client, database = assessment_context
    with database.session() as session:
        question = session.get(Question, "soil-question-00")
        question.question_type = question_type
        question.options = [{"label": "A", "text": "甲"}, {"label": "B", "text": "乙"}] if "选择" in question_type else []
        question.answer_word_limit = 3 if question_type in {"简答题", "计算题"} else None
        session.commit()
    practice = _practice(client, count=13)
    practice_question = next(item for item in practice["questions"] if item["id"] == "soil-question-00")
    practice_url = f"/api/student/practice-sessions/{practice['id']}/answers/{practice_question['id']}"
    rejected = client.put(practice_url, json={"answer": invalid}, headers=CSRF)
    assert rejected.status_code == 422
    assert rejected.json()["success"] is False
    assert client.put(practice_url, json={"answer": valid}, headers=CSRF).status_code == 200
    assignment_id = _assignment(database)
    with database.session() as session:
        row = session.scalar(select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment_id))
        row.question_snapshot = {**row.question_snapshot, "questionType": question_type, "options": [{"label": "A", "text": "甲"}, {"label": "B", "text": "乙"}] if "选择" in question_type else [], "answerWordLimit": 3 if question_type in {"简答题", "计算题"} else None}
        session.commit()
    formal = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    formal_url = f"/api/student/submissions/{formal['submissionId']}/answers/{formal['questions'][0]['id']}"
    assert client.put(formal_url, json={"answer": invalid}, headers=CSRF).status_code == 422
    assert client.put(formal_url, json={"answer": valid}, headers=CSRF).status_code == 200


def test_allowed_resubmission_uses_latest_graded_attempt_for_average(assessment_context) -> None:
    from server.application.models import Student

    client, database = assessment_context
    assignment_id = _assignment(database, allow_resubmit=True)
    first = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    client.put(f"/api/student/submissions/{first['submissionId']}/answers/{first['questions'][0]['id']}", json={"answer": "A"}, headers=CSRF)
    assert client.post(f"/api/student/submissions/{first['submissionId']}/submit", headers=CSRF).json()["data"]["score"] == 10
    second = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]
    assert second["attemptNumber"] == 2
    client.put(f"/api/student/submissions/{second['submissionId']}/answers/{second['questions'][0]['id']}", json={"answer": "B"}, headers=CSRF)
    assert client.post(f"/api/student/submissions/{second['submissionId']}/submit", headers=CSRF).json()["data"]["score"] == 0
    assert client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).status_code == 409
    with database.session() as session:
        assert session.get(Student, "student-profile").average_score == 0


def test_formal_routes_enforce_exact_start_due_duration_and_after_close_boundaries(
    assessment_context, monkeypatch
) -> None:
    import server.application.api.student_assessment as assessment_api

    client, database = assessment_context
    base = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)

    starts_at = base
    due_at = base + timedelta(hours=2)
    assignment_id = _assignment(database, starts_at=starts_at, due_at=due_at)
    monkeypatch.setattr(assessment_api, "now", lambda: base - timedelta(microseconds=1))
    before = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF)
    assert before.status_code == 409
    assert before.json()["code"] == "ASSIGNMENT_NOT_OPEN"

    monkeypatch.setattr(assessment_api, "now", lambda: base)
    started = client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF)
    assert started.status_code == 200
    submission_id = started.json()["data"]["submissionId"]
    question_id = started.json()["data"]["questions"][0]["id"]

    monkeypatch.setattr(
        assessment_api,
        "now",
        lambda: base + timedelta(minutes=30) - timedelta(microseconds=1),
    )
    just_before_duration = client.put(
        f"/api/student/submissions/{submission_id}/answers/{question_id}",
        json={"answer": "A"},
        headers=CSRF,
    )
    assert just_before_duration.status_code == 200

    monkeypatch.setattr(assessment_api, "now", lambda: base + timedelta(minutes=30))
    at_duration = client.put(
        f"/api/student/submissions/{submission_id}/answers/{question_id}",
        json={"answer": "B"},
        headers=CSRF,
    )
    assert at_duration.status_code == 409
    assert at_duration.json()["code"] == "ASSIGNMENT_CLOSED"

    closed_assignment = _assignment(
        database,
        due_at=base + timedelta(hours=1),
        show_answers_mode="after_close",
    )
    monkeypatch.setattr(assessment_api, "now", lambda: base)
    closed_started = client.post(
        f"/api/student/assignments/{closed_assignment}/start", headers=CSRF
    ).json()["data"]
    client.put(
        f"/api/student/submissions/{closed_started['submissionId']}/answers/{closed_started['questions'][0]['id']}",
        json={"answer": "A"},
        headers=CSRF,
    )
    client.post(
        f"/api/student/submissions/{closed_started['submissionId']}/submit", headers=CSRF
    )
    monkeypatch.setattr(
        assessment_api,
        "now",
        lambda: base + timedelta(hours=1) - timedelta(microseconds=1),
    )
    before_due = client.get(
        f"/api/student/submissions/{closed_started['submissionId']}/result"
    )
    assert before_due.json()["data"]["showAnswers"] is False
    monkeypatch.setattr(assessment_api, "now", lambda: base + timedelta(hours=1))
    at_due = client.get(
        f"/api/student/submissions/{closed_started['submissionId']}/result"
    )
    assert at_due.json()["data"]["showAnswers"] is True

    monkeypatch.setattr(assessment_api, "now", lambda: base)
    due_now_assignment = _assignment(database, due_at=base)
    due_now = client.post(
        f"/api/student/assignments/{due_now_assignment}/start", headers=CSRF
    )
    assert due_now.status_code == 409
    assert due_now.json()["code"] == "ASSIGNMENT_CLOSED"


def test_unknown_and_foreign_question_routes_keep_not_found_error_envelope(
    assessment_context,
) -> None:
    client, database = assessment_context

    def assert_not_found(response, code):
        assert response.status_code == 404
        body = response.json()
        assert set(body) == {"success", "message", "code", "requestId"}
        assert body["success"] is False
        assert body["code"] == code

    assert_not_found(
        client.get("/api/student/practice-sessions/missing-session"),
        "PRACTICE_SESSION_NOT_FOUND",
    )
    assert_not_found(
        client.post("/api/student/practice-sessions/missing-session/submit", headers=CSRF),
        "PRACTICE_SESSION_NOT_FOUND",
    )
    practice = _practice(client)
    assert_not_found(
        client.put(
            f"/api/student/practice-sessions/{practice['id']}/answers/other-question",
            json={"answer": "A"},
            headers=CSRF,
        ),
        "PRACTICE_QUESTION_NOT_FOUND",
    )

    assert_not_found(
        client.post("/api/student/assignments/missing-assignment/start", headers=CSRF),
        "ASSIGNMENT_NOT_FOUND",
    )
    assignment_id = _assignment(database)
    started = client.post(
        f"/api/student/assignments/{assignment_id}/start", headers=CSRF
    ).json()["data"]
    submission_id = started["submissionId"]
    assert_not_found(
        client.put(
            f"/api/student/submissions/{submission_id}/answers/other-question",
            json={"answer": "A"},
            headers=CSRF,
        ),
        "SUBMISSION_QUESTION_NOT_FOUND",
    )
    for verb, path in (
        ("put", "/api/student/submissions/missing-submission/answers/soil-question-00"),
        ("post", "/api/student/submissions/missing-submission/submit"),
        ("get", "/api/student/submissions/missing-submission/result"),
    ):
        if verb == "put":
            response = client.put(path, json={"answer": "A"}, headers=CSRF)
        elif verb == "post":
            response = client.post(path, headers=CSRF)
        else:
            response = client.get(path)
        assert_not_found(response, "SUBMISSION_NOT_FOUND")
