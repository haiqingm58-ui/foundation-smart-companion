from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.fixture()
def admin_context(database_url: str, tmp_path: Path):
    from server.application.config import Settings
    from server.application.database import create_database
    from server.application.main import create_app
    from server.application.migrations import upgrade_database
    from server.application.models import SessionToken, User
    from server.application.security import hash_password, token_digest

    upgrade_database(database_url)
    database = create_database(database_url)
    settings = Settings(
        database_url=database_url, secret_key="test-secret", data_dir=tmp_path, upload_dir=tmp_path / "uploads",
        session_ttl_seconds=3600, captcha_ttl_seconds=120, cookie_secure=False, cookie_path="/",
        llm_api_url="", llm_api_key="", llm_model="test",
    )
    with database.session() as session:
        session.add_all(
            [
                User(
                    id="admin-test", username="admin-test", password_hash=hash_password("Admin-123"),
                    password_algorithm="argon2", role="admin", role_label="管理员", name="测试管理员",
                    student_no="ADMIN-TEST", college="土木工程学院", school="湖南大学", status="active",
                ),
                User(
                    id="student-existing", username="20260099", password_hash=hash_password("Student-123"),
                    password_algorithm="argon2", role="student", role_label="学生", name="已有学生",
                    student_no="20260099", college="土木工程学院", school="湖南大学", status="active",
                ),
            ]
        )
        session.flush()
        session.add(
            SessionToken(
                id="session-admin", user_id="admin-test", token_hash=token_digest("admin-session"),
                csrf_hash=token_digest("admin-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.commit()
    app = create_app(settings=settings, database=database)
    client = TestClient(app)
    client.cookies.set("foundation_session", "admin-session")
    client.cookies.set("foundation_csrf", "admin-csrf")
    return client, database


def wizard_payload(student_no: str = "20260001") -> dict:
    return {
        "teacher": {
            "name": "张老师", "teacherNo": "T2026001", "username": "teacher-zhang",
            "password": "Teacher-123", "college": "土木工程学院", "course": "基础工程", "status": "active",
        },
        "classInfo": {"name": "土木工程2401班", "grade": "2024", "major": "土木工程", "college": "土木工程学院"},
        "students": [
            {"name": "王同学", "studentNo": student_no, "username": student_no, "password": "Student-123", "className": "土木工程2401班"},
        ],
    }


def test_admin_creates_teacher_students_class_and_bindings_atomically(admin_context) -> None:
    from server.application.models import ClassRoom, OperationLog, Student, Teacher, TeacherStudentBinding, User

    client, database = admin_context
    response = client.post("/api/admin/teachers-with-students", json=wizard_payload(), headers={"X-CSRF-Token": "admin-csrf"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["teacherCreated"] is True
    assert data["studentSuccess"] == 1
    assert data["bindingSuccess"] == 1
    with database.session() as session:
        assert session.scalar(select(User).where(User.username == "teacher-zhang")) is not None
        assert session.scalar(select(Teacher).where(Teacher.teacher_no == "T2026001")) is not None
        assert session.scalar(select(Student).where(Student.student_no == "20260001")) is not None
        assert session.scalar(select(ClassRoom).where(ClassRoom.name == "土木工程2401班")) is not None
        assert session.scalar(select(func.count(TeacherStudentBinding.id))) == 1
        assert session.scalar(select(func.count(OperationLog.id))) == 1


def test_duplicate_student_rolls_back_entire_wizard_transaction(admin_context) -> None:
    from server.application.models import Teacher, User

    client, database = admin_context
    response = client.post(
        "/api/admin/teachers-with-students",
        json=wizard_payload(student_no="20260099"),
        headers={"X-CSRF-Token": "admin-csrf"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "IMPORT_CONFLICT"
    with database.session() as session:
        assert session.scalar(select(User).where(User.username == "teacher-zhang")) is None
        assert session.scalar(select(Teacher).where(Teacher.teacher_no == "T2026001")) is None


def test_import_rejects_spreadsheet_formulas() -> None:
    from server.application.services.imports import parse_pasted_students

    result = parse_pasted_students("姓名\t学号\t班级\n王同学\t=1+1\t土木工程2401班")
    assert result["valid"] == []
    assert result["errors"][0]["code"] == "FORMULA_NOT_ALLOWED"


def test_admin_dashboard_and_lists_return_real_counts(admin_context) -> None:
    client, _database = admin_context
    dashboard = client.get("/api/admin/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["studentTotal"] == 1
    assert client.get("/api/admin/teachers?page=1&pageSize=20").status_code == 200
    students = client.get("/api/admin/students?page=1&pageSize=20")
    assert students.status_code == 200
    assert students.json()["data"]["items"][0]["profileId"] is None


def test_admin_disables_account_and_resets_password(admin_context) -> None:
    from server.application.models import SessionToken, User
    from server.application.security import verify_password

    client, database = admin_context
    disabled = client.patch(
        "/api/admin/accounts/student-existing/status",
        json={"status": "disabled"},
        headers={"X-CSRF-Token": "admin-csrf"},
    )
    assert disabled.status_code == 200
    reset = client.post(
        "/api/admin/accounts/student-existing/reset-password",
        json={"password": "Fresh-Student-123"},
        headers={"X-CSRF-Token": "admin-csrf"},
    )
    assert reset.status_code == 200
    with database.session() as session:
        user = session.get(User, "student-existing")
        assert user.status == "disabled"
        assert user.must_change_password is True
        assert verify_password("Fresh-Student-123", user.password_hash, user.password_algorithm)[0]
        assert session.scalar(select(func.count(SessionToken.id)).where(SessionToken.user_id == user.id)) == 0


def test_admin_previews_student_file_without_writing_database(admin_context) -> None:
    from server.application.models import Student

    client, database = admin_context
    response = client.post(
        "/api/admin/import/preview",
        files={"file": ("students.csv", "姓名,学号,班级\n李同学,20260002,土木工程2401班\n".encode("utf-8"), "text/csv")},
        headers={"X-CSRF-Token": "admin-csrf"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["valid"][0]["studentNo"] == "20260002"
    with database.session() as session:
        assert session.scalar(select(func.count(Student.id))) == 0
