from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from ..errors import APIError
from ..models import ClassRoom, OperationLog, SessionToken, Student, Teacher, TeacherStudentBinding, User
from ..schemas.admin import (
    AccountStatusInput, AdminStudentInput, AdminStudentUpdate, BatchStudentsInput,
    BindingInput, ClassInput, PasswordResetInput, TeacherInput, TeacherStudentWizard, TeacherUpdate,
)
from ..security import hash_password
from ..services.audit import add_log
from ..services.imports import build_import_template, parse_student_file
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
        user_ids = [user.id for user in users]
        profiles = {}
        if role == "teacher" and user_ids:
            profiles = {item.user_id: item for item in session.scalars(select(Teacher).where(Teacher.user_id.in_(user_ids))).all()}
        if role == "student" and user_ids:
            profiles = {item.user_id: item for item in session.scalars(select(Student).where(Student.user_id.in_(user_ids))).all()}
        items = [
            {
                "id": user.id, "name": user.name, "username": user.username, "number": user.student_no,
                "college": user.college, "status": user.status, "lastLoginAt": user.last_login_at,
                "profileId": profiles[user.id].id if user.id in profiles else None,
            }
            for user in users
        ]
    return request.app.state.success(request, page_payload(items, total, page, page_size))


@router.get("/teachers")
def teachers(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str = "", status: str | None = None, _auth: AuthContext = Depends(require_admin)):
    return list_role_users(request, "teacher", page, pageSize, search, status)


@router.post("/teachers")
def create_teacher(body: TeacherInput, request: Request, auth: AuthContext = Depends(require_admin)):
    try:
        with request.app.state.database.session() as session:
            user = User(
                id=str(uuid4()), username=body.username, password_hash=hash_password(body.password),
                password_algorithm="argon2", role="teacher", role_label="指导老师", name=body.name,
                student_no=body.teacher_no, college=body.college, school="湖南大学",
                status=body.status, must_change_password=True,
            )
            session.add(user)
            session.flush()
            teacher = Teacher(
                id=str(uuid4()), user_id=user.id, teacher_no=body.teacher_no, college=body.college,
                course=body.course, phone=body.phone, email=str(body.email) if body.email else None,
            )
            session.add(teacher)
            add_log(session, auth.user.id, "teacher.create", "teacher", teacher.id, {"teacherNo": teacher.teacher_no}, client_ip(request))
            session.commit()
            teacher_id = teacher.id
    except IntegrityError as exc:
        raise APIError(409, "教师工号或登录账号已存在", "TEACHER_EXISTS") from exc
    return request.app.state.success(request, {"id": teacher_id}, "教师创建成功")


@router.put("/teachers/{teacher_id}")
def update_teacher(teacher_id: str, body: TeacherUpdate, request: Request, auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        teacher = session.get(Teacher, teacher_id)
        if not teacher:
            raise APIError(404, "教师不存在", "TEACHER_NOT_FOUND")
        user = session.get(User, teacher.user_id)
        user.name, user.college, user.status = body.name, body.college, body.status
        teacher.college, teacher.course, teacher.phone = body.college, body.course, body.phone
        teacher.email = str(body.email) if body.email else None
        if body.status == "disabled":
            session.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
        add_log(session, auth.user.id, "teacher.update", "teacher", teacher.id, {"status": body.status}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": teacher_id}, "教师信息已更新")


@router.get("/students")
def students(request: Request, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), search: str = "", status: str | None = None, _auth: AuthContext = Depends(require_admin)):
    return list_role_users(request, "student", page, pageSize, search, status)


def ensure_class(session, class_id: str | None) -> None:
    if class_id and not session.get(ClassRoom, class_id):
        raise APIError(404, "班级不存在", "CLASS_NOT_FOUND")


@router.post("/students")
def create_student(body: AdminStudentInput, request: Request, auth: AuthContext = Depends(require_admin)):
    try:
        with request.app.state.database.session() as session:
            ensure_class(session, body.class_id)
            user = User(
                id=str(uuid4()), username=body.username, password_hash=hash_password(body.password),
                password_algorithm="argon2", role="student", role_label="学生", name=body.name,
                student_no=body.student_no, college=body.college, school="湖南大学",
                status=body.status, must_change_password=True,
            )
            session.add(user)
            session.flush()
            student = Student(id=str(uuid4()), user_id=user.id, student_no=body.student_no, class_id=body.class_id)
            session.add(student)
            add_log(session, auth.user.id, "student.create", "student", student.id, {"studentNo": student.student_no}, client_ip(request))
            session.commit()
            student_id = student.id
    except IntegrityError as exc:
        raise APIError(409, "学生学号或登录账号已存在", "STUDENT_EXISTS") from exc
    return request.app.state.success(request, {"id": student_id}, "学生创建成功")


@router.put("/students/{student_id}")
def update_student(student_id: str, body: AdminStudentUpdate, request: Request, auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        student = session.get(Student, student_id)
        if not student:
            raise APIError(404, "学生不存在", "STUDENT_NOT_FOUND")
        ensure_class(session, body.class_id)
        user = session.get(User, student.user_id)
        user.name, user.college, user.status = body.name, body.college, body.status
        student.class_id = body.class_id
        if body.status == "disabled":
            session.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
        add_log(session, auth.user.id, "student.update", "student", student.id, {"status": body.status}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": student_id}, "学生信息已更新")


@router.post("/students/batch")
def create_students_batch(body: BatchStudentsInput, request: Request, auth: AuthContext = Depends(require_admin)):
    created = []
    try:
        with request.app.state.database.session() as session:
            ensure_class(session, body.class_id)
            for item in body.students:
                user = User(
                    id=str(uuid4()), username=item.username, password_hash=hash_password(item.password),
                    password_algorithm="argon2", role="student", role_label="学生", name=item.name,
                    student_no=item.student_no, college="土木工程学院", school="湖南大学",
                    status="active", must_change_password=True,
                )
                session.add(user)
                session.flush()
                student = Student(id=str(uuid4()), user_id=user.id, student_no=item.student_no, class_id=body.class_id)
                session.add(student)
                created.append(student.id)
            add_log(session, auth.user.id, "student.batch_create", "student", None, {"count": len(created)}, client_ip(request))
            session.commit()
    except IntegrityError as exc:
        raise APIError(409, "批量创建失败：存在重复学号或登录账号，已全部回滚", "STUDENT_BATCH_CONFLICT") from exc
    return request.app.state.success(request, {"created": len(created), "ids": created}, "学生批量创建成功")


@router.patch("/accounts/{user_id}/status")
def update_account_status(user_id: str, body: AccountStatusInput, request: Request, auth: AuthContext = Depends(require_admin)):
    if user_id == auth.user.id and body.status == "disabled":
        raise APIError(400, "不能停用当前管理员账号", "CANNOT_DISABLE_SELF")
    with request.app.state.database.session() as session:
        user = session.get(User, user_id)
        if not user:
            raise APIError(404, "账号不存在", "ACCOUNT_NOT_FOUND")
        user.status = body.status
        if body.status == "disabled":
            session.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
        add_log(session, auth.user.id, "account.status", "user", user.id, {"status": body.status}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": user_id, "status": body.status}, "账号状态已更新")


@router.post("/accounts/{user_id}/reset-password")
def reset_account_password(user_id: str, body: PasswordResetInput, request: Request, auth: AuthContext = Depends(require_admin)):
    with request.app.state.database.session() as session:
        user = session.get(User, user_id)
        if not user:
            raise APIError(404, "账号不存在", "ACCOUNT_NOT_FOUND")
        user.password_hash = hash_password(body.password)
        user.password_algorithm = "argon2"
        user.password_salt = None
        user.must_change_password = True
        session.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
        add_log(session, auth.user.id, "account.reset_password", "user", user.id, {}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": user_id}, "密码已重置")


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
        teacher_user = aliased(User)
        student_user = aliased(User)
        rows = session.execute(
            select(TeacherStudentBinding, Teacher, Student, teacher_user, student_user, ClassRoom)
            .join(Teacher, Teacher.id == TeacherStudentBinding.teacher_id)
            .join(Student, Student.id == TeacherStudentBinding.student_id)
            .join(teacher_user, teacher_user.id == Teacher.user_id)
            .join(student_user, student_user.id == Student.user_id)
            .outerjoin(ClassRoom, ClassRoom.id == TeacherStudentBinding.class_id)
            .order_by(TeacherStudentBinding.created_at.desc())
        ).all()
        items = [
            {
                "id": binding.id, "teacherId": teacher.id, "studentId": student.id,
                "teacherName": teacher_user_row.name, "teacherNo": teacher.teacher_no,
                "studentName": student_user_row.name, "studentNo": student.student_no,
                "classId": binding.class_id, "className": classroom.name if classroom else None,
                "status": binding.status,
            }
            for binding, teacher, student, teacher_user_row, student_user_row, classroom in rows
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


@router.post("/import/preview")
async def preview_import(request: Request, file: UploadFile = File(...), _auth: AuthContext = Depends(require_admin)):
    filename = file.filename or "students.xlsx"
    if not filename.lower().endswith((".xlsx", ".csv")):
        raise APIError(415, "仅支持 XLSX 或 CSV 文件", "IMPORT_FILE_TYPE")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise APIError(413, "导入文件不能超过 5MB", "IMPORT_FILE_TOO_LARGE")
    try:
        result = parse_student_file(content, filename)
    except Exception as exc:
        raise APIError(422, "无法解析导入文件，请检查模板格式", "IMPORT_PARSE_FAILED") from exc
    return request.app.state.success(request, result, "导入预检完成")


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
