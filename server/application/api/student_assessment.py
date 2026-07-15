from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import time_ns
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..errors import APIError
from ..models import (
    Assignment,
    AssignmentQuestion,
    AssignmentTarget,
    PracticeAttempt,
    PracticeSession,
    PracticeSessionQuestion,
    Question,
    Submission,
    SubmissionAnswer,
    Student,
)
from ..schemas.practice import AnswerSave, PracticeSessionCreate
from ..services.grading import grade_objective
from ..services.mastery import MasteryAllocation, apply_mastery
from ..services.practice_selection import question_snapshot, sanitize_snapshot, select_practice_questions
from .dependencies import AuthContext, require_student
from .student import student_for


router = APIRouter(prefix="/api/student", tags=["student-assessment"])


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def _session_for(session, session_id: str, student_id: str) -> PracticeSession:
    record = session.scalar(
        select(PracticeSession)
        .options(selectinload(PracticeSession.questions))
        .where(PracticeSession.id == session_id, PracticeSession.student_id == student_id)
    )
    if not record:
        raise APIError(404, "练习会话不存在", "PRACTICE_SESSION_NOT_FOUND")
    return record


def _practice_payload(record: PracticeSession) -> dict:
    reveal = record.status != "in_progress"
    return {
        "id": record.id,
        "subjectId": record.subject_id,
        "mode": record.selection_mode,
        "chapter": record.chapter,
        "knowledgePointIds": record.knowledge_point_ids,
        "requestedCount": record.requested_count,
        "status": record.status,
        "score": record.score,
        "maxScore": record.max_score,
        "startedAt": record.started_at,
        "submittedAt": record.submitted_at,
        "questions": [
            {
                **sanitize_snapshot(item.grading_snapshot, include_solutions=reveal),
                "answer": item.answer,
                "status": item.status,
                "score": item.score,
                "maxScore": item.max_score,
                "criteriaScores": item.criteria_scores,
                "confidence": item.confidence,
                "feedback": item.feedback,
                "savedAt": item.saved_at,
            }
            for item in record.questions
        ],
    }


@router.post("/practice-sessions")
def create_practice_session(body: PracticeSessionCreate, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        questions = select_practice_questions(
            session,
            student_id=student.id,
            subject_id=body.subject_id,
            mode=body.mode,
            chapter=body.chapter,
            knowledge_point_ids=body.knowledge_point_ids,
            count=body.count,
            seed=time_ns(),
        )
        record = PracticeSession(
            id=str(uuid4()), student_id=student.id, subject_id=body.subject_id,
            selection_mode=body.mode, chapter=body.chapter,
            knowledge_point_ids=list(body.knowledge_point_ids), requested_count=body.count,
            questions=[
                PracticeSessionQuestion(
                    id=str(uuid4()), question_id=question.id, sequence=index,
                    question_snapshot=sanitize_snapshot(question_snapshot(question, sequence=index)),
                    grading_snapshot=question_snapshot(question, sequence=index),
                    max_score=question.points,
                )
                for index, question in enumerate(questions, start=1)
            ],
        )
        session.add(record)
        session.commit()
        payload = _practice_payload(record)
    return request.app.state.success(request, payload, "练习已创建")


@router.get("/practice-sessions/{session_id}")
def get_practice_session(session_id: str, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        payload = _practice_payload(_session_for(session, session_id, student.id))
    return request.app.state.success(request, payload)


@router.put("/practice-sessions/{session_id}/answers/{question_id}")
def save_practice_answer(session_id: str, question_id: str, body: AnswerSave, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        record = _session_for(session, session_id, student.id)
        if record.status != "in_progress":
            raise APIError(409, "练习已提交，不能继续保存答案", "PRACTICE_SESSION_CLOSED")
        item = next((item for item in record.questions if item.question_id == question_id), None)
        if not item:
            raise APIError(404, "题目不属于该练习", "PRACTICE_QUESTION_NOT_FOUND")
        item.answer = body.answer
        item.status = "answered"
        item.saved_at = now()
        session.commit()
        payload = {"sessionId": record.id, "questionId": question_id, "answer": item.answer, "savedAt": item.saved_at}
    return request.app.state.success(request, payload)


@router.post("/practice-sessions/{session_id}/submit")
def submit_practice_session(session_id: str, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        record = _session_for(session, session_id, student.id)
        if record.status != "in_progress":
            raise APIError(409, "练习已提交", "PRACTICE_SESSION_CLOSED")
        pending = False
        total_score = 0.0
        total_points = 0.0
        for item in record.questions:
            result = grade_objective(item.grading_snapshot, item.answer)
            item.status = result.status
            item.score = result.score
            item.max_score = result.max_score
            item.criteria_scores = result.criteria_scores
            item.confidence = result.confidence
            item.feedback = result.feedback
            total_points += result.max_score
            if result.score is not None:
                total_score += result.score
            else:
                pending = True
            session.add(PracticeAttempt(
                id=str(uuid4()), student_id=student.id, question_id=item.question_id,
                answer=item.answer, status=result.status, score=result.score, max_score=result.max_score,
                criteria_scores=result.criteria_scores, confidence=result.confidence, feedback=result.feedback,
                attempt_number=(session.scalar(select(func.count(PracticeAttempt.id)).where(PracticeAttempt.student_id == student.id, PracticeAttempt.question_id == item.question_id)) or 0) + 1,
            ))
            if result.status == "graded" and result.max_score:
                points = item.grading_snapshot.get("knowledgePointIds", [])
                weights = item.grading_snapshot.get("knowledgePointWeights", {})
                if points:
                    apply_mastery(
                        session,
                        student.id,
                        [MasteryAllocation(point, record.subject_id, result.score / result.max_score * 100, weights.get(point)) for point in points],
                    )
        record.status = "pending_review" if pending else "graded"
        record.score = total_score
        record.max_score = total_points
        record.submitted_at = now()
        session.commit()
        payload = _practice_payload(record)
    return request.app.state.success(request, payload, "练习已提交")


def _assignment_for(session, assignment_id: str, student_id: str) -> Assignment:
    record = session.scalar(
        select(Assignment)
        .join(AssignmentTarget, AssignmentTarget.assignment_id == Assignment.id)
        .where(Assignment.id == assignment_id, AssignmentTarget.student_id == student_id, Assignment.status == "published")
    )
    if not record:
        raise APIError(404, "试卷不存在或无权访问", "ASSIGNMENT_NOT_FOUND")
    return record


def _deadline(assignment: Assignment, submission: Submission | None = None) -> datetime | None:
    deadlines = [value for value in (aware(assignment.due_at),) if value]
    if submission and assignment.duration_minutes and submission.started_at:
        deadlines.append(aware(submission.started_at) + timedelta(minutes=assignment.duration_minutes))
    return min(deadlines) if deadlines else None


def _ensure_assignment_open(assignment: Assignment, submission: Submission | None = None) -> None:
    current = now()
    starts_at = aware(assignment.starts_at)
    if starts_at and current < starts_at:
        raise APIError(409, "试卷尚未开始", "ASSIGNMENT_NOT_OPEN")
    deadline = _deadline(assignment, submission)
    if deadline and current >= deadline:
        raise APIError(409, "试卷已截止", "ASSIGNMENT_CLOSED")


def _assignment_questions(session, assignment: Assignment) -> list[AssignmentQuestion]:
    records = list(session.scalars(select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment.id).order_by(AssignmentQuestion.sequence)))
    for item in records:
        if item.question_snapshot is None:
            question = session.get(Question, item.question_id)
            if not question:
                raise APIError(409, "试卷题目已不可用", "ASSIGNMENT_QUESTION_UNAVAILABLE")
            item.question_snapshot = question_snapshot(question, sequence=item.sequence, points=item.points)
    return records


def _formal_questions_payload(session, assignment: Assignment, submission: Submission, *, reveal: bool) -> list[dict]:
    answers = {item.question_id: item for item in session.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id))}
    return [
        {
            **sanitize_snapshot(item.question_snapshot or {}, include_solutions=reveal),
            "answer": answers[item.question_id].answer if item.question_id in answers else None,
            "score": answers[item.question_id].score if item.question_id in answers else None,
            "status": "pending_review" if item.question_id in answers and answers[item.question_id].score is None and submission.status == "pending_review" else None,
            "feedback": answers[item.question_id].feedback if item.question_id in answers else None,
        }
        for item in _assignment_questions(session, assignment)
    ]


def _countdown(assignment: Assignment, submission: Submission | None = None) -> dict:
    deadline = _deadline(assignment, submission)
    return {
        "startsAt": assignment.starts_at,
        "dueAt": assignment.due_at,
        "durationMinutes": assignment.duration_minutes,
        "deadlineAt": deadline,
        "remainingSeconds": max(0, int((deadline - now()).total_seconds())) if deadline else None,
    }


def _submission_for(session, submission_id: str, student_id: str) -> tuple[Submission, Assignment]:
    row = session.execute(
        select(Submission, Assignment)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .join(AssignmentTarget, AssignmentTarget.assignment_id == Assignment.id)
        .where(Submission.id == submission_id, Submission.student_id == student_id, AssignmentTarget.student_id == student_id)
    ).first()
    if not row:
        raise APIError(404, "提交记录不存在", "SUBMISSION_NOT_FOUND")
    return row


@router.get("/papers")
def list_formal_papers(request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        assignments = session.scalars(
            select(Assignment)
            .join(AssignmentTarget, AssignmentTarget.assignment_id == Assignment.id)
            .where(AssignmentTarget.student_id == student.id, Assignment.status == "published")
            .order_by(Assignment.created_at.desc())
        ).all()
        items = []
        for assignment in assignments:
            current = session.scalar(select(Submission).where(Submission.assignment_id == assignment.id, Submission.student_id == student.id, Submission.status == "in_progress"))
            submitted = session.scalar(select(Submission).where(Submission.assignment_id == assignment.id, Submission.student_id == student.id, Submission.status != "in_progress").order_by(Submission.attempt_number.desc()))
            items.append({
                "assignmentId": assignment.id, "title": assignment.title, "description": assignment.description,
                "totalPoints": assignment.total_points, "showAnswersMode": assignment.show_answers_mode,
                "allowResubmit": assignment.allow_resubmit, "countdown": _countdown(assignment, current),
                "submissionId": current.id if current else None, "submitted": submitted is not None,
            })
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.post("/assignments/{assignment_id}/start")
def start_formal_paper(assignment_id: str, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        assignment = _assignment_for(session, assignment_id, student.id)
        active = session.scalar(select(Submission).where(Submission.assignment_id == assignment.id, Submission.student_id == student.id, Submission.status == "in_progress"))
        _ensure_assignment_open(assignment, active)
        if active:
            payload = {"submissionId": active.id, "attemptNumber": active.attempt_number, "resumed": True, "countdown": _countdown(assignment, active), "questions": _formal_questions_payload(session, assignment, active, reveal=False)}
            return request.app.state.success(request, payload)
        completed = list(session.scalars(select(Submission).where(Submission.assignment_id == assignment.id, Submission.student_id == student.id, Submission.status != "in_progress")))
        if len(completed) >= (2 if assignment.allow_resubmit else 1):
            raise APIError(409, "已达到可提交次数上限", "ATTEMPT_LIMIT_REACHED")
        submission = Submission(id=str(uuid4()), assignment_id=assignment.id, student_id=student.id, attempt_number=len(completed) + 1, status="in_progress", started_at=now())
        session.add(submission)
        _assignment_questions(session, assignment)
        session.commit()
        payload = {"submissionId": submission.id, "attemptNumber": submission.attempt_number, "resumed": False, "countdown": _countdown(assignment, submission), "questions": _formal_questions_payload(session, assignment, submission, reveal=False)}
    return request.app.state.success(request, payload, "试卷已开始")


@router.put("/submissions/{submission_id}/answers/{question_id}")
def save_formal_answer(submission_id: str, question_id: str, body: AnswerSave, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        submission, assignment = _submission_for(session, submission_id, student.id)
        if submission.status != "in_progress":
            raise APIError(409, "试卷已提交，不能继续保存答案", "SUBMISSION_CLOSED")
        _ensure_assignment_open(assignment, submission)
        item = session.scalar(select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment.id, AssignmentQuestion.question_id == question_id))
        if not item:
            raise APIError(404, "题目不属于该试卷", "SUBMISSION_QUESTION_NOT_FOUND")
        answer = session.scalar(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id, SubmissionAnswer.question_id == question_id))
        if not answer:
            answer = SubmissionAnswer(id=str(uuid4()), submission_id=submission.id, question_id=question_id, answer=body.answer)
            session.add(answer)
        else:
            answer.answer = body.answer
        session.commit()
        payload = {"submissionId": submission.id, "questionId": question_id, "answer": answer.answer}
    return request.app.state.success(request, payload)


def _recalculate_formal_average(session, student_id: str) -> None:
    submissions = session.execute(
        select(Submission, Assignment)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(Submission.student_id == student_id, Submission.status == "graded", Assignment.status == "published", Submission.score.is_not(None))
    ).all()
    latest: dict[str, tuple[Submission, Assignment]] = {}
    for submission, assignment in submissions:
        if assignment.id not in latest or submission.attempt_number > latest[assignment.id][0].attempt_number:
            latest[assignment.id] = (submission, assignment)
    scores = [submission.score / assignment.total_points * 100 for submission, assignment in latest.values() if assignment.total_points]
    if scores:
        student = session.get(Student, student_id)
        student.average_score = sum(scores) / len(scores)


@router.post("/submissions/{submission_id}/submit")
def submit_formal_paper(submission_id: str, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        submission, assignment = _submission_for(session, submission_id, student.id)
        if submission.status != "in_progress":
            raise APIError(409, "试卷已提交", "SUBMISSION_CLOSED")
        _ensure_assignment_open(assignment, submission)
        answers = {item.question_id: item for item in session.scalars(select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission.id))}
        score = 0.0
        pending = False
        for item in _assignment_questions(session, assignment):
            answer = answers.get(item.question_id)
            if not answer:
                answer = SubmissionAnswer(id=str(uuid4()), submission_id=submission.id, question_id=item.question_id, answer=None)
                session.add(answer)
            result = grade_objective(item.question_snapshot or {}, answer.answer)
            answer.score = result.score
            answer.criteria_scores = result.criteria_scores
            answer.confidence = result.confidence
            answer.feedback = result.feedback
            if result.score is None:
                pending = True
            else:
                score += result.score
        submission.score = score
        submission.status = "pending_review" if pending else "graded"
        submission.submitted_at = now()
        submission.graded_at = now() if not pending else None
        if submission.status == "graded":
            _recalculate_formal_average(session, student.id)
        session.commit()
        payload = {"submissionId": submission.id, "status": submission.status, "score": submission.score, "maxScore": assignment.total_points, "countdown": _countdown(assignment, submission)}
    return request.app.state.success(request, payload, "试卷已提交")


@router.get("/submissions/{submission_id}/result")
def formal_result(submission_id: str, request: Request, auth: AuthContext = Depends(require_student)):
    with request.app.state.database.session() as session:
        student = student_for(session, auth.user.id)
        submission, assignment = _submission_for(session, submission_id, student.id)
        if submission.status == "in_progress":
            raise APIError(409, "提交后才能查看结果", "SUBMISSION_NOT_FINISHED")
        reveal = assignment.show_answers_mode == "after_submission" or (assignment.show_answers_mode == "after_close" and _deadline(assignment, submission) is not None and now() >= _deadline(assignment, submission))
        payload = {"submissionId": submission.id, "assignmentId": assignment.id, "status": submission.status, "score": submission.score, "maxScore": assignment.total_points, "showAnswers": reveal, "questions": _formal_questions_payload(session, assignment, submission, reveal=reveal)}
    return request.app.state.success(request, payload)
