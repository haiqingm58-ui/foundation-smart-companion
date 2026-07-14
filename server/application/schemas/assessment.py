from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator


class AssessmentModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid", strict=True)


class KnowledgePointInput(AssessmentModel):
    subject_id: StrictStr = Field(alias="subjectId", min_length=1, max_length=64)
    chapter: StrictStr = Field(min_length=1, max_length=160)
    name: StrictStr = Field(min_length=1, max_length=160)
    description: StrictStr = Field(default="", max_length=12000)
    status: StrictStr = Field(default="active", pattern="^(active|inactive)$")

    @field_validator("chapter", "name", mode="before")
    @classmethod
    def strip_required_catalog_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class KnowledgePointMergeInput(AssessmentModel):
    target_id: StrictStr = Field(alias="targetId", min_length=1, max_length=96)
