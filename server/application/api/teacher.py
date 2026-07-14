from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from ..errors import APIError
from ..models import (
    Assignment,
    AssignmentQuestion,
    AssignmentTarget,
    ClassRoom,
    KnowledgeChunk,
    Notice,
    OperationLog,
    Question,
    Resource,
    Student,
    Submission,
    Teacher,
    TeacherStudentBinding,
    User,
)
from ..schemas.teacher import AssignmentInput, GradeInput, NoticeInput, QuestionImportInput
from ..services.audit import add_log
from ..services.storage import chunk_text, extract_text, save_upload
from ..services.question_imports import build_question_import_template, parse_question_import
from ..services.question_service import create_question
from .auth import client_ip
from .dependencies import AuthContext, require_teacher


router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def teacher_for(session, user_id: str) -> Teacher:
    teacher = session.scalar(select(Teacher).where(Teacher.user_id == user_id))
    if not teacher:
        raise APIError(404, "教师档案不存在", "TEACHER_PROFILE_NOT_FOUND")
    return teacher


def owned_student_ids(session, teacher_id: str) -> list[str]:
    return list(
        session.scalars(
            select(TeacherStudentBinding.student_id).where(
                TeacherStudentBinding.teacher_id == teacher_id,
                TeacherStudentBinding.status == "active",
            )
        ).all()
    )


@router.get("/dashboard")
def dashboard(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        student_ids = owned_student_ids(session, teacher.id)
        student_total = len(student_ids)
        average_score = session.scalar(select(func.avg(Student.average_score)).where(Student.id.in_(student_ids))) if student_ids else 0
        class_total = session.scalar(
            select(func.count(func.distinct(TeacherStudentBinding.class_id))).where(
                TeacherStudentBinding.teacher_id == teacher.id, TeacherStudentBinding.status == "active"
            )
        ) or 0
        resource_total = session.scalar(select(func.count(Resource.id)).where(Resource.uploaded_by == auth.user.id)) or 0
        question_total = session.scalar(select(func.count(Question.id)).where(Question.created_by == auth.user.id)) or 0
        assignment_total = session.scalar(select(func.count(Assignment.id)).where(Assignment.teacher_id == teacher.id)) or 0
        pending_grading = session.scalar(
            select(func.count(Submission.id)).join(Assignment).where(
                Assignment.teacher_id == teacher.id, Submission.status == "submitted"
            )
        ) or 0
        assignment_ids = session.scalars(select(Assignment.id).where(Assignment.teacher_id == teacher.id)).all()
        target_total = session.scalar(select(func.count(AssignmentTarget.id)).where(AssignmentTarget.assignment_id.in_(assignment_ids))) if assignment_ids else 0
        submitted_total = session.scalar(
            select(func.count(func.distinct(Submission.student_id))).where(Submission.assignment_id.in_(assignment_ids))
        ) if assignment_ids else 0
        completion_rate = round((submitted_total or 0) / target_total * 100, 1) if target_total else 0
    return request.app.state.success(
        request,
        {
            "classTotal": class_total, "studentTotal": student_total, "resourceTotal": resource_total,
            "questionTotal": question_total, "assignmentTotal": assignment_total, "pendingGrading": pending_grading,
            "averageScore": round(float(average_score or 0), 1), "completionRate": completion_rate,
        },
    )


@router.get("/classes")
def classes(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        class_ids = session.scalars(
            select(TeacherStudentBinding.class_id).where(TeacherStudentBinding.teacher_id == teacher.id).distinct()
        ).all()
        records = session.scalars(select(ClassRoom).where(ClassRoom.id.in_([item for item in class_ids if item]))).all() if class_ids else []
        items = [{"id": item.id, "name": item.name, "grade": item.grade, "major": item.major} for item in records]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.get("/students")
def students(
    request: Request,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: str = "",
    classId: str | None = None,
    status: str | None = None,
    sort: str = "name",
    auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        query = (
            select(Student, User, ClassRoom)
            .join(TeacherStudentBinding, TeacherStudentBinding.student_id == Student.id)
            .join(User, User.id == Student.user_id)
            .outerjoin(ClassRoom, ClassRoom.id == Student.class_id)
            .where(TeacherStudentBinding.teacher_id == teacher.id, TeacherStudentBinding.status == "active")
        )
        if search:
            term = f"%{search.strip()}%"
            query = query.where(or_(User.name.like(term), Student.student_no.like(term)))
        if classId:
            query = query.where(Student.class_id == classId)
        if status:
            query = query.where(User.status == status)
        rows = session.execute(query).all()
        items = [
            {
                "id": student.id, "name": user.name, "studentNo": student.student_no,
                "className": classroom.name if classroom else "未分班", "classId": student.class_id,
                "progress": student.progress, "averageScore": student.average_score,
                "assignmentCompletion": 0, "lastLoginAt": user.last_login_at, "status": user.status,
            }
            for student, user, classroom in rows
        ]
        items.sort(key=lambda item: item.get(sort) or "", reverse=sort in {"progress", "averageScore"})
        total = len(items)
        items = items[(page - 1) * pageSize : page * pageSize]
    return request.app.state.success(request, {"items": items, "total": total, "page": page, "pageSize": pageSize, "pages": max(1, (total + pageSize - 1) // pageSize)})


@router.get("/students/{student_id}")
def student_detail(student_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        binding = session.scalar(
            select(TeacherStudentBinding).where(
                TeacherStudentBinding.teacher_id == teacher.id,
                TeacherStudentBinding.student_id == student_id,
                TeacherStudentBinding.status == "active",
            )
        )
        if not binding:
            raise APIError(404, "学生不存在或不属于当前教师", "STUDENT_NOT_FOUND")
        student = session.get(Student, student_id)
        user = session.get(User, student.user_id)
    return request.app.state.success(request, {"id": student.id, "name": user.name, "studentNo": student.student_no, "progress": student.progress, "averageScore": student.average_score})


@router.get("/resources")
def resources(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        records = session.scalars(select(Resource).where(Resource.uploaded_by == auth.user.id).order_by(Resource.created_at.desc())).all()
        items = [{"id": item.id, "title": item.title, "name": item.name, "fileSize": item.file_size, "mimeType": item.mime_type, "chapter": item.chapter, "knowledgePoint": item.knowledge_point, "visibility": item.visibility, "createdAt": item.created_at} for item in records]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.post("/resources")
async def upload_resource(
    request: Request,
    file: UploadFile = File(...),
    chapter: str = Form(""),
    knowledgePoint: str = Form(""),
    visibility: str = Form("private"),
    classScope: str = Form(""),
    auth: AuthContext = Depends(require_teacher),
):
    content = await file.read()
    filename = file.filename or "resource.txt"
    path = save_upload(request.app.state.settings.upload_dir, filename, content)
    text = extract_text(content, path.suffix)
    resource_id = str(uuid4())
    with request.app.state.database.session() as session:
        resource = Resource(
            id=resource_id, name=filename, title=Path(filename).stem, storage_path=str(path),
            file_size=len(content), mime_type=file.content_type or "application/octet-stream",
            source_type="teacher-upload", uploaded_by=auth.user.id, chapter=chapter or None,
            knowledge_point=knowledgePoint or None, visibility=visibility,
            class_scope=[item for item in classScope.split(",") if item], extracted_text=text,
        )
        session.add(resource)
        session.flush()
        for index, piece in enumerate(chunk_text(text)):
            session.add(
                KnowledgeChunk(
                    id=f"resource:{resource_id}:{index + 1}", resource_id=resource_id,
                    source_type="teacher", heading=resource.title, text=piece,
                    chapter=resource.chapter, sequence=index,
                )
            )
        add_log(session, auth.user.id, "resource.upload", "resource", resource_id, {"filename": filename}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": resource_id, "title": resource.title, "chunkCount": len(chunk_text(text))}, "资料上传成功")


@router.get("/resources/{resource_id}/download")
def download_resource(resource_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        resource = session.get(Resource, resource_id)
        if not resource or resource.uploaded_by != auth.user.id:
            raise APIError(404, "资料不存在", "RESOURCE_NOT_FOUND")
        path = Path(resource.storage_path)
        if not path.is_file():
            raise APIError(404, "资料文件已丢失", "RESOURCE_FILE_MISSING")
        name = resource.name
        mime = resource.mime_type
    return FileResponse(path, filename=name, media_type=mime)


@router.get("/resources/{resource_id}/preview")
def preview_resource(resource_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        resource = session.get(Resource, resource_id)
        if not resource or resource.uploaded_by != auth.user.id:
            raise APIError(404, "资料不存在", "RESOURCE_NOT_FOUND")
        path = Path(resource.storage_path)
        if not path.is_file():
            raise APIError(404, "资料文件已丢失", "RESOURCE_FILE_MISSING")
        mime = resource.mime_type
    return FileResponse(path, media_type=mime, headers={"Content-Disposition": "inline"})


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        resource = session.get(Resource, resource_id)
        if not resource or resource.uploaded_by != auth.user.id:
            raise APIError(404, "资料不存在", "RESOURCE_NOT_FOUND")
        path = Path(resource.storage_path)
        session.delete(resource)
        add_log(session, auth.user.id, "resource.delete", "resource", resource_id, {"name": resource.name}, client_ip(request))
        session.commit()
    if path.is_file() and path.resolve().is_relative_to(request.app.state.settings.upload_dir.resolve()):
        path.unlink()
    return request.app.state.success(request, {})


@router.get("/question-import-template")
def question_import_template(_auth: AuthContext = Depends(require_teacher)):
    return Response(
        content=build_question_import_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="foundation-question-import.xlsx"'},
    )


@router.post("/questions/import-preview")
async def preview_question_import(request: Request, file: UploadFile = File(...), _auth: AuthContext = Depends(require_teacher)):
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise APIError(413, "题库文件不能超过 5MB", "QUESTION_IMPORT_TOO_LARGE")
    try:
        result = parse_question_import(file.filename or "questions.xlsx", content)
    except ValueError as exc:
        raise APIError(400, str(exc), "QUESTION_IMPORT_INVALID") from exc
    return request.app.state.success(request, result)


@router.post("/questions/import")
def import_questions(body: QuestionImportInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    texts = [item.text.strip() for item in body.rows]
    if len(texts) != len(set(texts)):
        raise APIError(400, "提交数据中存在重复题干", "QUESTION_IMPORT_DUPLICATE")
    created_ids = []
    with request.app.state.database.session() as session:
        existing = session.scalars(
            select(Question.text).where(Question.created_by == auth.user.id, Question.text.in_(texts))
        ).all()
        if existing:
            raise APIError(409, f"已有相同题目：{existing[0]}", "QUESTION_ALREADY_EXISTS")
        for item in body.rows:
            question = create_question(item.model_dump(by_alias=True), session, auth.user.id, source="teacher-import")
            created_ids.append(question.id)
        add_log(session, auth.user.id, "question.import", "question", None, {"count": len(created_ids)}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"created": len(created_ids), "ids": created_ids}, "题库导入成功")


@router.get("/assignments")
def assignments(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        records = session.scalars(select(Assignment).where(Assignment.teacher_id == teacher.id).order_by(Assignment.created_at.desc())).all()
        items = []
        for item in records:
            target_count = session.scalar(select(func.count(AssignmentTarget.id)).where(AssignmentTarget.assignment_id == item.id)) or 0
            submitted_count = session.scalar(
                select(func.count(func.distinct(Submission.student_id))).where(Submission.assignment_id == item.id)
            ) or 0
            average_score = session.scalar(select(func.avg(Submission.score)).where(Submission.assignment_id == item.id, Submission.score.is_not(None)))
            items.append({
                "id": item.id, "title": item.title, "description": item.description,
                "startsAt": item.starts_at, "dueAt": item.due_at, "totalPoints": item.total_points,
                "status": item.status, "targetCount": target_count, "submittedCount": submitted_count,
                "completionRate": round(submitted_count / target_count * 100, 1) if target_count else 0,
                "averageScore": round(float(average_score), 1) if average_score is not None else None,
            })
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.get("/submissions")
def submissions(request: Request, status: str | None = None, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        query = (
            select(Submission, Assignment, Student, User)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .join(Student, Student.id == Submission.student_id)
            .join(User, User.id == Student.user_id)
            .where(Assignment.teacher_id == teacher.id)
            .order_by(Submission.submitted_at.desc())
        )
        if status:
            query = query.where(Submission.status == status)
        rows = session.execute(query).all()
        items = [
            {
                "id": submission.id, "assignmentId": assignment.id, "assignmentTitle": assignment.title,
                "studentId": student.id, "studentName": user.name, "studentNo": student.student_no,
                "status": submission.status, "score": submission.score, "feedback": submission.feedback,
                "submittedAt": submission.submitted_at, "gradedAt": submission.graded_at,
            }
            for submission, assignment, student, user in rows
        ]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.put("/submissions/{submission_id}/grade")
def grade_submission(submission_id: str, body: GradeInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        row = session.execute(
            select(Submission, Assignment)
            .join(Assignment, Assignment.id == Submission.assignment_id)
            .where(Submission.id == submission_id, Assignment.teacher_id == teacher.id)
        ).first()
        if not row:
            raise APIError(404, "提交记录不存在或不属于当前教师", "SUBMISSION_NOT_FOUND")
        submission, assignment = row
        if body.score > assignment.total_points:
            raise APIError(422, "得分不能超过作业总分", "GRADE_EXCEEDS_TOTAL")
        submission.score = body.score
        submission.feedback = body.feedback
        submission.status = "graded"
        submission.graded_at = datetime.now(timezone.utc)
        submission.graded_by = auth.user.id
        add_log(session, auth.user.id, "submission.grade", "submission", submission.id, {"score": body.score}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": submission_id, "score": body.score, "status": "graded"}, "批改已保存")


@router.post("/assignments")
def create_assignment(body: AssignmentInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        owned = set(owned_student_ids(session, teacher.id))
        if not set(body.studentIds).issubset(owned):
            raise APIError(403, "只能给本人管理的学生布置作业", "STUDENT_SCOPE_FORBIDDEN")
        questions = session.scalars(select(Question).where(Question.id.in_(body.questionIds))).all()
        if len(questions) != len(set(body.questionIds)):
            raise APIError(404, "部分题目不存在", "QUESTION_NOT_FOUND")
        assignment = Assignment(
            id=str(uuid4()), title=body.title, description=body.description, teacher_id=teacher.id,
            starts_at=body.startsAt, due_at=body.dueAt, total_points=body.totalPoints,
            allow_resubmit=body.allowResubmit, auto_grade=body.autoGrade, status=body.status,
        )
        session.add(assignment)
        session.flush()
        points = body.totalPoints / len(body.questionIds)
        for index, question_id in enumerate(body.questionIds):
            session.add(AssignmentQuestion(id=str(uuid4()), assignment_id=assignment.id, question_id=question_id, sequence=index + 1, points=points))
        for student_id in body.studentIds:
            student = session.get(Student, student_id)
            session.add(AssignmentTarget(id=str(uuid4()), assignment_id=assignment.id, class_id=student.class_id, student_id=student_id))
        add_log(session, auth.user.id, "assignment.create", "assignment", assignment.id, {"status": assignment.status, "studentCount": len(body.studentIds)}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": assignment.id}, "作业创建成功")


@router.get("/analytics")
def analytics(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        ids = owned_student_ids(session, teacher.id)
        records = session.scalars(select(Student).where(Student.id.in_(ids))).all() if ids else []
        average = sum(item.average_score for item in records) / len(records) if records else 0
        progress = sum(item.progress for item in records) / len(records) if records else 0
    return request.app.state.success(request, {"studentTotal": len(records), "averageScore": round(average, 1), "averageProgress": round(progress, 1), "weakKnowledgePoints": [], "scoreTrend": []})


@router.get("/notices")
def notices(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        records = session.scalars(
            select(Notice).where(Notice.publisher_id == auth.user.id).order_by(Notice.published_at.desc())
        ).all()
        items = [
            {"id": item.id, "title": item.title, "content": item.content, "audience": item.audience, "classScope": item.class_scope, "publishedAt": item.published_at}
            for item in records
        ]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.post("/notices")
def create_notice(body: NoticeInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        if body.audience == "class":
            owned_class_ids = set(
                session.scalars(
                    select(TeacherStudentBinding.class_id).where(
                        TeacherStudentBinding.teacher_id == teacher.id,
                        TeacherStudentBinding.status == "active",
                    ).distinct()
                ).all()
            )
            if not body.classScope or not set(body.classScope).issubset(owned_class_ids):
                raise APIError(403, "只能向本人管理的班级发布通知", "CLASS_SCOPE_FORBIDDEN")
        notice = Notice(
            id=str(uuid4()), title=body.title, content=body.content, publisher_id=auth.user.id,
            audience=body.audience, class_scope=body.classScope,
        )
        session.add(notice)
        add_log(session, auth.user.id, "notice.create", "notice", notice.id, {"audience": notice.audience}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": notice.id}, "通知已发布")
