from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import selectinload

from ..errors import APIError
from ..models import (
    Assignment,
    AssignmentQuestion,
    AssignmentTarget,
    Paper,
    PaperQuestion,
    Question,
    Subject,
    TeacherStudentBinding,
)
from ..schemas.paper import (
    Blueprint,
    PaperPublishInput,
    PaperQuestionInput,
    PaperUpsert,
    dump_api,
)
from ..services.audit import add_log
from ..services.paper_assembly import assemble_paper
from .auth import client_ip
from .dependencies import AuthContext, require_teacher
from .teacher import teacher_for


router = APIRouter(prefix="/api/teacher/papers", tags=["teacher-papers"])


def _owned_paper(session, paper_id: str, actor_id: str) -> Paper:
    paper = session.scalar(
        select(Paper)
        .options(
            selectinload(Paper.paper_questions)
            .selectinload(PaperQuestion.question)
            .selectinload(Question.knowledge_point_links)
        )
        .where(Paper.id == paper_id, Paper.created_by == actor_id)
    )
    if paper is None:
        raise APIError(404, "试卷不存在", "PAPER_NOT_FOUND")
    return paper


def _paper_question_payload(item: PaperQuestion) -> dict:
    return {
        "questionId": item.question_id,
        "sectionTitle": item.section_title,
        "sequence": item.sequence,
        "points": item.points,
    }


def _paper_payload(paper: Paper, include_questions: bool = True) -> dict:
    payload = {
        "id": paper.id,
        "subjectId": paper.subject_id,
        "title": paper.title,
        "description": paper.description,
        "durationMinutes": paper.duration_minutes,
        "totalPoints": paper.total_points,
        "status": paper.status,
        "version": paper.version,
        "assemblyMode": paper.assembly_mode,
        "seed": paper.assembly_seed,
        "blueprintRows": paper.assembly_blueprint,
        "shortages": paper.shortages,
        "questionCount": len(paper.paper_questions),
        "createdAt": paper.created_at,
        "updatedAt": paper.updated_at,
    }
    if include_questions:
        payload["questions"] = [
            _paper_question_payload(item)
            for item in sorted(paper.paper_questions, key=lambda record: record.sequence)
        ]
    return payload


def _validate_subject(session, subject_id: str) -> Subject:
    subject = session.get(Subject, subject_id)
    if subject is None:
        raise APIError(404, "课程不存在", "SUBJECT_NOT_FOUND")
    if subject.status != "active":
        raise APIError(409, "课程当前不可用", "SUBJECT_INACTIVE")
    return subject


def _validate_manual_questions(
    session, actor_id: str, subject_id: str, items: list[PaperQuestionInput]
) -> list[PaperQuestionInput]:
    question_ids = [item.question_id for item in items]
    sequences = [item.sequence for item in items]
    if len(question_ids) != len(set(question_ids)):
        raise APIError(409, "试卷中不能重复使用同一题", "PAPER_QUESTION_DUPLICATE")
    if len(sequences) != len(set(sequences)):
        raise APIError(409, "试卷题目顺序不能重复", "PAPER_SEQUENCE_DUPLICATE")
    if not question_ids:
        return []
    questions = session.scalars(
        select(Question).where(
            Question.id.in_(question_ids),
            Question.status == "active",
            or_(Question.created_by.is_(None), Question.created_by == actor_id),
        )
    ).all()
    by_id = {question.id: question for question in questions}
    if len(by_id) != len(question_ids):
        raise APIError(404, "部分题目不存在或不可用", "QUESTION_NOT_FOUND")
    if any(question.subject_id != subject_id for question in by_id.values()):
        raise APIError(422, "试卷题目必须属于同一课程", "PAPER_SUBJECT_MISMATCH")
    return sorted(items, key=lambda item: item.sequence)


def _resolved_questions(session, body: PaperUpsert, actor_id: str):
    if body.assembly_mode == "manual":
        return _validate_manual_questions(
            session, actor_id, body.subject_id, body.questions
        ), [], [], body.seed
    if not body.blueprint_rows:
        raise APIError(422, "自动组卷必须提供蓝图条件", "PAPER_BLUEPRINT_REQUIRED")
    blueprint = Blueprint(
        subject_id=body.subject_id,
        seed=body.seed or 0,
        rows=body.blueprint_rows,
    )
    blueprint._actor_id = actor_id
    preview = assemble_paper(session, blueprint)
    questions = [
        PaperQuestionInput(
            question_id=item.question_id,
            section_title=item.section_title,
            sequence=item.sequence,
            points=item.points,
        )
        for item in preview.questions
    ]
    return (
        questions,
        [dump_api(item) for item in preview.shortages],
        [dump_api(item) for item in body.blueprint_rows],
        blueprint.seed,
    )


def _replace_questions(session, paper: Paper, questions: list[PaperQuestionInput]) -> None:
    if paper.paper_questions:
        paper.paper_questions.clear()
        session.flush()
    for item in questions:
        paper.paper_questions.append(
            PaperQuestion(
                id=str(uuid4()),
                question_id=item.question_id,
                section_title=item.section_title.strip(),
                sequence=item.sequence,
                points=item.points,
            )
        )
    paper.total_points = sum(item.points for item in questions)


def _apply_paper_body(session, paper: Paper, body: PaperUpsert, actor_id: str) -> None:
    _validate_subject(session, body.subject_id)
    questions, shortages, blueprint_rows, seed = _resolved_questions(session, body, actor_id)
    paper.subject_id = body.subject_id
    paper.title = body.title.strip()
    paper.description = body.description.strip()
    paper.duration_minutes = body.duration_minutes
    paper.status = body.status
    paper.assembly_mode = body.assembly_mode
    paper.assembly_blueprint = blueprint_rows
    paper.assembly_seed = seed
    paper.shortages = shortages
    _replace_questions(session, paper, questions)


@router.post("/generate-preview")
def generate_preview(
    body: Blueprint,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        _validate_subject(session, body.subject_id)
        body._actor_id = auth.user.id
        preview = assemble_paper(session, body)
    return request.app.state.success(request, dump_api(preview))


@router.get("")
def list_papers(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        records = session.scalars(
            select(Paper)
            .options(selectinload(Paper.paper_questions))
            .where(Paper.created_by == auth.user.id)
            .order_by(Paper.updated_at.desc(), Paper.id)
        ).all()
        items = [_paper_payload(item, include_questions=False) for item in records]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.post("")
def create_paper(
    body: PaperUpsert,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        paper = Paper(id=str(uuid4()), created_by=auth.user.id)
        _apply_paper_body(session, paper, body, auth.user.id)
        session.add(paper)
        add_log(
            session,
            auth.user.id,
            "paper.create",
            "paper",
            paper.id,
            {"subjectId": paper.subject_id, "questionCount": len(paper.paper_questions)},
            client_ip(request),
        )
        session.commit()
        payload = _paper_payload(paper)
    return request.app.state.success(request, payload, "试卷已保存")


@router.get("/{paper_id}")
def get_paper(
    paper_id: str,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        paper = _owned_paper(session, paper_id, auth.user.id)
        payload = _paper_payload(paper)
    return request.app.state.success(request, payload)


@router.put("/{paper_id}")
def update_paper(
    paper_id: str,
    body: PaperUpsert,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        paper = _owned_paper(session, paper_id, auth.user.id)
        _apply_paper_body(session, paper, body, auth.user.id)
        paper.version += 1
        add_log(
            session,
            auth.user.id,
            "paper.update",
            "paper",
            paper.id,
            {"version": paper.version},
            client_ip(request),
        )
        session.commit()
        payload = _paper_payload(paper)
    return request.app.state.success(request, payload)


@router.delete("/{paper_id}")
def delete_paper(
    paper_id: str,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        paper = _owned_paper(session, paper_id, auth.user.id)
        session.delete(paper)
        add_log(
            session,
            auth.user.id,
            "paper.delete",
            "paper",
            paper_id,
            {},
            client_ip(request),
        )
        session.commit()
    return request.app.state.success(request, {})


@router.post("/{paper_id}/copy")
def copy_paper(
    paper_id: str,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        source = _owned_paper(session, paper_id, auth.user.id)
        copied = Paper(
            id=str(uuid4()),
            subject_id=source.subject_id,
            title=f"{source.title} 副本",
            description=source.description,
            duration_minutes=source.duration_minutes,
            total_points=source.total_points,
            status="draft",
            version=1,
            assembly_mode=source.assembly_mode,
            assembly_blueprint=deepcopy(source.assembly_blueprint),
            assembly_seed=source.assembly_seed,
            shortages=deepcopy(source.shortages),
            created_by=auth.user.id,
            paper_questions=[
                PaperQuestion(
                    id=str(uuid4()),
                    question_id=item.question_id,
                    section_title=item.section_title,
                    sequence=item.sequence,
                    points=item.points,
                )
                for item in source.paper_questions
            ],
        )
        session.add(copied)
        add_log(
            session,
            auth.user.id,
            "paper.copy",
            "paper",
            copied.id,
            {"sourcePaperId": source.id},
            client_ip(request),
        )
        session.commit()
        payload = _paper_payload(copied)
    return request.app.state.success(request, payload, "试卷副本已创建")


def _publication_targets(session, teacher_id: str, body: PaperPublishInput) -> dict[str, str | None]:
    bindings = session.scalars(
        select(TeacherStudentBinding).where(
            TeacherStudentBinding.teacher_id == teacher_id,
            TeacherStudentBinding.status == "active",
        )
    ).all()
    owned_students = {binding.student_id: binding.class_id for binding in bindings}
    owned_classes = {binding.class_id for binding in bindings if binding.class_id is not None}
    if not set(body.student_ids).issubset(owned_students) or not set(body.class_ids).issubset(
        owned_classes
    ):
        raise APIError(403, "只能向本人管理的学生或班级发布试卷", "PAPER_TARGET_FORBIDDEN")
    selected = {student_id: owned_students[student_id] for student_id in body.student_ids}
    for binding in bindings:
        if binding.class_id in body.class_ids:
            selected[binding.student_id] = binding.class_id
    if not selected:
        raise APIError(422, "至少选择一名学生或一个班级", "PAPER_TARGET_REQUIRED")
    return selected


def _question_snapshot(item: PaperQuestion) -> dict:
    question = item.question
    return {
        "id": question.id,
        "subjectId": question.subject_id,
        "text": question.text,
        "questionType": question.question_type,
        "options": deepcopy(question.options),
        "correctAnswer": deepcopy(question.correct_answer),
        "explanation": question.explanation,
        "rubric": deepcopy(question.rubric),
        "difficulty": question.difficulty,
        "sourcePoints": question.points,
        "chapter": question.chapter,
        "knowledgePointIds": [
            link.knowledge_point_id for link in question.knowledge_point_links
        ],
        "attachments": deepcopy(question.attachments),
        "answerWordLimit": question.answer_word_limit,
        "gradingMode": question.grading_mode,
        "status": question.status,
        "source": question.source,
        "sourceMetadata": deepcopy(question.source_metadata),
        "sectionTitle": item.section_title,
        "sequence": item.sequence,
        "points": item.points,
    }


@router.post("/{paper_id}/publish")
def publish_paper(
    paper_id: str,
    body: PaperPublishInput,
    request: Request,
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        paper = _owned_paper(session, paper_id, auth.user.id)
        if paper.shortages:
            raise APIError(409, "试卷存在缺题，不能发布", "PAPER_HAS_SHORTAGES")
        if not paper.paper_questions:
            raise APIError(409, "空试卷不能发布", "PAPER_EMPTY")
        if body.starts_at and body.due_at and body.due_at <= body.starts_at:
            raise APIError(422, "截止时间必须晚于开始时间", "PAPER_TIME_RANGE_INVALID")
        targets = _publication_targets(session, teacher.id, body)
        assignment = Assignment(
            id=str(uuid4()),
            title=body.title or paper.title,
            description=paper.description if body.description is None else body.description,
            teacher_id=teacher.id,
            paper_id=paper.id,
            starts_at=body.starts_at,
            due_at=body.due_at,
            duration_minutes=body.duration_minutes or paper.duration_minutes,
            show_answers_mode=body.show_answers_mode,
            total_points=paper.total_points,
            allow_resubmit=body.allow_resubmit,
            auto_grade=body.auto_grade,
            status="published",
        )
        session.add(assignment)
        for item in sorted(paper.paper_questions, key=lambda record: record.sequence):
            session.add(
                AssignmentQuestion(
                    id=str(uuid4()),
                    assignment_id=assignment.id,
                    question_id=item.question_id,
                    sequence=item.sequence,
                    points=item.points,
                    question_snapshot=_question_snapshot(item),
                )
            )
        for student_id, class_id in targets.items():
            session.add(
                AssignmentTarget(
                    id=str(uuid4()),
                    assignment_id=assignment.id,
                    class_id=class_id,
                    student_id=student_id,
                )
            )
        paper.status = "published"
        detail = {
            "paperId": paper.id,
            "assignmentId": assignment.id,
            "targetCount": len(targets),
        }
        add_log(
            session,
            auth.user.id,
            "paper.publish",
            "paper",
            paper.id,
            detail,
            client_ip(request),
        )
        session.commit()
    return request.app.state.success(
        request,
        {
            "assignmentId": assignment.id,
            "paperId": paper.id,
            "targetCount": len(targets),
            "status": "published",
        },
        "试卷已发布",
    )
