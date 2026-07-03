from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select

from ..errors import APIError
from ..models import (
    Assignment,
    AssignmentQuestion,
    AssignmentTarget,
    ClassRoom,
    KnowledgeChunk,
    OperationLog,
    Question,
    Resource,
    Student,
    Teacher,
    TeacherStudentBinding,
    User,
)
from ..schemas.teacher import AssignmentInput, QuestionInput
from ..services.audit import add_log
from ..services.storage import chunk_text, extract_text, save_upload
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
    return request.app.state.success(
        request,
        {
            "classTotal": class_total, "studentTotal": student_total, "resourceTotal": resource_total,
            "questionTotal": question_total, "assignmentTotal": assignment_total, "pendingGrading": 0,
            "averageScore": round(float(average_score or 0), 1), "completionRate": 0,
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


@router.get("/questions")
def questions(request: Request, search: str = "", chapter: str | None = None, questionType: str | None = None, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        filters = [or_(Question.created_by == auth.user.id, Question.source == "textbook")]
        if search:
            filters.append(Question.text.like(f"%{search}%"))
        if chapter:
            filters.append(Question.chapter == chapter)
        if questionType:
            filters.append(Question.question_type == questionType)
        records = session.scalars(select(Question).where(*filters).order_by(Question.created_at.desc())).all()
        items = [question_payload(item) for item in records]
    return request.app.state.success(request, {"items": items, "total": len(items)})


def question_payload(item: Question) -> dict:
    return {"id": item.id, "text": item.text, "questionType": item.question_type, "options": item.options, "correctAnswer": item.correct_answer, "explanation": item.explanation, "rubric": item.rubric, "difficulty": item.difficulty, "points": item.points, "chapter": item.chapter, "knowledgePoint": item.knowledge_point, "source": item.source}


@router.post("/questions")
def create_question(body: QuestionInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    question = Question(
        id=str(uuid4()), text=body.text, question_type=body.questionType, options=body.options,
        correct_answer=body.correctAnswer, explanation=body.explanation, rubric=body.rubric,
        difficulty=body.difficulty, points=body.points, chapter=body.chapter,
        knowledge_point=body.knowledgePoint, source="teacher", created_by=auth.user.id,
    )
    with request.app.state.database.session() as session:
        session.add(question)
        add_log(session, auth.user.id, "question.create", "question", question.id, {"chapter": question.chapter}, client_ip(request))
        session.commit()
    return request.app.state.success(request, question_payload(question), "题目创建成功")


@router.put("/questions/{question_id}")
def update_question(question_id: str, body: QuestionInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        question = session.get(Question, question_id)
        if not question or question.created_by != auth.user.id:
            raise APIError(404, "题目不存在或不可编辑", "QUESTION_NOT_FOUND")
        values = {
            "text": body.text, "question_type": body.questionType, "options": body.options,
            "correct_answer": body.correctAnswer, "explanation": body.explanation, "rubric": body.rubric,
            "difficulty": body.difficulty, "points": body.points, "chapter": body.chapter,
            "knowledge_point": body.knowledgePoint,
        }
        for key, value in values.items():
            setattr(question, key, value)
        add_log(session, auth.user.id, "question.update", "question", question.id, {}, client_ip(request))
        session.commit()
        payload = question_payload(question)
    return request.app.state.success(request, payload)


@router.delete("/questions/{question_id}")
def delete_question(question_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        question = session.get(Question, question_id)
        if not question or question.created_by != auth.user.id:
            raise APIError(404, "题目不存在或不可删除", "QUESTION_NOT_FOUND")
        session.delete(question)
        add_log(session, auth.user.id, "question.delete", "question", question_id, {}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {})


@router.get("/assignments")
def assignments(request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        teacher = teacher_for(session, auth.user.id)
        records = session.scalars(select(Assignment).where(Assignment.teacher_id == teacher.id).order_by(Assignment.created_at.desc())).all()
        items = [{"id": item.id, "title": item.title, "description": item.description, "startsAt": item.starts_at, "dueAt": item.due_at, "totalPoints": item.total_points, "status": item.status} for item in records]
    return request.app.state.success(request, {"items": items, "total": len(items)})


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
