from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class TeacherInput(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    teacher_no: str = Field(alias="teacherNo", min_length=1, max_length=64)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    college: str = Field(min_length=1, max_length=120)
    course: str = Field(default="基础工程", min_length=1, max_length=120)
    status: str = Field(default="active", pattern="^(active|disabled)$")

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("密码必须包含大写字母、小写字母和数字")
        return value

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        if value and not re.fullmatch(r"1\d{10}|[+\d][\d -]{5,20}", value):
            raise ValueError("手机号格式不正确")
        return value


class ClassInput(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    grade: str | None = Field(default=None, max_length=32)
    major: str = Field(default="土木工程", max_length=120)
    college: str = Field(default="土木工程学院", max_length=120)


class StudentInput(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    student_no: str = Field(alias="studentNo", min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    class_name: str = Field(alias="className", min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("密码必须包含大写字母、小写字母和数字")
        return value


class TeacherStudentWizard(StrictModel):
    teacher: TeacherInput
    classInfo: ClassInput
    students: list[StudentInput] = Field(min_length=1, max_length=1000)

    @property
    def class_info(self) -> ClassInput:
        return self.classInfo


class BindingInput(StrictModel):
    teacher_id: str = Field(alias="teacherId")
    student_ids: list[str] = Field(alias="studentIds", min_length=1)
    class_id: str | None = Field(default=None, alias="classId")


class AccountStatusInput(StrictModel):
    status: str = Field(pattern="^(active|disabled)$")


class PasswordResetInput(StrictModel):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("密码必须包含大写字母、小写字母和数字")
        return value
