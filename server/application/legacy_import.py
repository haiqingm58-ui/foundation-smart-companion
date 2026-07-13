from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from .database import Database
from .models import (
    KnowledgePoint,
    LegacyDocument,
    LegacyExercise,
    Question,
    QuestionKnowledgePoint,
    Resource,
    Setting,
    Student,
    Subject,
    Teacher,
    User,
)


FOUNDATION_SUBJECT_ID = "foundation-engineering"


def normalize_knowledge_point_name(value: str) -> str:
    return " ".join(value.split())


def knowledge_point_id(subject_id: str, normalized_name: str) -> str:
    digest = sha256(f"{subject_id}:{normalized_name}".encode("utf-8")).hexdigest()
    return f"knowledge-point-{digest}"


def question_knowledge_point_id(question_id: str, knowledge_point_id: str) -> str:
    digest = sha256(f"{question_id}:{knowledge_point_id}".encode("utf-8")).hexdigest()
    return f"question-knowledge-point-{digest}"


def ensure_foundation_subject(session) -> Subject:
    subject = session.get(Subject, FOUNDATION_SUBJECT_ID)
    if subject is None:
        subject = Subject(
            id=FOUNDATION_SUBJECT_ID,
            title="基础工程",
            slug=FOUNDATION_SUBJECT_ID,
            status="active",
            sort_order=0,
        )
        session.add(subject)
        session.flush()
    return subject


def add_legacy_question_knowledge_point(session, question: Question) -> None:
    if not question.knowledge_point:
        return
    name = question.knowledge_point.strip()
    normalized_name = normalize_knowledge_point_name(name)
    if not normalized_name:
        return
    knowledge_point = session.scalar(
        select(KnowledgePoint).where(
            KnowledgePoint.subject_id == question.subject_id,
            KnowledgePoint.normalized_name == normalized_name,
        )
    )
    if knowledge_point is None:
        knowledge_point = KnowledgePoint(
            id=knowledge_point_id(question.subject_id, normalized_name),
            subject_id=question.subject_id,
            chapter=question.chapter or "",
            name=name,
            normalized_name=normalized_name,
        )
        session.add(knowledge_point)
        session.flush()
    link_id = question_knowledge_point_id(question.id, knowledge_point.id)
    if session.get(QuestionKnowledgePoint, link_id) is None:
        session.add(
            QuestionKnowledgePoint(
                id=link_id,
                question_id=question.id,
                knowledge_point_id=knowledge_point.id,
            )
        )


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def import_legacy_sqlite(path: Path, database: Database) -> dict[str, int]:
    source = sqlite3.connect(path)
    source.row_factory = sqlite3.Row
    counts = {"users": 0, "resources": 0, "questions": 0, "settings": 0}
    try:
        with database.session() as session:
            foundation_subject = ensure_foundation_subject(session)
            for row in source.execute("SELECT * FROM users"):
                if session.get(User, row["id"]):
                    continue
                user = User(
                    id=row["id"],
                    username=row["username"],
                    password_hash=row["password_hash"],
                    password_salt=row["password_salt"],
                    password_algorithm="pbkdf2_sha256",
                    role=row["role"],
                    role_label=row["role_label"],
                    name=row["name"],
                    status="active",
                    student_no=row["student_no"],
                    college=row["college"],
                    school=row["school"],
                    mentor=row["mentor"],
                    must_change_password=True,
                    created_at=parse_datetime(row["created_at"]),
                    updated_at=parse_datetime(row["created_at"]),
                )
                session.add(user)
                session.flush()
                if user.role == "student":
                    session.add(Student(id=f"profile-{user.id}", user_id=user.id, student_no=user.student_no or user.username))
                elif user.role == "teacher":
                    session.add(
                        Teacher(
                            id=f"profile-{user.id}",
                            user_id=user.id,
                            teacher_no=user.student_no or user.username,
                            college=user.college,
                        )
                    )
                counts["users"] += 1

            fallback_user = session.scalar(select(User).order_by(User.created_at))
            for row in source.execute("SELECT * FROM documents"):
                if session.get(LegacyDocument, row["id"]):
                    continue
                uploaded_at = parse_datetime(row["uploaded_at"])
                uploader = session.get(User, row["uploaded_by"]) or fallback_user
                if uploader is None:
                    continue
                session.add(
                    LegacyDocument(
                        id=row["id"], title=row["title"], text=row["text"], source_type=row["source_type"],
                        uploaded_by=row["uploaded_by"], uploaded_at=uploaded_at,
                    )
                )
                session.add(
                    Resource(
                        id=f"resource-{row['id']}", name=row["title"], title=row["title"],
                        storage_path=f"legacy-db://documents/{row['id']}", file_size=len(row["text"].encode("utf-8")),
                        mime_type="text/plain", source_type=row["source_type"], uploaded_by=uploader.id,
                        visibility="school", extracted_text=row["text"], created_at=uploaded_at, updated_at=uploaded_at,
                    )
                )
                counts["resources"] += 1

            for row in source.execute("SELECT * FROM exercises"):
                if session.get(LegacyExercise, row["id"]):
                    continue
                payload = json.loads(row["payload"])
                created_at = parse_datetime(row["created_at"])
                session.add(
                    LegacyExercise(
                        id=row["id"], payload=row["payload"], source=row["source"],
                        created_by=row["created_by"], created_at=created_at,
                    )
                )
                question = Question(
                        id=row["id"], text=payload.get("text") or payload.get("title") or "未命名题目",
                        question_type=payload.get("type") or "简答题", options=payload.get("options") or [],
                        correct_answer=payload.get("answer"), explanation=payload.get("explanation"),
                        rubric=payload.get("rubric") or [], difficulty=payload.get("difficulty") or "基础",
                        points=float(payload.get("points") or 10), chapter=payload.get("chapter"),
                        knowledge_point=(payload.get("tags") or [None])[0], source=row["source"],
                        subject_id=foundation_subject.id, created_by=None, created_at=created_at, updated_at=created_at,
                    )
                session.add(question)
                session.flush()
                add_legacy_question_knowledge_point(session, question)
                counts["questions"] += 1

            for row in source.execute("SELECT * FROM settings"):
                if session.get(Setting, row["key"]):
                    continue
                session.add(Setting(key=row["key"], value=row["value"], updated_at=parse_datetime(row["updated_at"])))
                counts["settings"] += 1
            session.commit()
    finally:
        source.close()
    return counts
