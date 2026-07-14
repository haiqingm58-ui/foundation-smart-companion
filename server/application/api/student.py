from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select

from ..errors import APIError
from ..models import KnowledgeMastery, LearningProgress, PracticeAttempt, Question, Student, User
from ..schemas.student import AttemptInput, ProgressInput
from ..services.grading import grade_objective
from .dependencies import AuthContext, require_student


router = APIRouter(prefix="/api/student", tags=["student"])


def student_for(session, user_id: str) -> Student:
    student = session.scalar(select(Student).where(Student.user_id == user_id))
    if not student:
        raise APIError(404, "学生档案不存在", "STUDENT_PROFILE_NOT_FOUND")
    return student


def rank_for(score: float) -> str:
    if score >= 90:
        return "王者"
    if score >= 80:
        return "白金"
    if score >= 70:
        return "黄金"
    if score >= 60:
        return "白银"
    return "青铜"


@router.get("/dashboard")
def dashboard(request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        progress_rows = session.scalars(select(LearningProgress).where(LearningProgress.student_id == student.id)).all()
        attempts = session.scalars(select(PracticeAttempt).where(PracticeAttempt.student_id == student.id).order_by(PracticeAttempt.submitted_at.desc())).all()
        weak = session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == student.id).order_by(KnowledgeMastery.mastery).limit(5)).all()
        latest = next(
            (
                item for item in attempts
                if item.status == "graded" and item.score is not None and item.max_score
            ),
            None,
        )
    return request.app.state.success(
        request,
        {
            "student": {"name": auth.user.name, "studentNo": student.student_no, "college": auth.user.college, "mentor": auth.user.mentor},
            "progress": student.progress, "averageScore": student.average_score, "rank": rank_for(student.average_score),
            "recentChapter": progress_rows[0].chapter_id if progress_rows else None,
            "pendingAssignments": 0,
            "latestScore": round(latest.score / latest.max_score * 100, 1) if latest else None,
            "weakKnowledgePoints": [{"name": item.knowledge_point, "mastery": item.mastery} for item in weak],
        },
    )


@router.put("/progress/{chapter_id}")
def update_progress(chapter_id: str, body: ProgressInput, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        row = session.scalar(select(LearningProgress).where(LearningProgress.student_id == student.id, LearningProgress.chapter_id == chapter_id))
        if not row:
            row = LearningProgress(id=str(uuid4()), student_id=student.id, chapter_id=chapter_id)
            session.add(row)
        row.percent = body.percent
        row.last_section = body.lastSection
        all_rows = session.scalars(select(LearningProgress).where(LearningProgress.student_id == student.id)).all()
        values = [item.percent for item in all_rows if item.id != row.id] + [row.percent]
        student.progress = sum(values) / len(values)
        session.commit()
    return request.app.state.success(request, {"chapterId": chapter_id, "percent": body.percent})


@router.get("/exercises")
def exercises(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str = "", chapter: str | None = None, questionType: str | None = None, _auth: AuthContext = Depends(require_student)):
    filters = []
    if search:
        filters.append(Question.text.like(f"%{search}%"))
    if chapter:
        filters.append(Question.chapter == chapter)
    if questionType:
        filters.append(Question.question_type == questionType)
    with request.app.state.database.session() as session:
        total = session.scalar(select(func.count(Question.id)).where(*filters)) or 0
        records = session.scalars(select(Question).where(*filters).order_by(Question.chapter, Question.created_at).offset((page - 1) * pageSize).limit(pageSize)).all()
        items = [{"id": item.id, "text": item.text, "questionType": item.question_type, "options": item.options, "difficulty": item.difficulty, "points": item.points, "chapter": item.chapter, "knowledgePoint": item.knowledge_point} for item in records]
    return request.app.state.success(request, {"items": items, "total": total, "page": page, "pageSize": pageSize})


@router.post("/exercises/{question_id}/attempts")
def submit_attempt(question_id: str, body: AttemptInput, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        question = session.get(Question, question_id)
        if not question:
            raise APIError(404, "题目不存在", "QUESTION_NOT_FOUND")
        previous = session.scalar(select(func.count(PracticeAttempt.id)).where(PracticeAttempt.student_id == student.id, PracticeAttempt.question_id == question_id)) or 0
        result = grade_objective(
            {
                "questionType": question.question_type,
                "correctAnswer": question.correct_answer,
                "points": question.points,
                "explanation": question.explanation,
            },
            body.answer,
        )
        attempt = PracticeAttempt(
            id=str(uuid4()), student_id=student.id, question_id=question.id, answer=body.answer,
            status=result.status, score=result.score, max_score=result.max_score,
            criteria_scores=result.criteria_scores, confidence=result.confidence,
            feedback=result.feedback, attempt_number=previous + 1,
        )
        session.add(attempt)
        mastery_value = (result.score / question.points * 100) if result.score is not None and question.points else 0
        if result.status == "graded" and question.knowledge_point:
            mastery = session.scalar(select(KnowledgeMastery).where(KnowledgeMastery.student_id == student.id, KnowledgeMastery.knowledge_point == question.knowledge_point))
            if not mastery:
                mastery = KnowledgeMastery(
                    id=str(uuid4()), student_id=student.id,
                    knowledge_point=question.knowledge_point, mastery=0, attempts=0,
                )
                session.add(mastery)
            mastery.mastery = (mastery.mastery * mastery.attempts + mastery_value) / (mastery.attempts + 1)
            mastery.attempts += 1
        session.commit()
    return request.app.state.success(request, {"attemptId": attempt.id, "status": result.status, "score": result.score, "maxScore": result.max_score, "confidence": result.confidence, "feedback": result.feedback, "criteriaScores": result.criteria_scores, "teacherReview": result.status == "pending_review" or result.confidence < 0.6})


@router.get("/report")
def report(request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        progress = session.scalars(select(LearningProgress).where(LearningProgress.student_id == student.id)).all()
        mastery = session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == student.id).order_by(KnowledgeMastery.mastery)).all()
        attempts = session.scalars(select(PracticeAttempt).where(PracticeAttempt.student_id == student.id).order_by(PracticeAttempt.submitted_at.desc())).all()
    graded_attempts = [item for item in attempts if item.status == "graded" and item.score is not None]
    return request.app.state.success(request, {"progress": round(student.progress, 1), "averageScore": round(student.average_score, 1), "rank": rank_for(student.average_score), "chapters": [{"id": item.chapter_id, "percent": item.percent, "lastSection": item.last_section} for item in progress], "mastery": [{"name": item.knowledge_point, "value": round(item.mastery, 1), "attempts": item.attempts} for item in mastery], "attemptTotal": len(attempts), "gradedAttemptTotal": len(graded_attempts), "weakKnowledgePoints": [item.knowledge_point for item in mastery[:5] if item.mastery < 70]})
