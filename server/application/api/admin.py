from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from ..errors import APIError
from ..models import ClassRoom, OperationLog, Student, Teacher, TeacherStudentBinding, User
from ..schemas.admin import BindingInput, ClassInput, TeacherStudentWizard
from ..security import hash_password
from ..services.audit import add_log
from ..services.imports import build_import_template
from .auth import client_ip
from .dependencies import AuthContext, require_admin


router = APIRouter(prefix="/api/admin", tags=["administrator"])


def page_payload(items: list[dict], total: int, page: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page, "pageSize": page_size, "pages": max(1, (total + page_size - 1) // page_size)}


@router.get("/dashboard")
def dashboard(request: Request, _auth: AuthContext = Depends(require_admin)):
    database = request.app.state.database
    today = datetime.now(timezone.utc).date()
    with database.session() as session:
        role_counts = dict(session.execute(select(User.role, func.count(User.id)).group_by(User.role)).all())
        class_total = session.scalar(select(func.count(ClassRoom.id))) or 0
        bound_total = session.scalar(select(func.count(TeacherStudentBinding.id)).where(TeacherStudentBinding.status == "active")) or 0
        disabled_total = session.scalar(select(func.count(User.id)).where(User.status == "disabled")) or 0
    student_total = role_counts.get("student", 0)
    return request.app.state.success(
        request,
        {
            "teacherTotal": role_counts.get("teacher", 0), "studentTotal": student_total,
            "classTotal": class_total, "boundStudentTotal": bound_total,
            "unboundStudentTotal": max(0, student_total - bound_total), "disabledAccountTotal": disabled_total,
            "todayNewAccounts": 0, "todayLoginTotal": 0,
        },
    )


def list_role_users(request: Request, role: str, page: int, page_size: int, search: str, status: str | None):
    database = request.app.state.database
    filters = [User.role == role]
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(User.name.like(term), User.username.like(term), User.student_no.like(term)))
    if status:
        filters.append(User.status == status)
    with database.session() as session:
        total = session.scalar(select(func.count(User.id)).where(*filters)) or 0
        users = session.scalars(
            select(User).where(*filters).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        items = [
            {
                "id": user.id, "name": user.name, "username": user.username, "number": user.student_no,
                "college": user.college, "status": user.status, "lastLoginAt": user.last_login_at,
            }
            for user in users
        ]
    return request.app.state.success(request, page_payload(items, total, page, page_size))


@router.get("/teachers")
def teachers(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str = "", status: str | None = None, _auth: AuthContext = Depends(require_admin)):
    return list_role_users(request, "teacher", page, pageSize, search, status)


@router.get("/students")
def students(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str = "", status: str | None = None, _auth: AuthContext = Depends(require_admin)):
    return list_role_users(request, "student", page, pageSize, search, status)


@router.get("/classes")
def classes(request: Request, _auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        items = [
            {"id": item.id, "name": item.name, "grade": item.grade, "major": item.major, "college": item.college}
            for item in session.scalars(select(ClassRoom).order_by(ClassRoom.name)).all()
        ]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.post("/classes")
def create_class(body: ClassInput, request: Request, auth: AuthContext = Depends(require_admin)):
    database = request.app.state.database
    with database.session() as session:
        if session.scalar(select(ClassRoom).where(ClassRoom.name == body.name)):
            raise APIError(409, "班级名称已存在", "CLASS_EXISTS")
        classroom = ClassRoom(id=str(uuid4()), **body.model_dump())
        session.add(classroom)
        add_log(session, auth.user.id, "class.create", "class", classroom.id, {"name": classroom.name}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": classroom.id}, "班级创建成功")


@router.get("/bindings")
def bindings(request: Request, _auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        rows = session.execute(
            select(TeacherStudentBinding, Teacher, Student, User)
            .join(Teacher, Teacher.id == TeacherStudentBinding.teacher_id)
            .join(Student, Student.id == TeacherStudentBinding.student_id)
            .join(User, User.id == Student.user_id)
            .order_by(TeacherStudentBinding.created_at.desc())
        ).all()
        items = [
            {
                "id": binding.id, "teacherId": teacher.id, "studentId": student.id,
                "studentName": user.name, "studentNo": student.student_no,
                "classId": binding.class_id, "status": binding.status,
            }
            for binding, teacher, student, user in rows
        ]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.post("/bindings/batch")
def create_bindings(body: BindingInput, request: Request, auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        teacher = session.get(Teacher, body.teacher_id)
        if not teacher:
            raise APIError(404, "教师不存在", "TEACHER_NOT_FOUND")
        created = 0
        for student_id in body.student_ids:
            if not session.get(Student, student_id):
                raise APIError(404, "学生不存在", "STUDENT_NOT_FOUND")
            existing = session.scalar(
                select(TeacherStudentBinding).where(
                    TeacherStudentBinding.teacher_id == teacher.id,
                    TeacherStudentBinding.student_id == student_id,
                )
            )
            if existing:
                continue
            session.add(
                TeacherStudentBinding(
                    id=str(uuid4()), teacher_id=teacher.id, student_id=student_id,
                    class_id=body.class_id, status="active", created_by=auth.user.id,
                )
            )
            created += 1
        add_log(session, auth.user.id, "binding.batch_create", "teacher", teacher.id, {"count": created}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"created": created})


@router.post("/teachers-with-students")
def create_teacher_with_students(body: TeacherStudentWizard, request: Request, auth: AuthContext = Depends(require_admin)):
    database = request.app.state.database
    teacher_data = body.teacher
    student_numbers = [student.student_no for student in body.students]
    usernames = [student.username for student in body.students]
    if len(set(student_numbers)) != len(student_numbers) or len(set(usernames)) != len(usernames):
        raise APIError(409, "导入数据中存在重复学号或账号", "IMPORT_CONFLICT")
    try:
        with database.session() as session:
            teacher_conflict = session.scalar(
                select(User).where(or_(User.username == teacher_data.username, User.student_no == teacher_data.teacher_no))
            ) or session.scalar(select(Teacher).where(Teacher.teacher_no == teacher_data.teacher_no))
            student_conflict = session.scalar(
                select(User).where(or_(User.username.in_(usernames), User.student_no.in_(student_numbers)))
            )
            if teacher_conflict or student_conflict:
                raise APIError(409, "教师工号、学生学号或登录账号已存在", "IMPORT_CONFLICT")

            classroom = session.scalar(select(ClassRoom).where(ClassRoom.name == body.class_info.name))
            if not classroom:
                classroom = ClassRoom(id=str(uuid4()), **body.class_info.model_dump())
                session.add(classroom)
                session.flush()

            teacher_user = User(
                id=str(uuid4()), username=teacher_data.username, password_hash=hash_password(teacher_data.password),
                password_algorithm="argon2", role="teacher", role_label="指导老师", name=teacher_data.name,
                student_no=teacher_data.teacher_no, college=teacher_data.college, school="湖南大学",
                status=teacher_data.status, must_change_password=True,
            )
            session.add(teacher_user)
            session.flush()
            teacher = Teacher(
                id=str(uuid4()), user_id=teacher_user.id, teacher_no=teacher_data.teacher_no,
                college=teacher_data.college, course=teacher_data.course, phone=teacher_data.phone,
                email=str(teacher_data.email) if teacher_data.email else None,
            )
            session.add(teacher)
            session.flush()

            created_students = []
            for item in body.students:
                student_user = User(
                    id=str(uuid4()), username=item.username, password_hash=hash_password(item.password),
                    password_algorithm="argon2", role="student", role_label="学生", name=item.name,
                    student_no=item.student_no, college=body.class_info.college, school="湖南大学",
                    mentor=teacher_user.name, status="active", must_change_password=True,
                )
                session.add(student_user)
                session.flush()
                student = Student(id=str(uuid4()), user_id=student_user.id, student_no=item.student_no, class_id=classroom.id)
                session.add(student)
                session.flush()
                session.add(
                    TeacherStudentBinding(
                        id=str(uuid4()), teacher_id=teacher.id, student_id=student.id,
                        class_id=classroom.id, status="active", created_by=auth.user.id,
                    )
                )
                created_students.append(student)

            add_log(
                session, auth.user.id, "teacher.create_with_students", "teacher", teacher.id,
                {"teacherNo": teacher.teacher_no, "className": classroom.name, "studentCount": len(created_students)},
                client_ip(request),
            )
            session.commit()
    except APIError:
        raise
    except IntegrityError as exc:
        raise APIError(409, "创建失败，账号或绑定关系发生冲突", "IMPORT_CONFLICT") from exc

    return request.app.state.success(
        request,
        {
            "teacherCreated": True, "teacherId": teacher.id, "studentTotal": len(body.students),
            "studentSuccess": len(created_students), "studentFailed": 0,
            "bindingSuccess": len(created_students), "errors": [],
        },
        "教师、学生和绑定关系创建成功",
    )


@router.get("/import-template")
def import_template(_auth: AuthContext = Depends(require_admin)):
    return Response(
        build_import_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student-import-template.xlsx"'},
    )


@router.get("/logs")
def logs(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), _auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        total = session.scalar(select(func.count(OperationLog.id))) or 0
        records = session.scalars(select(OperationLog).order_by(OperationLog.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize)).all()
        items = [
            {"id": item.id, "actorId": item.actor_id, "action": item.action, "targetType": item.target_type, "targetId": item.target_id, "detail": item.detail, "createdAt": item.created_at}
            for item in records
        ]
    return request.app.state.success(request, page_payload(items, total, page, pageSize))
