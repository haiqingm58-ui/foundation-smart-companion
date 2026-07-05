from __future__ import annotations

import secrets
from collections.abc import Callable
from uuid import uuid4

from sqlalchemy import select

from ..database import Database
from ..models import ClassRoom, Student, Teacher, TeacherStudentBinding, User
from ..security import hash_password


PasswordFactory = Callable[[str, int], str]


def generate_demo_password(role: str, index: int) -> str:
    prefix = {"teacher": "Teach", "student": "Study", "admin": "Admin"}[role]
    return f"{prefix}-{secrets.token_hex(4)}A{index}"


def create_demo_accounts(database: Database, count: int = 6, password_factory: PasswordFactory = generate_demo_password) -> dict:
    created = 0
    skipped = 0
    credentials: list[dict] = []
    teachers: dict[int, tuple[User, Teacher]] = {}
    students: dict[int, tuple[User, Student]] = {}

    with database.session() as session:
        classroom = session.scalar(select(ClassRoom).where(ClassRoom.name == "基础工程演示班"))
        if not classroom:
            classroom = ClassRoom(
                id=str(uuid4()), name="基础工程演示班", grade="2026",
                major="土木工程", college="土木工程学院",
            )
            session.add(classroom)
            session.flush()

        for role in ("teacher", "student", "admin"):
            for index in range(1, count + 1):
                username = f"{role}{index:02d}"
                user = session.scalar(select(User).where(User.username == username))
                if user:
                    skipped += 1
                else:
                    password = password_factory(role, index)
                    role_label = {"teacher": "指导老师", "student": "学生", "admin": "管理员"}[role]
                    name_prefix = {"teacher": "演示教师", "student": "演示学生", "admin": "演示管理员"}[role]
                    number = {"teacher": f"DEMO-T{index:02d}", "student": f"DEMO-S{index:02d}", "admin": f"DEMO-A{index:02d}"}[role]
                    user = User(
                        id=str(uuid4()), username=username, password_hash=hash_password(password),
                        password_algorithm="argon2", role=role, role_label=role_label,
                        name=f"{name_prefix}{index:02d}", status="active", student_no=number,
                        college="土木工程学院", school="湖南大学", must_change_password=True,
                    )
                    session.add(user)
                    session.flush()
                    created += 1
                    credentials.append({"role": role, "name": user.name, "username": username, "password": password})

                if role == "teacher":
                    profile = session.scalar(select(Teacher).where(Teacher.user_id == user.id))
                    if not profile:
                        profile = Teacher(
                            id=str(uuid4()), user_id=user.id, teacher_no=f"DEMO-T{index:02d}",
                            college="土木工程学院", course="基础工程",
                        )
                        session.add(profile)
                        session.flush()
                    teachers[index] = (user, profile)
                elif role == "student":
                    profile = session.scalar(select(Student).where(Student.user_id == user.id))
                    if not profile:
                        profile = Student(
                            id=str(uuid4()), user_id=user.id, student_no=f"DEMO-S{index:02d}",
                            class_id=classroom.id,
                        )
                        session.add(profile)
                        session.flush()
                    elif profile.class_id is None:
                        profile.class_id = classroom.id
                    students[index] = (user, profile)

        for index in range(1, count + 1):
            teacher_user, teacher = teachers[index]
            _student_user, student = students[index]
            binding = session.scalar(
                select(TeacherStudentBinding).where(
                    TeacherStudentBinding.teacher_id == teacher.id,
                    TeacherStudentBinding.student_id == student.id,
                    TeacherStudentBinding.class_id == classroom.id,
                )
            )
            if not binding:
                session.add(
                    TeacherStudentBinding(
                        id=str(uuid4()), teacher_id=teacher.id, student_id=student.id,
                        class_id=classroom.id, status="active", created_by=teacher_user.id,
                    )
                )
        session.commit()

    return {"created": created, "skipped": skipped, "credentials": credentials}
