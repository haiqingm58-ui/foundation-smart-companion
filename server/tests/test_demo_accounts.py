from __future__ import annotations

from sqlalchemy import func, select


def test_demo_accounts_are_created_with_profiles_bindings_and_unique_passwords(database_url: str) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import ClassRoom, Student, Teacher, TeacherStudentBinding, User
    from server.application.security import verify_password
    from server.application.services.demo_accounts import create_demo_accounts

    upgrade_database(database_url)
    database = create_database(database_url)
    password_factory = lambda role, index: f"{role.title()}-Demo{index:02d}Aa1"
    result = create_demo_accounts(database, count=6, password_factory=password_factory)

    assert result["created"] == 18
    assert result["skipped"] == 0
    assert len(result["credentials"]) == 18
    assert len({item["password"] for item in result["credentials"]}) == 18
    with database.session() as session:
        assert session.scalar(select(func.count(User.id))) == 18
        assert session.scalar(select(func.count(Teacher.id))) == 6
        assert session.scalar(select(func.count(Student.id))) == 6
        assert session.scalar(select(func.count(TeacherStudentBinding.id))) == 6
        classroom = session.scalar(select(ClassRoom).where(ClassRoom.name == "基础工程演示班"))
        assert classroom is not None
        user = session.scalar(select(User).where(User.username == "teacher01"))
        assert user.must_change_password is True
        assert user.password_algorithm == "argon2"
        assert verify_password("Teacher-Demo01Aa1", user.password_hash, user.password_algorithm)[0] is True

    repeated = create_demo_accounts(database, count=6, password_factory=password_factory)
    assert repeated == {"created": 0, "skipped": 18, "credentials": []}
    with database.session() as session:
        assert session.scalar(select(func.count(User.id))) == 18
        assert session.scalar(select(func.count(TeacherStudentBinding.id))) == 6
