from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import time_ns

import pytest
from fastapi.testclient import TestClient
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


def _assignment(database, *, due_at=None, starts_at=None, show_answers_mode="after_submission", allow_resubmit=False, subjective=False, student_id="student-profile"):
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
            show_answers_mode=show_answers_mode, allow_resubmit=allow_resubmit, auto_grade=True, status="published",
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
    assert client.post(f"/api/student/assignments/{assignment_id}/start", headers=CSRF).json()["data"]["submissionId"] == submission_id
    inaccessible_id = _assignment(database, student_id="other-student")
    inaccessible = client.post(f"/api/student/assignments/{inaccessible_id}/start", headers=CSRF)
    assert inaccessible.status_code == 404
    assert client.post(f"/api/student/submissions/{submission_id}/submit", headers=CSRF).status_code == 200
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
    from server.application.migrations import upgrade_database

    database_url = f"sqlite:///{tmp_path / 'assessment-migration.db'}"
    upgrade_database(database_url, "006_papers_and_snapshots")
    database = create_database(database_url)
    with database.engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, username, password_hash, password_algorithm, role, role_label, name, status, college, school, must_change_password, created_at, updated_at) VALUES ('migration-user', 'migration-user', 'hash', 'argon2', 'student', '学生', '迁移学生', 'active', '学院', '学校', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        connection.execute(text("INSERT INTO students (id, user_id, student_no, progress, average_score, created_at) VALUES ('migration-student', 'migration-user', 'MS1', 0, 0, CURRENT_TIMESTAMP)"))
    upgrade_database(database_url)
    with database.engine.connect() as connection:
        assert connection.execute(text("SELECT student_no FROM students WHERE id = 'migration-student'")).scalar_one() == "MS1"
        assert {"practice_sessions", "practice_session_questions"}.issubset(set(connection.dialect.get_table_names(connection)))
