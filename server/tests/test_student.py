from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture()
def student_context(database_url: str, tmp_path: Path):
    from server.application.config import Settings
    from server.application.database import create_database
    from server.application.main import create_app
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgeChunk, Question, SessionToken, Student, User
    from server.application.security import hash_password, token_digest

    upgrade_database(database_url)
    database = create_database(database_url)
    settings = Settings(
        database_url=database_url, secret_key="test-secret", data_dir=tmp_path, upload_dir=tmp_path / "uploads",
        session_ttl_seconds=3600, captcha_ttl_seconds=120, cookie_secure=False, cookie_path="/",
        llm_api_url="", llm_api_key="", llm_model="test",
    )
    with database.session() as session:
        user = User(
            id="student-user", username="student", password_hash=hash_password("Student-123"),
            password_algorithm="argon2", role="student", role_label="学生", name="张同学",
            student_no="20260001", college="土木工程学院", school="湖南大学", mentor="李老师", status="active",
        )
        session.add(user)
        session.flush()
        session.add_all(
            [
                Student(id="student-profile", user_id=user.id, student_no="20260001", progress=0, average_score=0),
                SessionToken(id="student-session", user_id=user.id, token_hash=token_digest("student-token"), csrf_hash=token_digest("student-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1)),
                Question(id="question-choice", text="桩侧阻力属于哪类阻力？", question_type="单项选择题", options=[{"label": "A", "text": "桩土界面阻力"}, {"label": "B", "text": "空气阻力"}], correct_answer="A", explanation="桩侧阻力来源于桩土界面。", difficulty="基础", points=10, chapter="第3章 桩基础", knowledge_point="桩侧阻力", source="textbook"),
                KnowledgeChunk(id="chunk-test", source_type="textbook", heading="第3章 桩基础 > 桩侧阻力", text="桩侧阻力由桩土界面的剪切作用发挥，并随桩土相对位移逐步发展。", chapter="第3章 桩基础", sequence=1),
            ]
        )
        session.commit()
    app = create_app(settings=settings, database=database)
    client = TestClient(app)
    client.cookies.set("foundation_session", "student-token")
    client.cookies.set("foundation_csrf", "student-csrf")
    return client, database


def test_student_progress_attempt_and_report_are_persisted(student_context) -> None:
    from server.application.models import LearningProgress, PracticeAttempt

    client, database = student_context
    progress = client.put(
        "/api/student/progress/chapter-03",
        json={"percent": 60, "lastSection": "3.4 单桩竖向承载力"},
        headers={"X-CSRF-Token": "student-csrf"},
    )
    assert progress.status_code == 200
    attempt = client.post(
        "/api/student/exercises/question-choice/attempts",
        json={"answer": "A"},
        headers={"X-CSRF-Token": "student-csrf"},
    )
    assert attempt.status_code == 200
    assert attempt.json()["data"]["score"] == 10
    report = client.get("/api/student/report")
    assert report.status_code == 200
    assert report.json()["data"]["averageScore"] == 100
    with database.session() as session:
        assert session.scalar(select(LearningProgress).where(LearningProgress.chapter_id == "chapter-03")).percent == 60
        assert session.scalar(select(PracticeAttempt).where(PracticeAttempt.question_id == "question-choice")) is not None


def test_student_dashboard_and_exercise_bank_use_database(student_context) -> None:
    client, _database = student_context
    dashboard = client.get("/api/student/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["student"]["name"] == "张同学"
    exercises = client.get("/api/student/exercises?chapter=第3章%20桩基础")
    assert exercises.status_code == 200
    assert exercises.json()["data"]["total"] == 1


def test_rag_returns_ranked_citation_without_llm(student_context) -> None:
    client, _database = student_context
    response = client.post(
        "/api/qa",
        json={"question": "桩侧阻力如何发挥？", "mode": "教材问答", "useLlm": True},
        headers={"X-CSRF-Token": "student-csrf"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["usedLlm"] is False
    assert "桩侧阻力" in data["sources"][0]["heading"]
    assert "桩侧阻力" in data["answer"]
