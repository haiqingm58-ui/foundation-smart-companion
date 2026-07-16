from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from server.application.database import create_database
from server.application.migrations import upgrade_database
from server.application.models import (
    ClassRoom,
    KnowledgePoint,
    Question,
    SessionToken,
    Student,
    Teacher,
    TeacherStudentBinding,
    User,
)
from server.application.security import hash_password, token_digest
from server.application.services.question_bank_import import import_question_bank


E2E_ROOT = ROOT / "output" / "e2e"
DATABASE_PATH = E2E_ROOT / "e2e.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
MANIFEST_PATH = ROOT / "content" / "question-banks" / "soil-mechanics" / "manifest.json"


def reset_database() -> None:
    E2E_ROOT.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{DATABASE_PATH}{suffix}")
        if path.exists():
            path.unlink()


def seed_accounts(database) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    password_hash = hash_password("E2e-Only-123")
    with database.session() as session:
        session.add_all(
            [
                User(
                    id="e2e-teacher-user",
                    username="e2e-teacher",
                    password_hash=password_hash,
                    password_algorithm="argon2",
                    role="teacher",
                    role_label="指导老师",
                    name="端到端教师",
                    status="active",
                    college="土木工程学院",
                    school="湖南大学",
                    must_change_password=False,
                ),
                User(
                    id="e2e-student-user",
                    username="e2e-student",
                    password_hash=password_hash,
                    password_algorithm="argon2",
                    role="student",
                    role_label="学生",
                    name="端到端学生",
                    student_no="E2E2026001",
                    college="土木工程学院",
                    school="湖南大学",
                    mentor="端到端教师",
                    status="active",
                    must_change_password=False,
                ),
                ClassRoom(
                    id="e2e-class",
                    name="基础工程演示班",
                    grade="2026级",
                    major="土木工程",
                    college="土木工程学院",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                Teacher(
                    id="e2e-teacher",
                    user_id="e2e-teacher-user",
                    teacher_no="E2ET001",
                    college="土木工程学院",
                    course="土力学、基础工程",
                ),
                Student(
                    id="e2e-student",
                    user_id="e2e-student-user",
                    student_no="E2E2026001",
                    class_id="e2e-class",
                    progress=0,
                    average_score=0,
                ),
                SessionToken(
                    id="e2e-teacher-session",
                    user_id="e2e-teacher-user",
                    token_hash=token_digest("e2e-teacher-token"),
                    csrf_hash=token_digest("e2e-teacher-csrf"),
                    expires_at=expires_at,
                ),
                SessionToken(
                    id="e2e-student-session",
                    user_id="e2e-student-user",
                    token_hash=token_digest("e2e-student-token"),
                    csrf_hash=token_digest("e2e-student-csrf"),
                    expires_at=expires_at,
                ),
            ]
        )
        session.flush()
        session.add(
            TeacherStudentBinding(
                id="e2e-binding",
                teacher_id="e2e-teacher",
                student_id="e2e-student",
                class_id="e2e-class",
                status="active",
                created_by="e2e-teacher-user",
            )
        )
        session.commit()


def main() -> None:
    reset_database()
    os.environ["FOUNDATION_DATABASE_URL"] = DATABASE_URL
    upgrade_database(DATABASE_URL)
    database = create_database(DATABASE_URL)
    imported = import_question_bank(database, MANIFEST_PATH, None)
    seed_accounts(database)
    with database.session() as session:
        counts = {
            "questions": session.scalar(select(func.count(Question.id))) or 0,
            "knowledgePoints": session.scalar(select(func.count(KnowledgePoint.id))) or 0,
            "users": session.scalar(select(func.count(User.id))) or 0,
        }
    print(json.dumps({"import": imported.to_dict(), "fixtures": counts}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
