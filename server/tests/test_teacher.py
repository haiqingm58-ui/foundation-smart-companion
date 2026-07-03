from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture()
def teacher_context(database_url: str, tmp_path: Path):
    from server.application.config import Settings
    from server.application.database import create_database
    from server.application.main import create_app
    from server.application.migrations import upgrade_database
    from server.application.models import ClassRoom, SessionToken, Student, Teacher, TeacherStudentBinding, User
    from server.application.security import hash_password, token_digest

    upgrade_database(database_url)
    database = create_database(database_url)
    settings = Settings(
        database_url=database_url, secret_key="test-secret", data_dir=tmp_path, upload_dir=tmp_path / "uploads",
        session_ttl_seconds=3600, captcha_ttl_seconds=120, cookie_secure=False, cookie_path="/",
        llm_api_url="", llm_api_key="", llm_model="test",
    )
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    password = hash_password("Teacher-123")
    with database.session() as session:
        users = [
            User(id="teacher-user-1", username="teacher1", password_hash=password, password_algorithm="argon2", role="teacher", role_label="指导老师", name="教师一", student_no="T1", college="土木工程学院", school="湖南大学", status="active"),
            User(id="teacher-user-2", username="teacher2", password_hash=password, password_algorithm="argon2", role="teacher", role_label="指导老师", name="教师二", student_no="T2", college="土木工程学院", school="湖南大学", status="active"),
            User(id="student-user-1", username="student1", password_hash=password, password_algorithm="argon2", role="student", role_label="学生", name="学生一", student_no="S1", college="土木工程学院", school="湖南大学", status="active"),
            User(id="student-user-2", username="student2", password_hash=password, password_algorithm="argon2", role="student", role_label="学生", name="学生二", student_no="S2", college="土木工程学院", school="湖南大学", status="active"),
        ]
        session.add_all(users)
        session.flush()
        classroom = ClassRoom(id="class-1", name="土木工程2401班", grade="2024", major="土木工程", college="土木工程学院")
        teachers = [
            Teacher(id="teacher-1", user_id="teacher-user-1", teacher_no="T1", college="土木工程学院"),
            Teacher(id="teacher-2", user_id="teacher-user-2", teacher_no="T2", college="土木工程学院"),
        ]
        students = [
            Student(id="student-1", user_id="student-user-1", student_no="S1", class_id="class-1", progress=45, average_score=82),
            Student(id="student-2", user_id="student-user-2", student_no="S2", class_id="class-1", progress=20, average_score=66),
        ]
        session.add(classroom)
        session.add_all(teachers)
        session.add_all(students)
        session.flush()
        session.add_all(
            [
                TeacherStudentBinding(id="binding-1", teacher_id="teacher-1", student_id="student-1", class_id="class-1", status="active", created_by="teacher-user-1"),
                TeacherStudentBinding(id="binding-2", teacher_id="teacher-2", student_id="student-2", class_id="class-1", status="active", created_by="teacher-user-2"),
                SessionToken(id="teacher-session", user_id="teacher-user-1", token_hash=token_digest("teacher-token"), csrf_hash=token_digest("teacher-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)),
            ]
        )
        session.commit()
    app = create_app(settings=settings, database=database)
    client = TestClient(app)
    client.cookies.set("foundation_session", "teacher-token")
    client.cookies.set("foundation_csrf", "teacher-csrf")
    return client, database, settings


def test_teacher_only_sees_bound_students(teacher_context) -> None:
    client, _database, _settings = teacher_context
    response = client.get("/api/teacher/students?page=1&pageSize=20")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["studentNo"] for item in items] == ["S1"]
    assert client.get("/api/teacher/students/student-2").status_code == 404


def test_teacher_uploads_real_markdown_resource(teacher_context) -> None:
    from server.application.models import KnowledgeChunk, Resource

    client, database, settings = teacher_context
    response = client.post(
        "/api/teacher/resources",
        data={"chapter": "第3章 桩基础", "knowledgePoint": "桩侧阻力", "visibility": "class"},
        files={"file": ("pile-notes.md", b"# Pile\nThe pile side resistance transfers load.", "text/markdown")},
        headers={"X-CSRF-Token": "teacher-csrf"},
    )
    assert response.status_code == 200
    resource_id = response.json()["data"]["id"]
    with database.session() as session:
        resource = session.get(Resource, resource_id)
        assert Path(resource.storage_path).is_file()
        assert Path(resource.storage_path).resolve().is_relative_to(settings.upload_dir.resolve())
        assert session.scalar(select(KnowledgeChunk).where(KnowledgeChunk.resource_id == resource_id)) is not None


def test_teacher_manages_question_and_assignment_for_own_student(teacher_context) -> None:
    client, _database, _settings = teacher_context
    question = client.post(
        "/api/teacher/questions",
        json={"text": "桩侧阻力主要受哪些因素影响？", "questionType": "简答题", "difficulty": "基础", "points": 10, "chapter": "第3章 桩基础", "knowledgePoint": "桩侧阻力", "options": [], "correctAnswer": "土性与相对位移", "explanation": "考查荷载传递"},
        headers={"X-CSRF-Token": "teacher-csrf"},
    )
    assert question.status_code == 200
    question_id = question.json()["data"]["id"]
    assignment = client.post(
        "/api/teacher/assignments",
        json={"title": "桩基础练习", "description": "完成简答题", "studentIds": ["student-1"], "questionIds": [question_id], "totalPoints": 10, "allowResubmit": False, "autoGrade": False, "status": "published"},
        headers={"X-CSRF-Token": "teacher-csrf"},
    )
    assert assignment.status_code == 200
    forbidden_target = client.post(
        "/api/teacher/assignments",
        json={"title": "越权作业", "studentIds": ["student-2"], "questionIds": [question_id], "totalPoints": 10, "status": "published"},
        headers={"X-CSRF-Token": "teacher-csrf"},
    )
    assert forbidden_target.status_code == 403


def test_teacher_dashboard_uses_real_owned_data(teacher_context) -> None:
    client, _database, _settings = teacher_context
    response = client.get("/api/teacher/dashboard")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["studentTotal"] == 1
    assert data["averageScore"] == 82
