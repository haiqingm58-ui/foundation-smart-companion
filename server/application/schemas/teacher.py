from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeacherModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionInput(TeacherModel):
    text: str = Field(min_length=2, max_length=12000)
    questionType: str = Field(pattern="^(单项选择题|多项选择题|判断题|填空题|简答题|计算题)$")
    options: list[dict[str, Any]] = Field(default_factory=list)
    correctAnswer: Any | None = None
    explanation: str | None = Field(default=None, max_length=12000)
    rubric: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: str = Field(default="基础", pattern="^(基础|中等|困难)$")
    points: float = Field(default=10, gt=0, le=1000)
    chapter: str | None = Field(default=None, max_length=120)
    knowledgePoint: str | None = Field(default=None, max_length=160)
    answerWordLimit: int | None = Field(default=None, ge=20, le=2000)
    gradingMode: str = Field(default="auto", pattern="^(auto|manual)$")


class QuestionImportInput(TeacherModel):
    rows: list[QuestionInput] = Field(min_length=1, max_length=1000)


class AssignmentInput(TeacherModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    studentIds: list[str] = Field(min_length=1)
    questionIds: list[str] = Field(min_length=1)
    startsAt: datetime | None = None
    dueAt: datetime | None = None
    totalPoints: float = Field(default=100, gt=0)
    allowResubmit: bool = False
    autoGrade: bool = True
    status: str = Field(default="draft", pattern="^(draft|published|closed)$")

    @field_validator("startsAt", "dueAt")
    @classmethod
    def require_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include an offset")
        return value.astimezone(timezone.utc)


class GradeInput(TeacherModel):
    score: float = Field(ge=0)
    feedback: str = Field(default="", max_length=8000)


class NoticeInput(TeacherModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=12000)
    audience: str = Field(default="all", pattern="^(all|class)$")
    classScope: list[str] = Field(default_factory=list)
