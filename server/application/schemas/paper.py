from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator


class PaperModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PaperQuestionInput(PaperModel):
    question_id: str = Field(alias="questionId", min_length=1, max_length=96)
    section_title: str = Field(default="", alias="sectionTitle", max_length=255)
    sequence: int = Field(ge=1)
    points: float = Field(gt=0, le=1000)


class BlueprintRow(PaperModel):
    chapter_ids: list[str] = Field(default_factory=list, alias="chapterIds")
    knowledge_point_ids: list[str] = Field(default_factory=list, alias="knowledgePointIds")
    question_types: list[str] = Field(default_factory=list, alias="questionTypes")
    difficulties: list[str] = Field(default_factory=list)
    count: int = Field(ge=1, le=1000)
    points_each: float = Field(alias="pointsEach", gt=0, le=1000)
    section_title: str = Field(default="", alias="sectionTitle", max_length=255)


class Blueprint(PaperModel):
    subject_id: str = Field(alias="subjectId", min_length=1, max_length=64)
    seed: int = 0
    rows: list[BlueprintRow] = Field(min_length=1, max_length=100)
    _actor_id: str | None = PrivateAttr(default=None)


class AssemblyQuestion(PaperModel):
    question_id: str = Field(alias="questionId")
    text: str
    question_type: str = Field(alias="questionType")
    difficulty: str
    chapter: str | None
    knowledge_point_ids: list[str] = Field(alias="knowledgePointIds")
    section_title: str = Field(alias="sectionTitle")
    sequence: int
    points: float


class AssemblyShortage(PaperModel):
    row: int
    requested: int
    available: int
    missing: int
    criteria: dict[str, list[str]]


class AssemblyPreview(PaperModel):
    questions: list[AssemblyQuestion]
    coverage: dict[str, int]
    type_distribution: dict[str, int] = Field(alias="typeDistribution")
    difficulty_distribution: dict[str, int] = Field(alias="difficultyDistribution")
    duplicate_risk: int = Field(alias="duplicateRisk")
    shortages: list[AssemblyShortage]


class PaperUpsert(PaperModel):
    subject_id: str = Field(alias="subjectId", min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=12000)
    duration_minutes: int | None = Field(default=None, alias="durationMinutes", ge=1, le=1440)
    status: Literal["draft", "ready", "archived"] = "draft"
    assembly_mode: Literal["manual", "automatic"] = Field(default="manual", alias="assemblyMode")
    seed: int | None = None
    blueprint_rows: list[BlueprintRow] = Field(default_factory=list, alias="blueprintRows", max_length=100)
    questions: list[PaperQuestionInput] = Field(default_factory=list, max_length=1000)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("title cannot be blank")
        return value


class PaperPublishInput(PaperModel):
    publication_key: str | None = Field(
        default=None,
        alias="publicationKey",
        min_length=8,
        max_length=96,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$",
    )
    student_ids: list[str] = Field(default_factory=list, alias="studentIds")
    class_ids: list[str] = Field(default_factory=list, alias="classIds")
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=12000)
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    due_at: datetime | None = Field(default=None, alias="dueAt")
    duration_minutes: int | None = Field(default=None, alias="durationMinutes", ge=1, le=1440)
    show_answers_mode: Literal["never", "after_submission", "after_close"] = Field(
        default="after_submission", alias="showAnswersMode"
    )
    allow_resubmit: bool = Field(default=False, alias="allowResubmit")
    auto_grade: bool = Field(default=True, alias="autoGrade")

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("title cannot be blank")
        return value

    @field_validator("starts_at", "due_at")
    @classmethod
    def require_aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include an offset")
        return value.astimezone(timezone.utc)


def dump_api(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(by_alias=True)
