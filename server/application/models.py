from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, event
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


REVIEW_REQUIRED_STATUS = "review_required"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_salt: Mapped[str | None] = mapped_column(String(128))
    password_algorithm: Mapped[str] = mapped_column(String(32), default="argon2", nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    role_label: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    student_no: Mapped[str | None] = mapped_column(String(64))
    college: Mapped[str] = mapped_column(String(120), default="土木工程学院", nullable=False)
    school: Mapped[str] = mapped_column(String(120), default="湖南大学", nullable=False)
    mentor: Mapped[str | None] = mapped_column(String(80))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    teacher_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    college: Mapped[str] = mapped_column(String(120), nullable=False)
    course: Mapped[str] = mapped_column(String(120), default="基础工程", nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ClassRoom(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(32))
    major: Mapped[str] = mapped_column(String(120), default="土木工程", nullable=False)
    college: Mapped[str] = mapped_column(String(120), default="土木工程学院", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    student_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    class_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id", ondelete="SET NULL"), index=True)
    progress: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    average_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    last_study_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TeacherStudentBinding(Base):
    __tablename__ = "teacher_student_bindings"
    __table_args__ = (UniqueConstraint("teacher_id", "student_id", "class_id", name="uq_teacher_student_class"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SessionToken(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CaptchaRecord(Base):
    __tablename__ = "captcha_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    answer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    client_ip: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    client_ip: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class LegacyDocument(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LegacyExercise(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    chapter: Mapped[str | None] = mapped_column(String(120), index=True)
    knowledge_point: Mapped[str | None] = mapped_column(String(160), index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="private", nullable=False)
    class_scope: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    heading: Mapped[str] = mapped_column(String(300), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    chapter: Mapped[str | None] = mapped_column(String(120), index=True)
    page: Mapped[int | None] = mapped_column(Integer)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    knowledge_points: Mapped[list[KnowledgePoint]] = relationship(back_populates="subject")
    questions: Mapped[list[Question]] = relationship(back_populates="subject")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (UniqueConstraint("subject_id", "normalized_name", name="uq_subject_knowledge_name"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    subject: Mapped[Subject] = relationship(back_populates="knowledge_points")
    question_links: Mapped[list[QuestionKnowledgePoint]] = relationship(back_populates="knowledge_point")
    questions = association_proxy("question_links", "question")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    correct_answer: Mapped[Any | None] = mapped_column(JSON)
    explanation: Mapped[str | None] = mapped_column(Text)
    rubric: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(24), default="基础", nullable=False, index=True)
    points: Mapped[float] = mapped_column(Float, default=10, nullable=False)
    chapter: Mapped[str | None] = mapped_column(String(120), index=True)
    knowledge_point: Mapped[str | None] = mapped_column(String(160), index=True)
    subject_id: Mapped[str | None] = mapped_column(ForeignKey("subjects.id"), index=True)
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    answer_word_limit: Mapped[int | None] = mapped_column(Integer)
    grading_mode: Mapped[str] = mapped_column(String(24), default="auto", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=REVIEW_REQUIRED_STATUS, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_fingerprint: Mapped[str | None] = mapped_column(String(96), index=True)
    source: Mapped[str] = mapped_column(String(32), default="teacher", nullable=False)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    subject: Mapped[Subject | None] = relationship(back_populates="questions")
    knowledge_point_links: Mapped[list[QuestionKnowledgePoint]] = relationship(back_populates="question", cascade="all, delete-orphan")
    knowledge_points = association_proxy("knowledge_point_links", "knowledge_point")


class QuestionKnowledgePoint(Base):
    __tablename__ = "question_knowledge_points"
    __table_args__ = (UniqueConstraint("question_id", "knowledge_point_id", name="uq_question_knowledge_point"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_point_id: Mapped[str] = mapped_column(ForeignKey("knowledge_points.id", ondelete="RESTRICT"), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    question: Mapped[Question] = relationship(back_populates="knowledge_point_links")
    knowledge_point: Mapped[KnowledgePoint] = relationship(back_populates="question_links")


def question_can_be_active(session: Session, question: Question) -> bool:
    links = list(question.knowledge_point_links)
    for candidate in session.new.union(session.dirty):
        if (
            isinstance(candidate, QuestionKnowledgePoint)
            and candidate not in links
            and (candidate.question is question or candidate.question_id == question.id)
        ):
            links.append(candidate)
    links = [link for link in links if link not in session.deleted]
    if not question.subject_id or not 1 <= len(links) <= 3:
        return False
    for link in links:
        knowledge_point = link.knowledge_point
        if knowledge_point is None and link.knowledge_point_id:
            knowledge_point = session.get(KnowledgePoint, link.knowledge_point_id)
        if knowledge_point is None or knowledge_point.subject_id != question.subject_id:
            return False
    return True


@event.listens_for(Session, "before_flush")
def mark_incomplete_active_questions_for_review(session: Session, flush_context, instances) -> None:
    questions = {item for item in session.new.union(session.dirty) if isinstance(item, Question)}
    for item in session.new.union(session.dirty).union(session.deleted):
        if isinstance(item, QuestionKnowledgePoint):
            question = item.question or session.get(Question, item.question_id)
            if question is not None:
                questions.add(question)
        elif isinstance(item, KnowledgePoint):
            questions.update(link.question for link in item.question_links if link.question is not None)
    for question in questions:
        if question.status == "active" and not question_can_be_active(session, question):
            question.status = REVIEW_REQUIRED_STATUS


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("teachers.id"), nullable=False, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_points: Mapped[float] = mapped_column(Float, default=100, nullable=False)
    allow_resubmit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_grade: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"
    __table_args__ = (UniqueConstraint("assignment_id", "question_id", name="uq_assignment_question"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)


class AssignmentTarget(Base):
    __tablename__ = "assignment_targets"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id", ondelete="SET NULL"), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="submitted", nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    graded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    answer: Mapped[Any] = mapped_column(JSON, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    criteria_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    answer: Mapped[Any] = mapped_column(JSON, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    criteria_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("student_id", "chapter_id", name="uq_student_chapter_progress"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    percent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    last_section: Mapped[str | None] = mapped_column(String(160))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class KnowledgeMastery(Base):
    __tablename__ = "knowledge_mastery"
    __table_args__ = (UniqueConstraint("student_id", "knowledge_point", name="uq_student_knowledge"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_point: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    mastery: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    publisher_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    class_scope: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(96))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
