from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PracticeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PracticeSessionCreate(PracticeModel):
    subject_id: str = Field(alias="subjectId", min_length=1, max_length=64)
    mode: Literal["chapter", "knowledge_points"]
    chapter: str | None = Field(default=None, min_length=1, max_length=160)
    knowledge_point_ids: list[str] = Field(default_factory=list, alias="knowledgePointIds", max_length=3)
    question_types: list[str] = Field(default_factory=list, alias="questionTypes", max_length=12)
    difficulties: list[str] = Field(default_factory=list, max_length=12)
    count: int = Field(ge=1, le=100)

    @model_validator(mode="after")
    def validate_selection(self):
        if self.mode == "chapter" and not self.chapter:
            raise ValueError("chapter mode requires chapter")
        if self.mode == "knowledge_points" and not 1 <= len(self.knowledge_point_ids) <= 3:
            raise ValueError("knowledge-point mode requires one to three IDs")
        if len(set(self.knowledge_point_ids)) != len(self.knowledge_point_ids):
            raise ValueError("knowledge-point IDs must be unique")
        if len(set(self.question_types)) != len(self.question_types):
            raise ValueError("question types must be unique")
        if len(set(self.difficulties)) != len(self.difficulties):
            raise ValueError("difficulties must be unique")
        return self


class AnswerSave(PracticeModel):
    answer: Any
